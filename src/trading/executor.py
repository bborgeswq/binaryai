"""
Trade Executor
Handles safe execution of trades with risk management integration
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum
from loguru import logger

from src.broker import BaseBroker, Order, OrderSide, OrderType, OrderStatus
from .risk_manager import RiskManager, RiskAssessment


class ExecutionStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    REJECTED = "rejected"
    FAILED = "failed"
    RISK_BLOCKED = "risk_blocked"


@dataclass
class ExecutionResult:
    """Result of trade execution"""
    status: ExecutionStatus
    order: Optional[Order] = None
    risk_assessment: Optional[RiskAssessment] = None
    message: str = ""
    executed_quantity: Decimal = Decimal("0")
    executed_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "order_id": self.order.id if self.order else None,
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "message": self.message,
            "executed_quantity": float(self.executed_quantity),
            "executed_price": self.executed_price,
            "timestamp": str(self.timestamp)
        }


class TradeExecutor:
    """
    Executes trades with risk management integration.
    Ensures all trades pass risk checks before execution.
    """

    def __init__(
            self,
            broker: BaseBroker,
            risk_manager: RiskManager,
            require_stop_loss: bool = True,
            use_limit_orders: bool = False,
            slippage_tolerance: float = 0.005  # 0.5%
    ):
        """
        Initialize trade executor.

        Args:
            broker: Broker for trade execution
            risk_manager: Risk manager for validation
            require_stop_loss: Require stop loss on all trades
            use_limit_orders: Use limit orders instead of market
            slippage_tolerance: Max acceptable slippage
        """
        self.broker = broker
        self.risk_manager = risk_manager
        self.require_stop_loss = require_stop_loss
        self.use_limit_orders = use_limit_orders
        self.slippage_tolerance = slippage_tolerance

        # Execution history
        self.execution_history: List[ExecutionResult] = []

        logger.info("Trade Executor initialized")

    async def execute_trade(
            self,
            symbol: str,
            side: str,  # "buy" or "sell"
            quantity: Decimal,
            entry_price: float,
            stop_loss: Optional[float] = None,
            take_profit: Optional[float] = None,
            portfolio_value: Optional[Decimal] = None,
            skip_risk_check: bool = False
    ) -> ExecutionResult:
        """
        Execute a trade with full risk management.

        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Quantity to trade
            entry_price: Expected entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            portfolio_value: Current portfolio value
            skip_risk_check: Skip risk validation (dangerous!)

        Returns:
            ExecutionResult with status and details
        """
        # Validate stop loss requirement
        if self.require_stop_loss and not stop_loss:
            return ExecutionResult(
                status=ExecutionStatus.REJECTED,
                message="Stop loss required but not provided"
            )

        # Get current state for risk assessment
        current_positions = []
        open_orders = []

        try:
            positions = await self.broker.get_positions()
            current_positions = [
                {"symbol": p.symbol, "side": p.side.value, "quantity": float(p.quantity)}
                for p in positions
            ]

            orders = await self.broker.get_open_orders()
            open_orders = [
                {"symbol": o.symbol, "side": o.side.value, "quantity": float(o.quantity)}
                for o in orders
            ]
        except Exception as e:
            logger.warning(f"Failed to get current state: {e}")

        # Get portfolio value if not provided
        if not portfolio_value:
            try:
                account = await self.broker.get_account()
                portfolio_value = account.equity
            except Exception as e:
                logger.error(f"Failed to get portfolio value: {e}")
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    message=f"Failed to get portfolio value: {e}"
                )

        # Risk assessment
        risk_assessment = None
        if not skip_risk_check:
            risk_assessment = self.risk_manager.assess_trade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                portfolio_value=portfolio_value,
                current_positions=current_positions,
                open_orders=open_orders
            )

            if not risk_assessment.approved:
                logger.warning(f"Trade blocked by risk manager: {risk_assessment.warnings}")
                return ExecutionResult(
                    status=ExecutionStatus.RISK_BLOCKED,
                    risk_assessment=risk_assessment,
                    message=f"Risk check failed: {', '.join(risk_assessment.warnings)}"
                )

            # Use adjusted values from risk manager
            if risk_assessment.adjusted_size:
                quantity = risk_assessment.adjusted_size
            if risk_assessment.adjusted_stop_loss:
                stop_loss = risk_assessment.adjusted_stop_loss

        # Execute the trade
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            order_type = OrderType.LIMIT if self.use_limit_orders else OrderType.MARKET

            order = await self.broker.submit_order(
                symbol=symbol,
                side=order_side,
                quantity=quantity,
                order_type=order_type,
                limit_price=Decimal(str(entry_price)) if self.use_limit_orders else None
            )

            # Wait briefly for order status
            import asyncio
            await asyncio.sleep(0.5)

            # Check order status
            updated_order = await self.broker.get_order(order.id)
            if updated_order:
                order = updated_order

            if order.status == OrderStatus.FILLED:
                result = ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    order=order,
                    risk_assessment=risk_assessment,
                    message="Order filled successfully",
                    executed_quantity=order.filled_quantity,
                    executed_price=float(order.filled_avg_price) if order.filled_avg_price else entry_price
                )
            elif order.status == OrderStatus.PARTIALLY_FILLED:
                result = ExecutionResult(
                    status=ExecutionStatus.PARTIAL,
                    order=order,
                    risk_assessment=risk_assessment,
                    message=f"Order partially filled: {order.filled_quantity}/{quantity}",
                    executed_quantity=order.filled_quantity,
                    executed_price=float(order.filled_avg_price) if order.filled_avg_price else entry_price
                )
            elif order.status in [OrderStatus.REJECTED, OrderStatus.CANCELLED]:
                result = ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    order=order,
                    risk_assessment=risk_assessment,
                    message=f"Order rejected/cancelled: {order.status.value}"
                )
            else:
                result = ExecutionResult(
                    status=ExecutionStatus.SUCCESS,
                    order=order,
                    risk_assessment=risk_assessment,
                    message=f"Order submitted: {order.status.value}",
                    executed_quantity=quantity
                )

            self.execution_history.append(result)

            # Log execution
            logger.info(
                f"Trade executed: {side.upper()} {quantity} {symbol} "
                f"@ {entry_price} - {result.status.value}"
            )

            return result

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            result = ExecutionResult(
                status=ExecutionStatus.FAILED,
                risk_assessment=risk_assessment,
                message=f"Execution error: {str(e)}"
            )
            self.execution_history.append(result)
            return result

    async def close_position(
            self,
            symbol: str,
            reason: str = "signal"
    ) -> ExecutionResult:
        """
        Close an existing position.

        Args:
            symbol: Symbol to close
            reason: Reason for closing

        Returns:
            ExecutionResult
        """
        try:
            position = await self.broker.get_position(symbol)
            if not position:
                return ExecutionResult(
                    status=ExecutionStatus.REJECTED,
                    message=f"No position found for {symbol}"
                )

            order = await self.broker.close_position(symbol)

            # Record the trade result
            pnl = position.unrealized_pnl
            self.risk_manager.record_trade(pnl)

            result = ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                order=order,
                message=f"Position closed ({reason}): P&L = ${float(pnl):.2f}",
                executed_quantity=position.quantity,
                executed_price=float(position.current_price)
            )

            self.execution_history.append(result)
            logger.info(f"Position closed: {symbol} - P&L: ${float(pnl):.2f} ({reason})")

            return result

        except Exception as e:
            logger.error(f"Failed to close position {symbol}: {e}")
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                message=f"Failed to close position: {str(e)}"
            )

    async def close_all_positions(self, reason: str = "manual") -> List[ExecutionResult]:
        """
        Close all open positions.

        Args:
            reason: Reason for closing

        Returns:
            List of ExecutionResults
        """
        results = []
        positions = await self.broker.get_positions()

        for position in positions:
            result = await self.close_position(position.symbol, reason)
            results.append(result)

        return results

    async def cancel_all_orders(self) -> int:
        """
        Cancel all open orders.

        Returns:
            Number of orders cancelled
        """
        cancelled = 0
        orders = await self.broker.get_open_orders()

        for order in orders:
            try:
                success = await self.broker.cancel_order(order.id)
                if success:
                    cancelled += 1
            except Exception as e:
                logger.warning(f"Failed to cancel order {order.id}: {e}")

        logger.info(f"Cancelled {cancelled} orders")
        return cancelled

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "success_rate": 0.0,
                "by_status": {}
            }

        total = len(self.execution_history)
        by_status = {}

        for result in self.execution_history:
            status = result.status.value
            by_status[status] = by_status.get(status, 0) + 1

        success_count = by_status.get("success", 0) + by_status.get("partial", 0)

        return {
            "total_executions": total,
            "success_rate": success_count / total if total > 0 else 0.0,
            "by_status": by_status
        }
