"""
Historical Data Manager
Downloads, caches, and manages historical market data for backtesting and analysis
"""
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd
from loguru import logger

from config.settings import DATA_DIR
from .market_data import MarketDataProvider


class HistoricalDataManager:
    """
    Manages historical market data.
    Handles downloading, caching, and retrieving historical OHLCV data.
    """

    def __init__(
            self,
            data_provider: MarketDataProvider,
            cache_dir: Optional[Path] = None
    ):
        """
        Initialize historical data manager.

        Args:
            data_provider: Market data provider instance
            cache_dir: Directory for caching data
        """
        self.data_provider = data_provider
        self.cache_dir = cache_dir or DATA_DIR / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._memory_cache: Dict[str, pd.DataFrame] = {}

    def _get_cache_path(self, symbol: str, timeframe: str) -> Path:
        """Get cache file path for symbol/timeframe."""
        safe_symbol = symbol.replace("/", "_")
        return self.cache_dir / f"{safe_symbol}_{timeframe}.parquet"

    async def get_historical_data(
            self,
            symbol: str,
            timeframe: str = "1h",
            days: int = 365,
            use_cache: bool = True,
            force_refresh: bool = False
    ) -> pd.DataFrame:
        """
        Get historical OHLCV data.

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            days: Number of days of data
            use_cache: Whether to use cached data
            force_refresh: Force download even if cached

        Returns:
            DataFrame with historical OHLCV data
        """
        cache_key = f"{symbol}_{timeframe}"
        cache_path = self._get_cache_path(symbol, timeframe)

        # Check memory cache first
        if use_cache and not force_refresh and cache_key in self._memory_cache:
            logger.debug(f"Using memory cache for {symbol} {timeframe}")
            return self._memory_cache[cache_key]

        # Check file cache
        if use_cache and not force_refresh and cache_path.exists():
            try:
                df = pd.read_parquet(cache_path)
                # Check if cache is fresh (less than 1 hour old for intraday)
                cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
                max_age = timedelta(hours=1) if timeframe in ["1m", "5m", "15m", "30m", "1h"] else timedelta(days=1)

                if cache_age < max_age:
                    logger.debug(f"Using file cache for {symbol} {timeframe}")
                    self._memory_cache[cache_key] = df
                    return df
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")

        # Download fresh data
        logger.info(f"Downloading historical data for {symbol} {timeframe} ({days} days)")

        start = datetime.now() - timedelta(days=days)
        end = datetime.now()

        df = await self.data_provider.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=days * 24,  # Approximate for hourly
            start=start,
            end=end
        )

        if not df.empty:
            # Save to cache
            try:
                df.to_parquet(cache_path)
                logger.debug(f"Saved cache for {symbol} {timeframe}")
            except Exception as e:
                logger.warning(f"Failed to save cache: {e}")

            self._memory_cache[cache_key] = df

        return df

    async def download_all(
            self,
            symbols: List[str],
            timeframes: List[str] = ["1h", "4h", "1d"],
            days: int = 365
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Download historical data for multiple symbols and timeframes.

        Args:
            symbols: List of symbols
            timeframes: List of timeframes
            days: Number of days

        Returns:
            Nested dict: {symbol: {timeframe: DataFrame}}
        """
        results: Dict[str, Dict[str, pd.DataFrame]] = {}

        for symbol in symbols:
            results[symbol] = {}
            for timeframe in timeframes:
                df = await self.get_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    days=days,
                    force_refresh=True
                )
                results[symbol][timeframe] = df
                logger.info(f"Downloaded {symbol} {timeframe}: {len(df)} candles")

        return results

    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None):
        """
        Clear cached data.

        Args:
            symbol: Specific symbol to clear (None = all)
            timeframe: Specific timeframe to clear (None = all)
        """
        if symbol and timeframe:
            # Clear specific cache
            cache_path = self._get_cache_path(symbol, timeframe)
            if cache_path.exists():
                cache_path.unlink()
            cache_key = f"{symbol}_{timeframe}"
            self._memory_cache.pop(cache_key, None)
        elif symbol:
            # Clear all timeframes for symbol
            safe_symbol = symbol.replace("/", "_")
            for path in self.cache_dir.glob(f"{safe_symbol}_*.parquet"):
                path.unlink()
            self._memory_cache = {
                k: v for k, v in self._memory_cache.items()
                if not k.startswith(f"{symbol}_")
            }
        else:
            # Clear all cache
            for path in self.cache_dir.glob("*.parquet"):
                path.unlink()
            self._memory_cache.clear()

        logger.info(f"Cache cleared for {symbol or 'all'} {timeframe or 'all timeframes'}")

    def get_cache_info(self) -> List[Dict]:
        """Get information about cached data."""
        info = []
        for path in self.cache_dir.glob("*.parquet"):
            try:
                df = pd.read_parquet(path)
                parts = path.stem.rsplit("_", 1)
                symbol = parts[0].replace("_", "/")
                timeframe = parts[1] if len(parts) > 1 else "unknown"

                info.append({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "rows": len(df),
                    "start": df.index[0] if len(df) > 0 else None,
                    "end": df.index[-1] if len(df) > 0 else None,
                    "size_mb": path.stat().st_size / 1024 / 1024,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime)
                })
            except Exception as e:
                logger.warning(f"Failed to read cache info for {path}: {e}")

        return info


class DataPreprocessor:
    """
    Preprocesses market data for ML/AI analysis.
    """

    @staticmethod
    def add_returns(df: pd.DataFrame) -> pd.DataFrame:
        """Add return columns."""
        df = df.copy()
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = pd.np.log(df["close"] / df["close"].shift(1))
        return df

    @staticmethod
    def add_volatility(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """Add volatility metrics."""
        df = df.copy()
        df["volatility"] = df["returns"].rolling(window=window).std()
        df["volatility_pct"] = df["volatility"] * 100
        return df

    @staticmethod
    def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features."""
        df = df.copy()

        # Price ranges
        df["range"] = df["high"] - df["low"]
        df["range_pct"] = df["range"] / df["close"] * 100

        # Body and wicks (candlestick analysis)
        df["body"] = abs(df["close"] - df["open"])
        df["body_pct"] = df["body"] / df["close"] * 100

        df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
        df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

        # Trend
        df["is_bullish"] = (df["close"] > df["open"]).astype(int)

        return df

    @staticmethod
    def normalize(df: pd.DataFrame, columns: List[str], method: str = "zscore") -> pd.DataFrame:
        """Normalize specified columns."""
        df = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            if method == "zscore":
                df[f"{col}_norm"] = (df[col] - df[col].mean()) / df[col].std()
            elif method == "minmax":
                df[f"{col}_norm"] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
            elif method == "robust":
                median = df[col].median()
                iqr = df[col].quantile(0.75) - df[col].quantile(0.25)
                df[f"{col}_norm"] = (df[col] - median) / iqr

        return df

    @staticmethod
    def prepare_for_ml(
            df: pd.DataFrame,
            target_column: str = "returns",
            lookback: int = 10,
            lookahead: int = 1
    ) -> tuple:
        """
        Prepare data for ML training.

        Args:
            df: Input DataFrame
            target_column: Column to predict
            lookback: Number of past periods to use as features
            lookahead: Number of periods ahead to predict

        Returns:
            Tuple of (X, y) arrays
        """
        import numpy as np

        df = df.copy()

        # Create target (future return)
        df["target"] = df[target_column].shift(-lookahead)

        # Create features from lookback period
        feature_cols = ["open", "high", "low", "close", "volume"]
        features = []

        for col in feature_cols:
            if col in df.columns:
                for i in range(lookback):
                    df[f"{col}_lag_{i}"] = df[col].shift(i)
                    features.append(f"{col}_lag_{i}")

        # Drop NaN rows
        df = df.dropna()

        X = df[features].values
        y = df["target"].values

        return X, y
