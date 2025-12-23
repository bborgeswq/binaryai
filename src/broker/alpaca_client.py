"""
Alpaca Markets Broker Implementation
Supports both stocks and crypto trading with paper trading mode
"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from loguru import logger

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        MarketOrderRequest, LimitOrderRequest, StopOrderRequest,
        StopLimitOrderRequest, TrailingStopOrderRequest,
        GetOrdersRequest, ClosePositionRequest
    )
    from alpaca.trading.enums import (
        OrderSide as AlpacaOrderSide,
        OrderType as AlpacaOrderType,
        TimeInForce, OrderStatus as AlpacaOrderStatus,
        QueryOrderStatus
    )
    from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
    from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logger.warning("Alpaca SDK not installed. Run: pip install alpaca-trade-api")

from .base import (
    BaseBroker, Order, Position, AccountInfo,
    OrderSide, OrderType, OrderStatus, PositionSide
)


class AlpacaBroker(BaseBroker):
    """
    Alpaca Markets broker implementation.
    Supports stocks and crypto trading with paper trading mode.
    """

    # Mapping from our enums to Alpaca's
    SIDE_MAP = {
        OrderSide.BUY: AlpacaOrderSide.BUY if ALPACA_AVAILABLE else "buy",
        OrderSide.SELL: AlpacaOrderSide.SELL if ALPACA_AVAILABLE else "sell"
    }

    STATUS_MAP = {
        "new": OrderStatus.OPEN,
        "partially_filled": OrderStatus.PARTIALLY_FILLED,
        "filled": OrderStatus.FILLED,
        "canceled": OrderStatus.CANCELLED,
        "cancelled": OrderStatus.CANCELLED,
        "expired": OrderStatus.EXPIRED,
        "rejected": OrderStatus.REJECTED,
        "pending_new": OrderStatus.PENDING,
        "accepted": OrderStatus.OPEN,
        "pending_cancel": OrderStatus.OPEN,
        "pending_replace": OrderStatus.OPEN,
        "stopped": OrderStatus.FILLED,
        "suspended": OrderStatus.OPEN,
        "calculated": OrderStatus.OPEN,
    }

    def __init__(
            self,
            api_key: str,
            secret_key: str,
            paper_trading: bool = True
    ):
        """
        Initialize Alpaca broker.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper_trading: Use paper trading mode
        """
        super().__init__(paper_trading)

        if not ALPACA_AVAILABLE:
            raise ImportError("Alpaca SDK not installed. Run: pip install alpaca-trade-api")

        self.api_key = api_key
        self.secret_key = secret_key

        # Initialize clients
        self.trading_client: Optional[TradingClient] = None
        self.crypto_data_client: Optional[CryptoHistoricalDataClient] = None
        self.stock_data_client: Optional[StockHistoricalDataClient] = None

    async def connect(self) -> bool:
        """Connect to Alpaca API."""
        try:
            # Trading client
            self.trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper=self.paper_trading
            )

            # Data clients (no auth needed for crypto)
            self.crypto_data_client = CryptoHistoricalDataClient()
            self.stock_data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.secret_key
            )

            # Test connection
            account = self.trading_client.get_account()
            self._connected = True

            mode = "PAPER" if self.paper_trading else "LIVE"
            logger.info(f"Connected to Alpaca [{mode}] - Account: {account.account_number}")
            logger.info(f"Equity: ${float(account.equity):,.2f} | Cash: ${float(account.cash):,.2f}")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Alpaca API."""
        self.trading_client = None
        self.crypto_data_client = None
        self.stock_data_client = None
        self._connected = False
        logger.info("Disconnected from Alpaca")

    async def get_account(self) -> AccountInfo:
        """Get account information."""
        self._ensure_connected()

        account = self.trading_client.get_account()

        return AccountInfo(
            account_id=account.account_number,
            equity=Decimal(str(account.equity)),
            cash=Decimal(str(account.cash)),
            buying_power=Decimal(str(account.buying_power)),
            portfolio_value=Decimal(str(account.portfolio_value)),
            currency=account.currency,
            pattern_day_trader=account.pattern_day_trader,
            trading_blocked=account.trading_blocked,
            transfers_blocked=account.transfers_blocked,
            account_blocked=account.account_blocked,
            created_at=account.created_at,
            status=account.status.value if hasattr(account.status, 'value') else str(account.status)
        )

    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        self._ensure_connected()

        positions = self.trading_client.get_all_positions()
        return [self._convert_position(p) for p in positions]

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        self._ensure_connected()

        try:
            # Alpaca uses different symbol format for crypto
            alpaca_symbol = self._to_alpaca_symbol(symbol)
            position = self.trading_client.get_open_position(alpaca_symbol)
            return self._convert_position(position)
        except Exception:
            return None

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
        """Submit a new order."""
        self._ensure_connected()

        alpaca_symbol = self._to_alpaca_symbol(symbol)
        alpaca_side = self.SIDE_MAP[side]
        tif = self._get_time_in_force(time_in_force)

        # Build order request based on type
        if order_type == OrderType.MARKET:
            order_request = MarketOrderRequest(
                symbol=alpaca_symbol,
                qty=float(quantity),
                side=alpaca_side,
                time_in_force=tif,
                client_order_id=client_order_id
            )
        elif order_type == OrderType.LIMIT:
            order_request = LimitOrderRequest(
                symbol=alpaca_symbol,
                qty=float(quantity),
                side=alpaca_side,
                time_in_force=tif,
                limit_price=float(limit_price),
                client_order_id=client_order_id
            )
        elif order_type == OrderType.STOP:
            order_request = StopOrderRequest(
                symbol=alpaca_symbol,
                qty=float(quantity),
                side=alpaca_side,
                time_in_force=tif,
                stop_price=float(stop_price),
                client_order_id=client_order_id
            )
        elif order_type == OrderType.STOP_LIMIT:
            order_request = StopLimitOrderRequest(
                symbol=alpaca_symbol,
                qty=float(quantity),
                side=alpaca_side,
                time_in_force=tif,
                limit_price=float(limit_price),
                stop_price=float(stop_price),
                client_order_id=client_order_id
            )
        elif order_type == OrderType.TRAILING_STOP:
            order_request = TrailingStopOrderRequest(
                symbol=alpaca_symbol,
                qty=float(quantity),
                side=alpaca_side,
                time_in_force=tif,
                trail_percent=float(stop_price) if stop_price else 2.0,
                client_order_id=client_order_id
            )
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        # Submit order
        alpaca_order = self.trading_client.submit_order(order_request)

        order = self._convert_order(alpaca_order, symbol)
        logger.info(f"Order submitted: {side.value} {quantity} {symbol} @ {order_type.value}")

        return order

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        self._ensure_connected()

        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        self._ensure_connected()

        try:
            alpaca_order = self.trading_client.get_order_by_id(order_id)
            return self._convert_order(alpaca_order)
        except Exception:
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        self._ensure_connected()

        request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
        if symbol:
            request.symbols = [self._to_alpaca_symbol(symbol)]

        orders = self.trading_client.get_orders(request)
        return [self._convert_order(o) for o in orders]

    async def close_position(self, symbol: str) -> Order:
        """Close an entire position."""
        self._ensure_connected()

        alpaca_symbol = self._to_alpaca_symbol(symbol)
        alpaca_order = self.trading_client.close_position(alpaca_symbol)

        logger.info(f"Position closed: {symbol}")
        return self._convert_order(alpaca_order, symbol)

    async def close_all_positions(self) -> List[Order]:
        """Close all open positions."""
        self._ensure_connected()

        responses = self.trading_client.close_all_positions(cancel_orders=True)
        orders = []

        for response in responses:
            if hasattr(response, 'body') and response.body:
                orders.append(self._convert_order(response.body))

        logger.info(f"Closed {len(orders)} positions")
        return orders

    # Helper methods
    def _ensure_connected(self):
        """Ensure we're connected to the broker."""
        if not self._connected or not self.trading_client:
            raise ConnectionError("Not connected to Alpaca. Call connect() first.")

    def _to_alpaca_symbol(self, symbol: str) -> str:
        """Convert our symbol format to Alpaca's format."""
        # Crypto: BTC/USD -> BTCUSD (Alpaca crypto format)
        # Stocks: AAPL -> AAPL (no change)
        if "/" in symbol:
            return symbol.replace("/", "")
        return symbol

    def _from_alpaca_symbol(self, alpaca_symbol: str) -> str:
        """Convert Alpaca symbol format to ours."""
        # Crypto: BTCUSD -> BTC/USD
        if alpaca_symbol.endswith("USD") and len(alpaca_symbol) > 3:
            base = alpaca_symbol[:-3]
            if base in ["BTC", "ETH", "LTC", "BCH", "DOGE", "SHIB", "AVAX", "DOT", "LINK", "UNI"]:
                return f"{base}/USD"
        return alpaca_symbol

    def _get_time_in_force(self, tif: str) -> TimeInForce:
        """Convert time in force string to Alpaca enum."""
        tif_map = {
            "gtc": TimeInForce.GTC,
            "day": TimeInForce.DAY,
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK,
        }
        return tif_map.get(tif.lower(), TimeInForce.GTC)

    def _convert_order(self, alpaca_order, original_symbol: Optional[str] = None) -> Order:
        """Convert Alpaca order to our Order object."""
        symbol = original_symbol or self._from_alpaca_symbol(alpaca_order.symbol)

        status_str = alpaca_order.status.value if hasattr(alpaca_order.status, 'value') else str(alpaca_order.status)
        status = self.STATUS_MAP.get(status_str.lower(), OrderStatus.PENDING)

        side = OrderSide.BUY if alpaca_order.side.value == "buy" else OrderSide.SELL

        order_type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT,
            "trailing_stop": OrderType.TRAILING_STOP,
        }
        order_type_str = alpaca_order.type.value if hasattr(alpaca_order.type, 'value') else str(alpaca_order.type)
        order_type = order_type_map.get(order_type_str.lower(), OrderType.MARKET)

        return Order(
            id=str(alpaca_order.id),
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=Decimal(str(alpaca_order.qty)) if alpaca_order.qty else Decimal("0"),
            status=status,
            created_at=alpaca_order.created_at,
            filled_at=alpaca_order.filled_at,
            limit_price=Decimal(str(alpaca_order.limit_price)) if alpaca_order.limit_price else None,
            stop_price=Decimal(str(alpaca_order.stop_price)) if alpaca_order.stop_price else None,
            filled_quantity=Decimal(str(alpaca_order.filled_qty)) if alpaca_order.filled_qty else Decimal("0"),
            filled_avg_price=Decimal(str(alpaca_order.filled_avg_price)) if alpaca_order.filled_avg_price else None,
            time_in_force=alpaca_order.time_in_force.value if hasattr(alpaca_order.time_in_force, 'value') else "gtc",
            client_order_id=alpaca_order.client_order_id
        )

    def _convert_position(self, alpaca_position) -> Position:
        """Convert Alpaca position to our Position object."""
        symbol = self._from_alpaca_symbol(alpaca_position.symbol)

        qty = Decimal(str(alpaca_position.qty))
        side = PositionSide.LONG if qty > 0 else PositionSide.SHORT

        return Position(
            symbol=symbol,
            quantity=abs(qty),
            side=side,
            entry_price=Decimal(str(alpaca_position.avg_entry_price)),
            current_price=Decimal(str(alpaca_position.current_price)),
            market_value=Decimal(str(alpaca_position.market_value)),
            unrealized_pnl=Decimal(str(alpaca_position.unrealized_pl)),
            unrealized_pnl_pct=float(alpaca_position.unrealized_plpc) * 100,
            cost_basis=Decimal(str(alpaca_position.cost_basis))
        )
