"""
Base broker interface - Abstract class for all broker implementations
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from decimal import Decimal


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Order:
    """Represents a trading order"""
    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime] = None
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    filled_quantity: Decimal = Decimal("0")
    filled_avg_price: Optional[Decimal] = None
    time_in_force: str = "gtc"  # good till cancelled
    client_order_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    quantity: Decimal
    side: PositionSide
    entry_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pnl_pct: float
    cost_basis: Decimal
    created_at: Optional[datetime] = None

    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0


@dataclass
class AccountInfo:
    """Account information"""
    account_id: str
    equity: Decimal
    cash: Decimal
    buying_power: Decimal
    portfolio_value: Decimal
    currency: str = "USD"
    pattern_day_trader: bool = False
    trading_blocked: bool = False
    transfers_blocked: bool = False
    account_blocked: bool = False
    created_at: Optional[datetime] = None
    status: str = "active"


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.
    Provides a unified interface for trading operations.
    """

    def __init__(self, paper_trading: bool = True):
        """
        Initialize the broker.

        Args:
            paper_trading: If True, use paper trading mode
        """
        self.paper_trading = paper_trading
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to the broker API.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the broker API."""
        pass

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """
        Get account information.

        Returns:
            AccountInfo object
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List of Position objects
        """
        pass

    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position if exists, None otherwise
        """
        pass

    @abstractmethod
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
        """
        Submit a new order.

        Args:
            symbol: Trading symbol
            side: Buy or Sell
            quantity: Amount to trade
            order_type: Type of order
            limit_price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            time_in_force: Order duration
            client_order_id: Custom order ID

        Returns:
            Order object
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancelled successfully
        """
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order if exists
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get all open orders.

        Args:
            symbol: Filter by symbol (optional)

        Returns:
            List of open orders
        """
        pass

    @abstractmethod
    async def close_position(self, symbol: str) -> Order:
        """
        Close an entire position.

        Args:
            symbol: Symbol to close

        Returns:
            Order for the closing trade
        """
        pass

    @abstractmethod
    async def close_all_positions(self) -> List[Order]:
        """
        Close all open positions.

        Returns:
            List of closing orders
        """
        pass

    # Convenience methods
    async def buy(
            self,
            symbol: str,
            quantity: Decimal,
            order_type: OrderType = OrderType.MARKET,
            **kwargs
    ) -> Order:
        """Submit a buy order."""
        return await self.submit_order(
            symbol=symbol,
            side=OrderSide.BUY,
            quantity=quantity,
            order_type=order_type,
            **kwargs
        )

    async def sell(
            self,
            symbol: str,
            quantity: Decimal,
            order_type: OrderType = OrderType.MARKET,
            **kwargs
    ) -> Order:
        """Submit a sell order."""
        return await self.submit_order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=quantity,
            order_type=order_type,
            **kwargs
        )
