"""
Portfolio Manager
Tracks portfolio state, performance, and provides allocation insights
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal
from collections import defaultdict
from loguru import logger

from src.broker import BaseBroker, Position, Order


@dataclass
class PortfolioState:
    """Current state of the portfolio"""
    timestamp: datetime
    equity: Decimal
    cash: Decimal
    positions_value: Decimal
    positions: List[Position]
    unrealized_pnl: Decimal
    realized_pnl_today: Decimal
    allocation: Dict[str, float]  # symbol -> percentage

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": str(self.timestamp),
            "equity": float(self.equity),
            "cash": float(self.cash),
            "positions_value": float(self.positions_value),
            "positions_count": len(self.positions),
            "unrealized_pnl": float(self.unrealized_pnl),
            "realized_pnl_today": float(self.realized_pnl_today),
            "allocation": self.allocation
        }


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics"""
    total_return: float
    total_return_pct: float
    daily_return: float
    weekly_return: float
    monthly_return: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    trades_count: int
    winning_trades: int
    losing_trades: int
    avg_win: Decimal
    avg_loss: Decimal
    best_trade: Decimal
    worst_trade: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_return": self.total_return,
            "total_return_pct": f"{self.total_return_pct:.2f}%",
            "daily_return": f"{self.daily_return:.2f}%",
            "weekly_return": f"{self.weekly_return:.2f}%",
            "monthly_return": f"{self.monthly_return:.2f}%",
            "win_rate": f"{self.win_rate:.1f}%",
            "profit_factor": f"{self.profit_factor:.2f}",
            "max_drawdown": f"{self.max_drawdown:.2f}%",
            "sharpe_ratio": f"{self.sharpe_ratio:.2f}" if self.sharpe_ratio else "N/A",
            "trades_count": self.trades_count,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "avg_win": float(self.avg_win),
            "avg_loss": float(self.avg_loss),
            "best_trade": float(self.best_trade),
            "worst_trade": float(self.worst_trade)
        }


