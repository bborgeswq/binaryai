"""
Risk Management System
Ensures trades comply with risk parameters and protects capital
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum
from loguru import logger

from config.settings import TradingConfig, get_settings


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskCheck:
    """Result of a risk check"""
    passed: bool
    risk_level: RiskLevel
    check_name: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "risk_level": self.risk_level.value,
            "check_name": self.check_name,
            "message": self.message,
            "details": self.details
        }


@dataclass
class RiskAssessment:
    """Complete risk assessment for a trade"""
    approved: bool
    overall_risk: RiskLevel
    checks: List[RiskCheck]
    adjusted_size: Optional[Decimal] = None
    adjusted_stop_loss: Optional[float] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "overall_risk": self.overall_risk.value,
            "checks": [c.to_dict() for c in self.checks],
            "adjusted_size": float(self.adjusted_size) if self.adjusted_size else None,
            "adjusted_stop_loss": self.adjusted_stop_loss,
            "warnings": self.warnings
        }


class RiskManager:
    """
    Comprehensive risk management system.
    Validates trades, manages position sizing, and enforces risk limits.
    """

    def __init__(
            self,
            config: Optional[TradingConfig] = None,
            max_daily_trades: int = 10,
            max_correlation_exposure: float = 0.5,
            cool_down_after_loss: int = 300  # seconds
    ):
        """
        Initialize risk manager.

        Args:
            config: Trading configuration
            max_daily_trades: Maximum trades per day
            max_correlation_exposure: Max exposure to correlated assets
            cool_down_after_loss: Cool down period after a loss (seconds)
        """
        self.config = config or get_settings().trading
        self.max_daily_trades = max_daily_trades
        self.max_correlation_exposure = max_correlation_exposure
        self.cool_down_after_loss = cool_down_after_loss

        # Tracking
        self.daily_trades: List[datetime] = []
        self.daily_pnl: Decimal = Decimal("0")
        self.last_loss_time: Optional[datetime] = None
        self.consecutive_losses: int = 0
        self.day_start: datetime = datetime.now().replace(hour=0, minute=0, second=0)

        # Correlated assets (simplified)
        self.correlation_groups = {
            "crypto": ["BTC/USD", "ETH/USD", "LTC/USD", "SOL/USD"],
            "tech": ["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
        }

        logger.info("Risk Manager initialized")

    def assess_trade(
            self,
            symbol: str,
            side: str,
            quantity: Decimal,
            entry_price: float,
            stop_loss: Optional[float],
            take_profit: Optional[float],
            portfolio_value: Decimal,
            current_positions: List[Dict[str, Any]],
            open_orders: List[Dict[str, Any]]
    ) -> RiskAssessment:
        """
        Assess a proposed trade for risk compliance.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Proposed quantity
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            portfolio_value: Current portfolio value
            current_positions: List of current positions
            open_orders: List of open orders

        Returns:
            RiskAssessment with approval status and any adjustments
        """
        self._reset_daily_if_needed()

        checks = []
        warnings = []
        adjusted_size = quantity
        adjusted_stop = stop_loss

        # 1. Daily trade limit check
        checks.append(self._check_daily_trades())

        # 2. Daily loss limit check
        checks.append(self._check_daily_loss(portfolio_value))

        # 3. Position size check
        size_check, adjusted_size = self._check_position_size(
            quantity, entry_price, portfolio_value
        )
        checks.append(size_check)

        # 4. Risk per trade check
        risk_check, adjusted_stop = self._check_trade_risk(
            entry_price, stop_loss, adjusted_size, portfolio_value
        )
        checks.append(risk_check)

        # 5. Max positions check
        checks.append(self._check_max_positions(current_positions))

        # 6. Correlation check
        checks.append(self._check_correlation(symbol, current_positions))

        # 7. Cool down check (after losses)
        checks.append(self._check_cool_down())

        # 8. Consecutive losses check
        checks.append(self._check_consecutive_losses())

        # 9. Minimum R:R ratio check
        if stop_loss and take_profit:
            checks.append(self._check_risk_reward(entry_price, stop_loss, take_profit))

        # 10. Market hours check (for stocks)
        if not "/" in symbol:  # Likely a stock
            checks.append(self._check_market_hours())

        # Compile results
        failed_checks = [c for c in checks if not c.passed]
        critical_fails = [c for c in failed_checks if c.risk_level == RiskLevel.CRITICAL]
        high_fails = [c for c in failed_checks if c.risk_level == RiskLevel.HIGH]

        # Determine approval
        approved = len(critical_fails) == 0 and len(high_fails) <= 1

        # Determine overall risk level
        if critical_fails:
            overall_risk = RiskLevel.CRITICAL
        elif len(high_fails) >= 2:
            overall_risk = RiskLevel.HIGH
        elif high_fails or len(failed_checks) >= 3:
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        # Add warnings for failed checks
        for check in failed_checks:
            warnings.append(f"{check.check_name}: {check.message}")

        return RiskAssessment(
            approved=approved,
            overall_risk=overall_risk,
            checks=checks,
            adjusted_size=adjusted_size,
            adjusted_stop_loss=adjusted_stop,
            warnings=warnings
        )

    def record_trade(self, pnl: Decimal):
        """Record a completed trade for tracking."""
        self.daily_trades.append(datetime.now())
        self.daily_pnl += pnl

        if pnl < 0:
            self.last_loss_time = datetime.now()
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

    def get_max_position_size(
            self,
            entry_price: float,
            stop_loss: float,
            portfolio_value: Decimal
    ) -> Decimal:
        """
        Calculate maximum position size based on risk parameters.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            portfolio_value: Portfolio value

        Returns:
            Maximum position size in base currency units
        """
        # Risk amount (2% of portfolio)
        risk_amount = portfolio_value * Decimal(str(self.config.max_risk_per_trade_pct))

        # Price risk per unit
        price_risk = abs(Decimal(str(entry_price)) - Decimal(str(stop_loss)))

        if price_risk <= 0:
            # Use default risk percentage
            price_risk = Decimal(str(entry_price)) * Decimal("0.02")

        # Calculate size
        size = risk_amount / price_risk

        # Also cap at max position size
        max_by_portfolio = portfolio_value * Decimal(str(self.config.max_position_size_pct)) / Decimal(str(entry_price))

        return min(size, max_by_portfolio)

    def _reset_daily_if_needed(self):
        """Reset daily counters if it's a new day."""
        now = datetime.now()
        if now.date() > self.day_start.date():
            self.daily_trades = []
            self.daily_pnl = Decimal("0")
            self.day_start = now.replace(hour=0, minute=0, second=0)
            logger.info("Daily risk counters reset")

    def _check_daily_trades(self) -> RiskCheck:
        """Check if daily trade limit is reached."""
        count = len([t for t in self.daily_trades if t.date() == datetime.now().date()])

        if count >= self.max_daily_trades:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.HIGH,
                check_name="Daily Trade Limit",
                message=f"Daily limit of {self.max_daily_trades} trades reached",
                details={"trades_today": count, "limit": self.max_daily_trades}
            )

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Daily Trade Limit",
            message=f"Trade {count + 1} of {self.max_daily_trades}",
            details={"trades_today": count, "limit": self.max_daily_trades}
        )

    def _check_daily_loss(self, portfolio_value: Decimal) -> RiskCheck:
        """Check if daily loss limit is reached."""
        max_loss = portfolio_value * Decimal(str(self.config.max_daily_loss_pct))
        loss_pct = abs(self.daily_pnl / portfolio_value * 100) if portfolio_value > 0 else 0

        if self.daily_pnl < -max_loss:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                check_name="Daily Loss Limit",
                message=f"Daily loss limit ({self.config.max_daily_loss_pct * 100:.1f}%) exceeded",
                details={
                    "daily_pnl": float(self.daily_pnl),
                    "max_loss": float(max_loss),
                    "loss_pct": float(loss_pct)
                }
            )

        risk_level = RiskLevel.LOW
        if loss_pct > self.config.max_daily_loss_pct * 50:
            risk_level = RiskLevel.MEDIUM

        return RiskCheck(
            passed=True,
            risk_level=risk_level,
            check_name="Daily Loss Limit",
            message=f"Daily P&L: ${float(self.daily_pnl):.2f} ({loss_pct:.1f}%)",
            details={"daily_pnl": float(self.daily_pnl), "max_loss": float(max_loss)}
        )

    def _check_position_size(
            self,
            quantity: Decimal,
            entry_price: float,
            portfolio_value: Decimal
    ) -> tuple:
        """Check if position size is within limits."""
        position_value = quantity * Decimal(str(entry_price))
        position_pct = position_value / portfolio_value if portfolio_value > 0 else Decimal("1")

        max_pct = Decimal(str(self.config.max_position_size_pct))
        adjusted_size = quantity

        if position_pct > max_pct:
            # Reduce size to max allowed
            adjusted_size = (portfolio_value * max_pct) / Decimal(str(entry_price))

            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                check_name="Position Size",
                message=f"Position reduced from {float(quantity):.4f} to {float(adjusted_size):.4f}",
                details={
                    "original_size": float(quantity),
                    "adjusted_size": float(adjusted_size),
                    "original_pct": float(position_pct * 100),
                    "max_pct": float(max_pct * 100)
                }
            ), adjusted_size

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Position Size",
            message=f"Position size: {float(position_pct * 100):.1f}% of portfolio",
            details={"position_pct": float(position_pct * 100)}
        ), adjusted_size

    def _check_trade_risk(
            self,
            entry_price: float,
            stop_loss: Optional[float],
            quantity: Decimal,
            portfolio_value: Decimal
    ) -> tuple:
        """Check if trade risk is within limits."""
        if not stop_loss:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                check_name="Trade Risk",
                message="No stop loss provided",
                details={}
            ), None

        price_risk = abs(Decimal(str(entry_price)) - Decimal(str(stop_loss)))
        dollar_risk = price_risk * quantity
        risk_pct = dollar_risk / portfolio_value if portfolio_value > 0 else Decimal("1")

        max_risk = Decimal(str(self.config.max_risk_per_trade_pct))
        adjusted_stop = stop_loss

        if risk_pct > max_risk:
            # Calculate adjusted stop loss
            max_dollar_risk = portfolio_value * max_risk
            max_price_risk = max_dollar_risk / quantity if quantity > 0 else Decimal("0")

            if entry_price > stop_loss:
                adjusted_stop = float(Decimal(str(entry_price)) - max_price_risk)
            else:
                adjusted_stop = float(Decimal(str(entry_price)) + max_price_risk)

            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                check_name="Trade Risk",
                message=f"Stop loss adjusted to maintain {max_risk * 100:.1f}% risk",
                details={
                    "original_stop": stop_loss,
                    "adjusted_stop": adjusted_stop,
                    "original_risk_pct": float(risk_pct * 100),
                    "max_risk_pct": float(max_risk * 100)
                }
            ), adjusted_stop

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Trade Risk",
            message=f"Trade risk: {float(risk_pct * 100):.1f}% of portfolio",
            details={"risk_pct": float(risk_pct * 100), "dollar_risk": float(dollar_risk)}
        ), stop_loss

    def _check_max_positions(self, current_positions: List[Dict[str, Any]]) -> RiskCheck:
        """Check if max positions limit is reached."""
        count = len(current_positions)
        max_pos = self.config.max_open_positions

        if count >= max_pos:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.HIGH,
                check_name="Max Positions",
                message=f"Maximum of {max_pos} positions already open",
                details={"current": count, "max": max_pos}
            )

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Max Positions",
            message=f"Positions: {count}/{max_pos}",
            details={"current": count, "max": max_pos}
        )

    def _check_correlation(
            self,
            symbol: str,
            current_positions: List[Dict[str, Any]]
    ) -> RiskCheck:
        """Check for over-exposure to correlated assets."""
        # Find which group the symbol belongs to
        symbol_group = None
        for group, symbols in self.correlation_groups.items():
            if symbol in symbols:
                symbol_group = group
                break

        if not symbol_group:
            return RiskCheck(
                passed=True,
                risk_level=RiskLevel.LOW,
                check_name="Correlation",
                message="No correlation group identified",
                details={}
            )

        # Count positions in the same group
        group_positions = 0
        for pos in current_positions:
            if pos.get("symbol") in self.correlation_groups.get(symbol_group, []):
                group_positions += 1

        exposure = group_positions / self.config.max_open_positions if self.config.max_open_positions > 0 else 0

        if exposure >= self.max_correlation_exposure:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                check_name="Correlation",
                message=f"High exposure to {symbol_group} assets ({group_positions} positions)",
                details={"group": symbol_group, "group_positions": group_positions}
            )

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Correlation",
            message=f"Correlation exposure OK ({group_positions} in {symbol_group})",
            details={"group": symbol_group, "group_positions": group_positions}
        )

    def _check_cool_down(self) -> RiskCheck:
        """Check if we're in cool down period after a loss."""
        if not self.last_loss_time:
            return RiskCheck(
                passed=True,
                risk_level=RiskLevel.LOW,
                check_name="Cool Down",
                message="No recent losses",
                details={}
            )

        elapsed = (datetime.now() - self.last_loss_time).total_seconds()

        if elapsed < self.cool_down_after_loss:
            remaining = self.cool_down_after_loss - elapsed
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                check_name="Cool Down",
                message=f"Cool down after loss: {remaining:.0f}s remaining",
                details={"remaining_seconds": remaining}
            )

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Cool Down",
            message="Cool down period completed",
            details={}
        )

    def _check_consecutive_losses(self) -> RiskCheck:
        """Check for consecutive losses."""
        if self.consecutive_losses >= 5:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.CRITICAL,
                check_name="Consecutive Losses",
                message=f"{self.consecutive_losses} consecutive losses - trading paused",
                details={"consecutive_losses": self.consecutive_losses}
            )

        if self.consecutive_losses >= 3:
            return RiskCheck(
                passed=True,
                risk_level=RiskLevel.HIGH,
                check_name="Consecutive Losses",
                message=f"{self.consecutive_losses} consecutive losses - proceed with caution",
                details={"consecutive_losses": self.consecutive_losses}
            )

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Consecutive Losses",
            message="Loss streak OK",
            details={"consecutive_losses": self.consecutive_losses}
        )

    def _check_risk_reward(
            self,
            entry_price: float,
            stop_loss: float,
            take_profit: float
    ) -> RiskCheck:
        """Check if risk/reward ratio is acceptable."""
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if risk == 0:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.HIGH,
                check_name="Risk/Reward",
                message="Invalid risk (stop = entry)",
                details={}
            )

        rr_ratio = reward / risk

        if rr_ratio < 1.5:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                check_name="Risk/Reward",
                message=f"R:R ratio {rr_ratio:.2f} below minimum 1.5",
                details={"rr_ratio": rr_ratio}
            )

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Risk/Reward",
            message=f"R:R ratio: {rr_ratio:.2f}",
            details={"rr_ratio": rr_ratio}
        )

    def _check_market_hours(self) -> RiskCheck:
        """Check if markets are open (for stocks)."""
        now = datetime.now()
        # Simplified: NYSE is open 9:30 AM - 4:00 PM ET, Mon-Fri
        # This is a basic check - in production, use proper market calendar

        is_weekend = now.weekday() >= 5
        is_market_hours = 9 <= now.hour < 16

        if is_weekend:
            return RiskCheck(
                passed=False,
                risk_level=RiskLevel.MEDIUM,
                check_name="Market Hours",
                message="Weekend - stock markets closed",
                details={}
            )

        if not is_market_hours:
            return RiskCheck(
                passed=True,
                risk_level=RiskLevel.LOW,
                check_name="Market Hours",
                message="Outside regular market hours",
                details={}
            )

        return RiskCheck(
            passed=True,
            risk_level=RiskLevel.LOW,
            check_name="Market Hours",
            message="Market hours OK",
            details={}
        )
