"""
Market Data Provider
Unified interface for getting market data from multiple sources
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
import pandas as pd
from loguru import logger

# Try importing data sources
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

try:
    from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
    from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest, CryptoLatestQuoteRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    ALPACA_DATA_AVAILABLE = True
except ImportError:
    ALPACA_DATA_AVAILABLE = False


class TimeframeEnum(Enum):
    """Supported timeframes"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


@dataclass
class OHLCV:
    """OHLCV candle data"""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "open": float(self.open),
            "high": float(self.high),
            "low": float(self.low),
            "close": float(self.close),
            "volume": float(self.volume)
        }


@dataclass
class Ticker:
    """Current ticker/quote data"""
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    volume_24h: Decimal
    change_24h_pct: float
    timestamp: datetime

    @property
    def spread(self) -> Decimal:
        return self.ask - self.bid

    @property
    def spread_pct(self) -> float:
        if self.bid > 0:
            return float((self.spread / self.bid) * 100)
        return 0.0

    @property
    def mid_price(self) -> Decimal:
        return (self.bid + self.ask) / 2


class MarketDataProvider:
    """
    Unified market data provider.
    Fetches data from multiple sources: Alpaca, Yahoo Finance, CCXT exchanges.
    """

    def __init__(
            self,
            alpaca_api_key: Optional[str] = None,
            alpaca_secret_key: Optional[str] = None,
            preferred_source: Literal["alpaca", "yfinance", "ccxt"] = "alpaca"
    ):
        """
        Initialize market data provider.

        Args:
            alpaca_api_key: Alpaca API key
            alpaca_secret_key: Alpaca secret key
            preferred_source: Preferred data source
        """
        self.preferred_source = preferred_source

        # Initialize Alpaca clients
        self.alpaca_crypto_client = None
        self.alpaca_stock_client = None
        if ALPACA_DATA_AVAILABLE:
            self.alpaca_crypto_client = CryptoHistoricalDataClient()
            if alpaca_api_key and alpaca_secret_key:
                self.alpaca_stock_client = StockHistoricalDataClient(
                    api_key=alpaca_api_key,
                    secret_key=alpaca_secret_key
                )

        # Initialize CCXT exchange (Binance for crypto)
        self.ccxt_exchange = None
        if CCXT_AVAILABLE:
            self.ccxt_exchange = ccxt.binance({
                'enableRateLimit': True,
            })

        # Cache
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # seconds

    async def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading symbol (e.g., "BTC/USD", "AAPL")

        Returns:
            Current price or None
        """
        ticker = await self.get_ticker(symbol)
        return ticker.last if ticker else None

    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """
        Get current ticker/quote data.

        Args:
            symbol: Trading symbol

        Returns:
            Ticker data
        """
        try:
            if self._is_crypto(symbol):
                return await self._get_crypto_ticker(symbol)
            else:
                return await self._get_stock_ticker(symbol)
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")
            return None

    async def get_ohlcv(
            self,
            symbol: str,
            timeframe: str = "1h",
            limit: int = 100,
            start: Optional[datetime] = None,
            end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get OHLCV candlestick data.

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            limit: Number of candles
            start: Start datetime
            end: End datetime

        Returns:
            DataFrame with OHLCV data
        """
        try:
            if self._is_crypto(symbol):
                return await self._get_crypto_ohlcv(symbol, timeframe, limit, start, end)
            else:
                return await self._get_stock_ohlcv(symbol, timeframe, limit, start, end)
        except Exception as e:
            logger.error(f"Error getting OHLCV for {symbol}: {e}")
            return pd.DataFrame()

    async def get_multiple_ohlcv(
            self,
            symbols: List[str],
            timeframe: str = "1h",
            limit: int = 100
    ) -> Dict[str, pd.DataFrame]:
        """
        Get OHLCV data for multiple symbols.

        Args:
            symbols: List of symbols
            timeframe: Candle timeframe
            limit: Number of candles

        Returns:
            Dict mapping symbol to DataFrame
        """
        results = {}
        tasks = [self.get_ohlcv(s, timeframe, limit) for s in symbols]
        data = await asyncio.gather(*tasks)

        for symbol, df in zip(symbols, data):
            results[symbol] = df

        return results

    # Private methods
    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is crypto."""
        # Crypto symbols typically have "/" or common crypto bases
        if "/" in symbol:
            return True
        crypto_bases = ["BTC", "ETH", "LTC", "XRP", "DOGE", "SOL", "ADA", "DOT", "AVAX"]
        return any(symbol.startswith(base) for base in crypto_bases)

    def _get_alpaca_timeframe(self, timeframe: str) -> Any:
        """Convert timeframe string to Alpaca TimeFrame."""
        if not ALPACA_DATA_AVAILABLE:
            return None

        tf_map = {
            "1m": TimeFrame(1, TimeFrameUnit.Minute),
            "5m": TimeFrame(5, TimeFrameUnit.Minute),
            "15m": TimeFrame(15, TimeFrameUnit.Minute),
            "30m": TimeFrame(30, TimeFrameUnit.Minute),
            "1h": TimeFrame(1, TimeFrameUnit.Hour),
            "4h": TimeFrame(4, TimeFrameUnit.Hour),
            "1d": TimeFrame(1, TimeFrameUnit.Day),
            "1w": TimeFrame(1, TimeFrameUnit.Week),
        }
        return tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Hour))

    async def _get_crypto_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get crypto ticker."""
        # Try CCXT first (more reliable for crypto)
        if CCXT_AVAILABLE and self.ccxt_exchange:
            try:
                ccxt_symbol = symbol.replace("/", "/")  # Already correct format
                ticker = self.ccxt_exchange.fetch_ticker(ccxt_symbol)
                return Ticker(
                    symbol=symbol,
                    bid=Decimal(str(ticker['bid'] or ticker['last'])),
                    ask=Decimal(str(ticker['ask'] or ticker['last'])),
                    last=Decimal(str(ticker['last'])),
                    volume_24h=Decimal(str(ticker['quoteVolume'] or 0)),
                    change_24h_pct=float(ticker['percentage'] or 0),
                    timestamp=datetime.now()
                )
            except Exception as e:
                logger.debug(f"CCXT ticker failed for {symbol}: {e}")

        # Fallback to Alpaca
        if ALPACA_DATA_AVAILABLE and self.alpaca_crypto_client:
            try:
                alpaca_symbol = symbol.replace("/", "")
                request = CryptoLatestQuoteRequest(symbol_or_symbols=[alpaca_symbol])
                quotes = self.alpaca_crypto_client.get_crypto_latest_quote(request)

                if alpaca_symbol in quotes:
                    quote = quotes[alpaca_symbol]
                    return Ticker(
                        symbol=symbol,
                        bid=Decimal(str(quote.bid_price)),
                        ask=Decimal(str(quote.ask_price)),
                        last=Decimal(str(quote.ask_price)),  # Use ask as last
                        volume_24h=Decimal("0"),
                        change_24h_pct=0.0,
                        timestamp=quote.timestamp
                    )
            except Exception as e:
                logger.debug(f"Alpaca ticker failed for {symbol}: {e}")

        return None

    async def _get_stock_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get stock ticker."""
        # Use yfinance
        if YFINANCE_AVAILABLE:
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                return Ticker(
                    symbol=symbol,
                    bid=Decimal(str(info.get('bid', info.get('regularMarketPrice', 0)))),
                    ask=Decimal(str(info.get('ask', info.get('regularMarketPrice', 0)))),
                    last=Decimal(str(info.get('regularMarketPrice', 0))),
                    volume_24h=Decimal(str(info.get('volume', 0))),
                    change_24h_pct=float(info.get('regularMarketChangePercent', 0)),
                    timestamp=datetime.now()
                )
            except Exception as e:
                logger.debug(f"yfinance ticker failed for {symbol}: {e}")

        return None

    async def _get_crypto_ohlcv(
            self,
            symbol: str,
            timeframe: str,
            limit: int,
            start: Optional[datetime],
            end: Optional[datetime]
    ) -> pd.DataFrame:
        """Get crypto OHLCV data."""
        # Try CCXT first
        if CCXT_AVAILABLE and self.ccxt_exchange:
            try:
                ccxt_tf_map = {
                    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                    "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w"
                }
                ccxt_tf = ccxt_tf_map.get(timeframe, "1h")

                since = None
                if start:
                    since = int(start.timestamp() * 1000)

                ohlcv = self.ccxt_exchange.fetch_ohlcv(
                    symbol, ccxt_tf, since=since, limit=limit
                )

                df = pd.DataFrame(
                    ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"]
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                return df

            except Exception as e:
                logger.debug(f"CCXT OHLCV failed for {symbol}: {e}")

        # Fallback to Alpaca
        if ALPACA_DATA_AVAILABLE and self.alpaca_crypto_client:
            try:
                alpaca_symbol = symbol.replace("/", "")
                tf = self._get_alpaca_timeframe(timeframe)

                if not start:
                    # Default to last N candles
                    start = datetime.now() - timedelta(days=30)
                if not end:
                    end = datetime.now()

                request = CryptoBarsRequest(
                    symbol_or_symbols=[alpaca_symbol],
                    timeframe=tf,
                    start=start,
                    end=end
                )

                bars = self.alpaca_crypto_client.get_crypto_bars(request)

                if alpaca_symbol in bars:
                    df = bars[alpaca_symbol].df.reset_index()
                    df.columns = [c.lower() for c in df.columns]
                    if 'symbol' in df.columns:
                        df = df.drop('symbol', axis=1)
                    df.set_index('timestamp', inplace=True)
                    return df.tail(limit)

            except Exception as e:
                logger.debug(f"Alpaca OHLCV failed for {symbol}: {e}")

        return pd.DataFrame()

    async def _get_stock_ohlcv(
            self,
            symbol: str,
            timeframe: str,
            limit: int,
            start: Optional[datetime],
            end: Optional[datetime]
    ) -> pd.DataFrame:
        """Get stock OHLCV data."""
        # Use yfinance
        if YFINANCE_AVAILABLE:
            try:
                # Map timeframe to yfinance interval
                yf_interval_map = {
                    "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
                    "1h": "1h", "4h": "1h", "1d": "1d", "1w": "1wk"
                }
                interval = yf_interval_map.get(timeframe, "1h")

                # Map timeframe to period
                yf_period_map = {
                    "1m": "7d", "5m": "60d", "15m": "60d", "30m": "60d",
                    "1h": "730d", "4h": "730d", "1d": "max", "1w": "max"
                }
                period = yf_period_map.get(timeframe, "60d")

                stock = yf.Ticker(symbol)
                df = stock.history(period=period, interval=interval)

                df.columns = [c.lower() for c in df.columns]
                df.index.name = "timestamp"

                # Keep only OHLCV columns
                df = df[["open", "high", "low", "close", "volume"]]

                return df.tail(limit)

            except Exception as e:
                logger.debug(f"yfinance OHLCV failed for {symbol}: {e}")

        # Fallback to Alpaca
        if ALPACA_DATA_AVAILABLE and self.alpaca_stock_client:
            try:
                tf = self._get_alpaca_timeframe(timeframe)

                if not start:
                    start = datetime.now() - timedelta(days=30)
                if not end:
                    end = datetime.now()

                request = StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=tf,
                    start=start,
                    end=end
                )

                bars = self.alpaca_stock_client.get_stock_bars(request)

                if symbol in bars:
                    df = bars[symbol].df.reset_index()
                    df.columns = [c.lower() for c in df.columns]
                    if 'symbol' in df.columns:
                        df = df.drop('symbol', axis=1)
                    df.set_index('timestamp', inplace=True)
                    return df.tail(limit)

            except Exception as e:
                logger.debug(f"Alpaca OHLCV failed for {symbol}: {e}")

        return pd.DataFrame()

    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book (bids/asks)."""
        if CCXT_AVAILABLE and self.ccxt_exchange and self._is_crypto(symbol):
            try:
                order_book = self.ccxt_exchange.fetch_order_book(symbol, limit)
                return {
                    "bids": order_book["bids"][:limit],
                    "asks": order_book["asks"][:limit],
                    "timestamp": datetime.now()
                }
            except Exception as e:
                logger.error(f"Error getting order book for {symbol}: {e}")

        return {"bids": [], "asks": [], "timestamp": datetime.now()}

    async def get_recent_trades(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades."""
        if CCXT_AVAILABLE and self.ccxt_exchange and self._is_crypto(symbol):
            try:
                trades = self.ccxt_exchange.fetch_trades(symbol, limit=limit)
                return [
                    {
                        "timestamp": datetime.fromtimestamp(t["timestamp"] / 1000),
                        "price": Decimal(str(t["price"])),
                        "amount": Decimal(str(t["amount"])),
                        "side": t["side"]
                    }
                    for t in trades
                ]
            except Exception as e:
                logger.error(f"Error getting recent trades for {symbol}: {e}")

        return []