class PortfolioManager:
    """
    Manages portfolio tracking and performance analysis.
    """

    def __init__(
            self,
            broker: BaseBroker,
            initial_capital: Optional[Decimal] = None
    ):
        """
        Initialize portfolio manager.

        Args:
            broker: Broker connection
            initial_capital: Starting capital (for return calculations)
        """
        self.broker = broker
        self.initial_capital = initial_capital

        # History tracking
        self.equity_history: List[tuple] = []  # (timestamp, equity)
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_pnl: Dict[str, Decimal] = defaultdict(Decimal)

        # Peak tracking for drawdown
        self.peak_equity: Decimal = Decimal("0")

        logger.info("Portfolio Manager initialized")

    async def get_state(self) -> PortfolioState:
        """Get current portfolio state."""
        try:
            account = await self.broker.get_account()
            positions = await self.broker.get_positions()

            positions_value = sum(p.market_value for p in positions)
            unrealized_pnl = sum(p.unrealized_pnl for p in positions)

            # Calculate allocation
            allocation = {}
            if account.equity > 0:
                allocation["cash"] = float(account.cash / account.equity * 100)
                for p in positions:
                    allocation[p.symbol] = float(p.market_value / account.equity * 100)

            # Update initial capital if not set
            if not self.initial_capital:
                self.initial_capital = account.equity

            # Track equity
            self.equity_history.append((datetime.now(), account.equity))

            # Update peak
            if account.equity > self.peak_equity:
                self.peak_equity = account.equity

            # Get today's realized P&L
            today = datetime.now().strftime("%Y-%m-%d")
            realized_today = self.daily_pnl.get(today, Decimal("0"))

            return PortfolioState(
                timestamp=datetime.now(),
                equity=account.equity,
                cash=account.cash,
                positions_value=positions_value,
                positions=positions,
                unrealized_pnl=unrealized_pnl,
                realized_pnl_today=realized_today,
                allocation=allocation
            )

        except Exception as e:
            logger.error(f"Failed to get portfolio state: {e}")
            raise

    async def record_trade(
            self,
            symbol: str,
            side: str,
            quantity: Decimal,
            entry_price: float,
            exit_price: Optional[float] = None,
            pnl: Optional[Decimal] = None
    ):
        """Record a completed trade."""
        trade = {
            "timestamp": datetime.now(),
            "symbol": symbol,
            "side": side,
            "quantity": float(quantity),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": float(pnl) if pnl else None
        }

        self.trade_history.append(trade)

        # Update daily P&L
        if pnl:
            today = datetime.now().strftime("%Y-%m-%d")
            self.daily_pnl[today] += pnl

        logger.debug(f"Trade recorded: {symbol} {side} {quantity} @ {entry_price}")

    def calculate_metrics(self) -> PerformanceMetrics:
        """Calculate portfolio performance metrics."""
        if not self.trade_history:
            return PerformanceMetrics(
                total_return=0, total_return_pct=0, daily_return=0,
                weekly_return=0, monthly_return=0, win_rate=0,
                profit_factor=0, max_drawdown=0, sharpe_ratio=None,
                trades_count=0, winning_trades=0, losing_trades=0,
                avg_win=Decimal("0"), avg_loss=Decimal("0"),
                best_trade=Decimal("0"), worst_trade=Decimal("0")
            )

        # Separate winning and losing trades
        trades_with_pnl = [t for t in self.trade_history if t.get("pnl") is not None]
        winning = [t for t in trades_with_pnl if t["pnl"] > 0]
        losing = [t for t in trades_with_pnl if t["pnl"] <= 0]

        # Calculate totals
        total_wins = sum(Decimal(str(t["pnl"])) for t in winning)
        total_losses = abs(sum(Decimal(str(t["pnl"])) for t in losing))

        # Win rate
        win_rate = len(winning) / len(trades_with_pnl) * 100 if trades_with_pnl else 0

        # Profit factor
        profit_factor = float(total_wins / total_losses) if total_losses > 0 else float("inf")

        # Average win/loss
        avg_win = total_wins / len(winning) if winning else Decimal("0")
        avg_loss = total_losses / len(losing) if losing else Decimal("0")

        # Best/worst trades
        all_pnl = [Decimal(str(t["pnl"])) for t in trades_with_pnl]
        best_trade = max(all_pnl) if all_pnl else Decimal("0")
        worst_trade = min(all_pnl) if all_pnl else Decimal("0")

        # Returns
        total_pnl = sum(all_pnl)
        total_return = float(total_pnl)
        total_return_pct = float(total_pnl / self.initial_capital * 100) if self.initial_capital else 0

        # Period returns (simplified)
        daily_return = self._calculate_period_return(timedelta(days=1))
        weekly_return = self._calculate_period_return(timedelta(days=7))
        monthly_return = self._calculate_period_return(timedelta(days=30))

        # Max drawdown
        max_drawdown = self._calculate_max_drawdown()

        # Sharpe ratio (simplified - using 0% risk-free rate)
        sharpe_ratio = self._calculate_sharpe_ratio()

        return PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            daily_return=daily_return,
            weekly_return=weekly_return,
            monthly_return=monthly_return,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades_count=len(trades_with_pnl),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=avg_win,
            avg_loss=avg_loss,
            best_trade=best_trade,
            worst_trade=worst_trade
        )

    def _calculate_period_return(self, period: timedelta) -> float:
        """Calculate return over a specific period."""
        if len(self.equity_history) < 2:
            return 0.0

        now = datetime.now()
        start_time = now - period

        # Find equity at start of period
        start_equity = None
        for ts, equity in self.equity_history:
            if ts >= start_time:
                start_equity = equity
                break

        if not start_equity:
            start_equity = self.equity_history[0][1]

        current_equity = self.equity_history[-1][1]

        if start_equity > 0:
            return float((current_equity - start_equity) / start_equity * 100)
        return 0.0

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage."""
        if len(self.equity_history) < 2:
            return 0.0

        peak = Decimal("0")
        max_dd = 0.0

        for _, equity in self.equity_history:
            if equity > peak:
                peak = equity

            if peak > 0:
                dd = float((peak - equity) / peak * 100)
                max_dd = max(max_dd, dd)

        return max_dd

    def _calculate_sharpe_ratio(self) -> Optional[float]:
        """Calculate Sharpe ratio (simplified)."""
        if len(self.equity_history) < 10:
            return None

        import numpy as np

        # Calculate daily returns
        equities = [float(e) for _, e in self.equity_history]
        returns = np.diff(equities) / equities[:-1]

        if len(returns) < 2:
            return None

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return None

        # Annualize (assuming daily data)
        sharpe = (avg_return * 252) / (std_return * np.sqrt(252))

        return float(sharpe)

    def get_allocation_recommendation(
            self,
            current_allocation: Dict[str, float],
            target_allocation: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Get allocation rebalancing recommendations.

        Args:
            current_allocation: Current portfolio allocation
            target_allocation: Target allocation (default: equal weight)

        Returns:
            Recommendations for rebalancing
        """
        if not target_allocation:
            # Default: equal weight across positions
            num_positions = len([k for k in current_allocation if k != "cash"])
            if num_positions > 0:
                target_per_position = (100 - 20) / num_positions  # Keep 20% cash
                target_allocation = {"cash": 20}
                for k in current_allocation:
                    if k != "cash":
                        target_allocation[k] = target_per_position
            else:
                target_allocation = {"cash": 100}

        # Calculate differences
        recommendations = []
        for symbol in set(list(current_allocation.keys()) + list(target_allocation.keys())):
            current = current_allocation.get(symbol, 0)
            target = target_allocation.get(symbol, 0)
            diff = target - current

            if abs(diff) > 2:  # Only recommend if difference > 2%
                if diff > 0:
                    action = "increase"
                else:
                    action = "decrease"

                recommendations.append({
                    "symbol": symbol,
                    "current": f"{current:.1f}%",
                    "target": f"{target:.1f}%",
                    "action": action,
                    "amount": f"{abs(diff):.1f}%"
                })

        return {
            "needs_rebalancing": len(recommendations) > 0,
            "recommendations": recommendations,
            "current_allocation": current_allocation,
            "target_allocation": target_allocation
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of portfolio status."""
        metrics = self.calculate_metrics()

        return {
            "trades_total": len(self.trade_history),
            "performance": metrics.to_dict(),
            "equity_history_length": len(self.equity_history),
            "peak_equity": float(self.peak_equity),
            "initial_capital": float(self.initial_capital) if self.initial_capital else None
        }
