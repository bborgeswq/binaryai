"""
Binance Exchange Broker Implementation
Supports crypto trading with testnet and live modes via CCXT
"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from loguru import logger

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    logger.warning("CCXT not installed. Run: pip install ccxt")

from .base import (
    BaseBroker, Order, Position, AccountInfo,
    OrderSide, OrderType, OrderStatus, PositionSide
)


class BinanceBroker(BaseBroker):
    """
    Binance exchange broker implementation using CCXT.
    Supports both testnet (paper) and live trading.
    """

    def __init__(
            self,
            api_key: str,
            secret_key: str,
            testnet: bool = True
    ):
        """
        Initialize Binance broker.

        Args:
            api_key: Binance API key
            secret_key: Binance secret key
            testnet: Use testnet (True) or live (False)
        """
        super().__init__(paper_trading=testnet)

        if not CCXT_AVAILABLE:
            raise ImportError("CCXT not installed. Run: pip install ccxt")

        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet

        # Initialize CCXT Binance client
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': testnet,  # Use testnet
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # spot trading
                'adjustForTimeDifference': True,
            }
        })

        if testnet:
            self.exchange.set_sandbox_mode(True)

        self.client = self.exchange
        logger.info(f"Binance Broker initialized ({'TESTNET' if testnet else 'LIVE'})")

    async def connect(self) -> bool:
        """Connect to Binance API."""
        try:
            # Test connection by fetching balance
            balance = self.exchange.fetch_balance()
            self._connected = True

            mode = "TESTNET" if self.testnet else "LIVE"
            logger.info(f"Connected to Binance [{mode}]")

            # Log available balance
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            btc_balance = balance.get('BTC', {}).get('free', 0)
            logger.info(f"Balance: {usdt_balance} USDT, {btc_balance} BTC")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Binance API."""
        self._connected = False
        logger.info("Disconnected from Binance")

    async def get_account(self) -> AccountInfo:
        """Get account information."""
        self._ensure_connected()

        try:
            balance = self.exchange.fetch_balance()

            # Calculate total equity in USDT
            total_usdt = Decimal("0")
            for currency, amounts in balance.get('total', {}).items():
                if amounts and amounts > 0:
                    if currency == 'USDT':
                        total_usdt += Decimal(str(amounts))
                    else:
                        # Convert to USDT
                        try:
                            ticker = self.exchange.fetch_ticker(f"{currency}/USDT")
                            price = Decimal(str(ticker['last']))
                            total_usdt += Decimal(str(amounts)) * price
                        except:
                            pass

            usdt_free = Decimal(str(balance.get('USDT', {}).get('free', 0)))

            return AccountInfo(
                account_id="binance-" + ("testnet" if self.testnet else "live"),
                equity=total_usdt,
                cash=usdt_free,
                buying_power=usdt_free,
                portfolio_value=total_usdt,
                currency="USDT",
                pattern_day_trader=False,
                trading_blocked=False,
                transfers_blocked=False,
                account_blocked=False,
                created_at=datetime.now(),
                status="active"
            )

        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            raise

    async def get_positions(self) -> List[Position]:
        """Get all open positions (non-zero balances)."""
        self._ensure_connected()

        positions = []
        try:
            balance = self.exchange.fetch_balance()

            for currency, amounts in balance.get('total', {}).items():
                if currency == 'USDT' or not amounts or amounts <= 0.00001:
                    continue

                try:
                    symbol = f"{currency}/USDT"
                    ticker = self.exchange.fetch_ticker(symbol)
                    current_price = Decimal(str(ticker['last']))
                    quantity = Decimal(str(amounts))
                    market_value = quantity * current_price

                    # We don't have entry price from Binance API, estimate from avg
                    positions.append(Position(
                        symbol=symbol,
                        quantity=quantity,
                        side=PositionSide.LONG,
                        entry_price=current_price,  # Approximation
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=Decimal("0"),  # Can't calculate without entry
                        unrealized_pnl_pct=0.0,
                        cost_basis=market_value,
                        created_at=datetime.now()
                    ))
                except Exception as e:
                    logger.debug(f"Skipping {currency}: {e}")

            return positions

        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        positions = await self.get_positions()
        for p in positions:
            if p.symbol == symbol:
                return p
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

        try:
            # Convert to CCXT format
            ccxt_side = 'buy' if side == OrderSide.BUY else 'sell'
            ccxt_type = 'market' if order_type == OrderType.MARKET else 'limit'

            # Prepare order params
            params = {}
            if client_order_id:
                params['clientOrderId'] = client_order_id

            # Submit order
            if ccxt_type == 'market':
                ccxt_order = self.exchange.create_order(
                    symbol=symbol,
                    type=ccxt_type,
                    side=ccxt_side,
                    amount=float(quantity),
                    params=params
                )
            else:
                ccxt_order = self.exchange.create_order(
                    symbol=symbol,
                    type=ccxt_type,
                    side=ccxt_side,
                    amount=float(quantity),
                    price=float(limit_price),
                    params=params
                )

            order = self._convert_order(ccxt_order)
            logger.info(f"Order submitted: {side.value} {quantity} {symbol}")
            return order

        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        self._ensure_connected()

        try:
            # Need symbol to cancel - try to get from open orders
            open_orders = self.exchange.fetch_open_orders()
            for order in open_orders:
                if order['id'] == order_id:
                    self.exchange.cancel_order(order_id, order['symbol'])
                    logger.info(f"Order cancelled: {order_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        self._ensure_connected()

        try:
            # Binance needs symbol to fetch order
            # Try common symbols
            for symbol in ['BTC/USDT', 'ETH/USDT']:
                try:
                    ccxt_order = self.exchange.fetch_order(order_id, symbol)
                    return self._convert_order(ccxt_order)
                except:
                    continue
            return None
        except Exception as e:
            logger.error(f"Failed to get order: {e}")
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all open orders."""
        self._ensure_connected()

        try:
            ccxt_orders = self.exchange.fetch_open_orders(symbol)
            return [self._convert_order(o) for o in ccxt_orders]
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []

    async def close_position(self, symbol: str) -> Order:
        """Close an entire position by selling."""
        self._ensure_connected()

        position = await self.get_position(symbol)
        if not position:
            raise ValueError(f"No position found for {symbol}")

        # Sell all
        return await self.submit_order(
            symbol=symbol,
            side=OrderSide.SELL,
            quantity=position.quantity,
            order_type=OrderType.MARKET
        )

    async def close_all_positions(self) -> List[Order]:
        """Close all open positions."""
        self._ensure_connected()

        orders = []
        positions = await self.get_positions()

        for position in positions:
            try:
                order = await self.close_position(position.symbol)
                orders.append(order)
            except Exception as e:
                logger.error(f"Failed to close {position.symbol}: {e}")

        return orders

    # Market Data Methods
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker data."""
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Failed to get ticker: {e}")
            return {}

    async def get_ohlcv(
            self,
            symbol: str,
            timeframe: str = '1h',
            limit: int = 100
    ) -> List[List]:
        """Get OHLCV candlestick data."""
        try:
            return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as e:
            logger.error(f"Failed to get OHLCV: {e}")
            return []

    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book."""
        try:
            return self.exchange.fetch_order_book(symbol, limit)
        except Exception as e:
            logger.error(f"Failed to get order book: {e}")
            return {'bids': [], 'asks': []}

    # Helper methods
    def _ensure_connected(self):
        """Ensure we're connected."""
        if not self._connected:
            raise ConnectionError("Not connected to Binance. Call connect() first.")

    def _convert_order(self, ccxt_order: Dict) -> Order:
        """Convert CCXT order to our Order format."""
        status_map = {
            'open': OrderStatus.OPEN,
            'closed': OrderStatus.FILLED,
            'canceled': OrderStatus.CANCELLED,
            'expired': OrderStatus.EXPIRED,
            'rejected': OrderStatus.REJECTED,
        }

        side = OrderSide.BUY if ccxt_order['side'] == 'buy' else OrderSide.SELL

        type_map = {
            'market': OrderType.MARKET,
            'limit': OrderType.LIMIT,
            'stop': OrderType.STOP,
            'stop_limit': OrderType.STOP_LIMIT,
        }

        return Order(
            id=str(ccxt_order['id']),
            symbol=ccxt_order['symbol'],
            side=side,
            order_type=type_map.get(ccxt_order['type'], OrderType.MARKET),
            quantity=Decimal(str(ccxt_order['amount'])) if ccxt_order['amount'] else Decimal("0"),
            status=status_map.get(ccxt_order['status'], OrderStatus.PENDING),
            created_at=datetime.fromtimestamp(ccxt_order['timestamp'] / 1000) if ccxt_order.get('timestamp') else datetime.now(),
            filled_at=datetime.fromtimestamp(ccxt_order['lastTradeTimestamp'] / 1000) if ccxt_order.get('lastTradeTimestamp') else None,
            limit_price=Decimal(str(ccxt_order['price'])) if ccxt_order.get('price') else None,
            filled_quantity=Decimal(str(ccxt_order['filled'])) if ccxt_order.get('filled') else Decimal("0"),
            filled_avg_price=Decimal(str(ccxt_order['average'])) if ccxt_order.get('average') else None,
            client_order_id=ccxt_order.get('clientOrderId')
        )
