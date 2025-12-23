"""
Local Paper Trading Broker
Simulates trading without any API connection - for testing and development
"""
import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass
from loguru import logger

from .base import (
    BaseBroker, Order, Position, AccountInfo,
    OrderSide, OrderType, OrderStatus, PositionSide
)


@dataclass
class PriceProvider:
    """Simple price provider for paper trading"""
    prices: Dict[str, Decimal]

    def get_price(self, symbol: str) -> Decimal:
        return self.prices.get(symbol, Decimal("0"))

    def update_price(self, symbol: str, price: Decimal):
        self.prices[symbol] = price


class PaperTradingBroker(BaseBroker):
    """
    Local paper trading broker for testing and development.
    No API connection required - simulates all trading locally.
    """

    def __init__(
            self,
            initial_cash: Decimal = Decimal("10000"),
            price_provider: Optional[PriceProvider] = None
    ):
        """
        Initialize paper trading broker.

        Args:
            initial_cash: Starting cash balance
            price_provider: Optional custom price provider
        """
        super().__init__(paper_trading=True)

        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.price_provider = price_provider or PriceProvider({
            "BTC/USD": Decimal("45000"),
            "ETH/USD": Decimal("2500"),
            "AAPL": Decimal("175"),
            "TSLA": Decimal("250"),
        })

        # Storage
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Order] = []

        # Callbacks
        self.on_order_filled: Optional[Callable[[Order], None]] = None
        self.on_position_changed: Optional[Callable[[Position], None]] = None

    async def connect(self) -> bool:
        """Connect to paper trading (always succeeds)."""
        self._connected = True
        logger.info(f"Paper Trading initialized with ${float(self.cash):,.2f}")
        return True

    async def disconnect(self) -> None:
        """Disconnect from paper trading."""
        self._connected = False
        logger.info("Paper Trading disconnected")

    async def get_account(self) -> AccountInfo:
        """Get account information."""
        # Calculate total portfolio value
        positions_value = sum(
            p.market_value for p in self.positions.values()
        )
        equity = self.cash + positions_value

        return AccountInfo(
            account_id="paper-trading-001",
            equity=equity,
            cash=self.cash,
            buying_power=self.cash,  # Simple: buying power = cash
            portfolio_value=equity,
            currency="USD",
            pattern_day_trader=False,
            trading_blocked=False,
            transfers_blocked=False,
            account_blocked=False,
            created_at=datetime.now(),
            status="active"
        )

    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        # Update current prices
        for symbol, position in self.positions.items():
            await self._update_position_price(position)

        return list(self.positions.values())

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        position = self.positions.get(symbol)
        if position:
            await self._update_position_price(position)
        return position

    async def submit_order(
            self,
            symbol: str,
            side: OrderSide,
            quantity: Decimal,
            order_type: OrderType = OrderType.MARKET,
            limit_price: Optional[Decimal] = None,
            stop_price: Optional[Decimal] = None,
            time_in_force: str = "gtc",
            client_order_id: Optional[str] = None
    ) -> Order:
        """Submit a new order (executes immediately for market orders)."""
        order_id = str(uuid.uuid4())

        order = Order(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
            client_order_id=client_order_id or order_id
        )

        self.orders[order_id] = order

        # For market orders, execute immediately
        if order_type == OrderType.MARKET:
            await self._execute_order(order)
        else:
            order.status = OrderStatus.OPEN
            logger.info(f"Order placed: {side.value} {quantity} {symbol} @ {order_type.value}")

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        order = self.orders.get(order_id)
        if not order:
            return False

        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return False

        order.status = OrderStatus.CANCELLED
        logger.info(f"Order cancelled: {order_id}")
        return True

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders.get(order_id)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        open_orders = [
            o for o in self.orders.values()
            if o.status == OrderStatus.OPEN
        ]

        if symbol:
            open_orders = [o for o in open_orders if o.symbol == symbol]

        return open_orders

    async def close_position(self, symbol: str) -> Order:
        """Close an entire position."""
        position = self.positions.get(symbol)
        if not position:
            raise ValueError(f"No position found for {symbol}")

        # Create closing order (opposite side)
        side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY

        order = await self.submit_order(
            symbol=symbol,
            side=side,
            quantity=position.quantity,
            order_type=OrderType.MARKET
        )

        return order

    async def close_all_positions(self) -> List[Order]:
        """Close all open positions."""
        orders = []
        for symbol in list(self.positions.keys()):
            order = await self.close_position(symbol)
            orders.append(order)
        return orders

    # Internal methods
    async def _execute_order(self, order: Order):
        """Execute an order (fill it)."""
        current_price = self.price_provider.get_price(order.symbol)
        if current_price == 0:
            order.status = OrderStatus.REJECTED
            logger.error(f"Order rejected: No price available for {order.symbol}")
            return

        total_cost = current_price * order.quantity

        # Check if we have enough cash for buy orders
        if order.side == OrderSide.BUY:
            if total_cost > self.cash:
                order.status = OrderStatus.REJECTED
                logger.error(f"Order rejected: Insufficient funds")
                return

            # Deduct cash
            self.cash -= total_cost

            # Update or create position
            await self._add_to_position(order.symbol, order.quantity, current_price)

        else:  # SELL
            position = self.positions.get(order.symbol)
            if not position or position.quantity < order.quantity:
                order.status = OrderStatus.REJECTED
                logger.error(f"Order rejected: Insufficient position")
                return

            # Add cash
            self.cash += total_cost

            # Update position
            await self._remove_from_position(order.symbol, order.quantity)

        # Mark order as filled
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        order.filled_quantity = order.quantity
        order.filled_avg_price = current_price

        self.trade_history.append(order)

        logger.info(
            f"Order filled: {order.side.value} {order.quantity} {order.symbol} "
            f"@ ${float(current_price):,.2f}"
        )

        if self.on_order_filled:
            self.on_order_filled(order)

    async def _add_to_position(self, symbol: str, quantity: Decimal, price: Decimal):
        """Add to a position or create new one."""
        if symbol in self.positions:
            position = self.positions[symbol]
            # Average the entry price
            total_qty = position.quantity + quantity
            total_cost = (position.entry_price * position.quantity) + (price * quantity)
            position.entry_price = total_cost / total_qty
            position.quantity = total_qty
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                side=PositionSide.LONG,
                entry_price=price,
                current_price=price,
                market_value=quantity * price,
                unrealized_pnl=Decimal("0"),
                unrealized_pnl_pct=0.0,
                cost_basis=quantity * price,
                created_at=datetime.now()
            )

        await self._update_position_price(self.positions[symbol])

        if self.on_position_changed:
            self.on_position_changed(self.positions[symbol])

    async def _remove_from_position(self, symbol: str, quantity: Decimal):
        """Remove from a position."""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]
        position.quantity -= quantity

        if position.quantity <= 0:
            del self.positions[symbol]
        else:
            await self._update_position_price(position)
            if self.on_position_changed:
                self.on_position_changed(position)

    async def _update_position_price(self, position: Position):
        """Update position with current price."""
        current_price = self.price_provider.get_price(position.symbol)
        if current_price > 0:
            position.current_price = current_price
            position.market_value = position.quantity * current_price
            position.unrealized_pnl = position.market_value - position.cost_basis
            if position.cost_basis > 0:
                position.unrealized_pnl_pct = float(
                    (position.unrealized_pnl / position.cost_basis) * 100
                )

    def update_price(self, symbol: str, price: Decimal):
        """Update price for a symbol (for simulation)."""
        self.price_provider.update_price(symbol, price)

    def get_trade_history(self) -> List[Order]:
        """Get all executed trades."""
        return self.trade_history.copy()

    def get_pnl(self) -> Dict[str, Decimal]:
        """Get profit/loss statistics."""
        positions_pnl = sum(
            p.unrealized_pnl for p in self.positions.values()
        )

        realized_pnl = Decimal("0")
        for order in self.trade_history:
            if order.side == OrderSide.SELL and order.filled_avg_price:
                # Simplified - doesn't account for entry price perfectly
                pass

        return {
            "unrealized_pnl": positions_pnl,
            "realized_pnl": realized_pnl,
            "total_pnl": self.cash + sum(p.market_value for p in self.positions.values()) - self.initial_cash,
            "equity": self.cash + sum(p.market_value for p in self.positions.values()),
            "cash": self.cash,
        }
