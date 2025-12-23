"""
Technical Analysis Engine
Calculates all major technical indicators for trading signals
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger

# Try importing TA libraries
try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logger.warning("pandas-ta not installed. Some indicators may be unavailable.")


class TrendDirection(Enum):
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


class MomentumState(Enum):
    OVERBOUGHT = "overbought"
    OVERSOLD = "oversold"
    NEUTRAL = "neutral"


@dataclass
class IndicatorResult:
    """Result from a single indicator"""
    name: str
    value: float
    signal: Literal["buy", "sell", "neutral"]
    strength: float  # 0-1, how strong the signal is
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TechnicalAnalysisResult:
    """Complete technical analysis result"""
    symbol: str
    timeframe: str
    timestamp: Any
    indicators: List[IndicatorResult]
    trend: TrendDirection
    momentum: MomentumState
    volatility: float
    support_levels: List[float]
    resistance_levels: List[float]
    overall_signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"]
    confidence: float  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": str(self.timestamp),
            "indicators": [
                {"name": i.name, "value": i.value, "signal": i.signal, "strength": i.strength}
                for i in self.indicators
            ],
            "trend": self.trend.value,
            "momentum": self.momentum.value,
            "volatility": self.volatility,
            "support_levels": self.support_levels,
            "resistance_levels": self.resistance_levels,
            "overall_signal": self.overall_signal,
            "confidence": self.confidence
        }


class TechnicalAnalyzer:
    """
    Comprehensive technical analysis engine.
    Calculates indicators and generates trading signals.
    """

    def __init__(self, use_pandas_ta: bool = True):
        """
        Initialize technical analyzer.

        Args:
            use_pandas_ta: Use pandas-ta library if available
        """
        self.use_pandas_ta = use_pandas_ta and PANDAS_TA_AVAILABLE

    def analyze(
            self,
            df: pd.DataFrame,
            symbol: str = "UNKNOWN",
            timeframe: str = "1h"
    ) -> TechnicalAnalysisResult:
        """
        Perform complete technical analysis on OHLCV data.

        Args:
            df: DataFrame with OHLCV data
            symbol: Trading symbol
            timeframe: Timeframe of the data

        Returns:
            TechnicalAnalysisResult with all indicators and signals
        """
        if df.empty or len(df) < 50:
            logger.warning(f"Insufficient data for analysis: {len(df)} rows")
            return self._empty_result(symbol, timeframe)

        # Calculate all indicators
        df = self._add_all_indicators(df.copy())

        # Get latest values
        latest = df.iloc[-1]

        # Calculate individual indicator signals
        indicators = self._evaluate_indicators(df, latest)

        # Determine overall trend
        trend = self._determine_trend(df, latest)

        # Determine momentum state
        momentum = self._determine_momentum(latest)

        # Calculate volatility
        volatility = self._calculate_volatility(df)

        # Find support/resistance levels
        support_levels, resistance_levels = self._find_levels(df)

        # Calculate overall signal
        overall_signal, confidence = self._calculate_overall_signal(indicators)

        return TechnicalAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=df.index[-1] if hasattr(df.index[-1], 'isoformat') else df.index[-1],
            indicators=indicators,
            trend=trend,
            momentum=momentum,
            volatility=volatility,
            support_levels=support_levels[:3],
            resistance_levels=resistance_levels[:3],
            overall_signal=overall_signal,
            confidence=confidence
        )

    def _add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators to the DataFrame."""

        # Moving Averages
        df["sma_10"] = df["close"].rolling(window=10).mean()
        df["sma_20"] = df["close"].rolling(window=20).mean()
        df["sma_50"] = df["close"].rolling(window=50).mean()
        df["sma_200"] = df["close"].rolling(window=200).mean()

        df["ema_9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()
        df["ema_55"] = df["close"].ewm(span=55, adjust=False).mean()

        # RSI
        df["rsi"] = self._calculate_rsi(df["close"], 14)

        # MACD
        macd_result = self._calculate_macd(df["close"])
        df["macd"] = macd_result["macd"]
        df["macd_signal"] = macd_result["signal"]
        df["macd_hist"] = macd_result["histogram"]

        # Bollinger Bands
        bb_result = self._calculate_bollinger_bands(df["close"])
        df["bb_upper"] = bb_result["upper"]
        df["bb_middle"] = bb_result["middle"]
        df["bb_lower"] = bb_result["lower"]
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        # Stochastic
        stoch_result = self._calculate_stochastic(df)
        df["stoch_k"] = stoch_result["k"]
        df["stoch_d"] = stoch_result["d"]

        # ATR (Average True Range)
        df["atr"] = self._calculate_atr(df, 14)

        # ADX (Average Directional Index)
        adx_result = self._calculate_adx(df, 14)
        df["adx"] = adx_result["adx"]
        df["di_plus"] = adx_result["di_plus"]
        df["di_minus"] = adx_result["di_minus"]

        # OBV (On Balance Volume)
        df["obv"] = self._calculate_obv(df)

        # VWAP (if intraday)
        if "volume" in df.columns:
            df["vwap"] = (df["volume"] * (df["high"] + df["low"] + df["close"]) / 3).cumsum() / df["volume"].cumsum()

        # Ichimoku Cloud (simplified)
        ichimoku = self._calculate_ichimoku(df)
        df["tenkan"] = ichimoku["tenkan"]
        df["kijun"] = ichimoku["kijun"]
        df["senkou_a"] = ichimoku["senkou_a"]
        df["senkou_b"] = ichimoku["senkou_b"]

        # Momentum
        df["momentum"] = df["close"] - df["close"].shift(10)
        df["roc"] = (df["close"] - df["close"].shift(10)) / df["close"].shift(10) * 100

        # Williams %R
        df["williams_r"] = self._calculate_williams_r(df, 14)

        # CCI (Commodity Channel Index)
        df["cci"] = self._calculate_cci(df, 20)

        return df

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(
            self,
            prices: pd.Series,
            fast: int = 12,
            slow: int = 26,
            signal: int = 9
    ) -> Dict[str, pd.Series]:
        """Calculate MACD."""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - macd_signal
        return {"macd": macd, "signal": macd_signal, "histogram": histogram}

    def _calculate_bollinger_bands(
            self,
            prices: pd.Series,
            period: int = 20,
            std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return {"upper": upper, "middle": middle, "lower": lower}

    def _calculate_stochastic(
            self,
            df: pd.DataFrame,
            k_period: int = 14,
            d_period: int = 3
    ) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator."""
        low_min = df["low"].rolling(window=k_period).min()
        high_max = df["high"].rolling(window=k_period).max()
        k = 100 * (df["close"] - low_min) / (high_max - low_min)
        d = k.rolling(window=d_period).mean()
        return {"k": k, "d": d}

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df["high"]
        low = df["low"]
        close = df["close"].shift(1)

        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate ADX and DI+/DI-."""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True Range
        tr = self._calculate_atr(df, 1)

        # +DM and -DM
        plus_dm = high.diff()
        minus_dm = low.diff().abs() * -1

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        minus_dm = minus_dm.abs()

        # When both are positive, keep the larger one
        plus_dm[(plus_dm > 0) & (minus_dm > 0) & (plus_dm <= minus_dm)] = 0
        minus_dm[(plus_dm > 0) & (minus_dm > 0) & (minus_dm < plus_dm)] = 0

        # Smoothed
        tr_smooth = tr.rolling(window=period).sum()
        plus_dm_smooth = plus_dm.rolling(window=period).sum()
        minus_dm_smooth = minus_dm.rolling(window=period).sum()

        # DI+ and DI-
        di_plus = 100 * plus_dm_smooth / tr_smooth
        di_minus = 100 * minus_dm_smooth / tr_smooth

        # DX and ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=period).mean()

        return {"adx": adx, "di_plus": di_plus, "di_minus": di_minus}

    def _calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """Calculate On Balance Volume."""
        obv = pd.Series(index=df.index, dtype=float)
        obv.iloc[0] = df["volume"].iloc[0]

        for i in range(1, len(df)):
            if df["close"].iloc[i] > df["close"].iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] + df["volume"].iloc[i]
            elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] - df["volume"].iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i - 1]

        return obv

    def _calculate_ichimoku(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate Ichimoku Cloud."""
        high = df["high"]
        low = df["low"]

        # Tenkan-sen (Conversion Line)
        tenkan = (high.rolling(window=9).max() + low.rolling(window=9).min()) / 2

        # Kijun-sen (Base Line)
        kijun = (high.rolling(window=26).max() + low.rolling(window=26).min()) / 2

        # Senkou Span A (Leading Span A)
        senkou_a = ((tenkan + kijun) / 2).shift(26)

        # Senkou Span B (Leading Span B)
        senkou_b = ((high.rolling(window=52).max() + low.rolling(window=52).min()) / 2).shift(26)

        return {
            "tenkan": tenkan,
            "kijun": kijun,
            "senkou_a": senkou_a,
            "senkou_b": senkou_b
        }

    def _calculate_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Williams %R."""
        highest_high = df["high"].rolling(window=period).max()
        lowest_low = df["low"].rolling(window=period).min()
        return -100 * (highest_high - df["close"]) / (highest_high - lowest_low)

    def _calculate_cci(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index."""
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        sma = typical_price.rolling(window=period).mean()
        mad = typical_price.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        return (typical_price - sma) / (0.015 * mad)

    def _evaluate_indicators(self, df: pd.DataFrame, latest: pd.Series) -> List[IndicatorResult]:
        """Evaluate all indicators and generate signals."""
        indicators = []

        # RSI
        rsi = latest.get("rsi", 50)
        if not pd.isna(rsi):
            if rsi < 30:
                signal, strength = "buy", (30 - rsi) / 30
            elif rsi > 70:
                signal, strength = "sell", (rsi - 70) / 30
            else:
                signal, strength = "neutral", 0.0
            indicators.append(IndicatorResult("RSI", float(rsi), signal, min(strength, 1.0)))

        # MACD
        macd = latest.get("macd", 0)
        macd_signal = latest.get("macd_signal", 0)
        if not pd.isna(macd) and not pd.isna(macd_signal):
            macd_hist = macd - macd_signal
            if macd > macd_signal:
                signal, strength = "buy", min(abs(macd_hist) / abs(macd) if macd != 0 else 0, 1)
            elif macd < macd_signal:
                signal, strength = "sell", min(abs(macd_hist) / abs(macd) if macd != 0 else 0, 1)
            else:
                signal, strength = "neutral", 0.0
            indicators.append(IndicatorResult("MACD", float(macd_hist), signal, strength))

        # Bollinger Bands
        close = latest.get("close", 0)
        bb_upper = latest.get("bb_upper", 0)
        bb_lower = latest.get("bb_lower", 0)
        if not pd.isna(bb_upper) and not pd.isna(bb_lower):
            if close < bb_lower:
                signal, strength = "buy", min((bb_lower - close) / (bb_upper - bb_lower), 1)
            elif close > bb_upper:
                signal, strength = "sell", min((close - bb_upper) / (bb_upper - bb_lower), 1)
            else:
                signal, strength = "neutral", 0.0
            indicators.append(IndicatorResult("Bollinger Bands", float(close), signal, strength))

        # Stochastic
        stoch_k = latest.get("stoch_k", 50)
        stoch_d = latest.get("stoch_d", 50)
        if not pd.isna(stoch_k) and not pd.isna(stoch_d):
            if stoch_k < 20 and stoch_k > stoch_d:
                signal, strength = "buy", (20 - stoch_k) / 20
            elif stoch_k > 80 and stoch_k < stoch_d:
                signal, strength = "sell", (stoch_k - 80) / 20
            else:
                signal, strength = "neutral", 0.0
            indicators.append(IndicatorResult("Stochastic", float(stoch_k), signal, min(strength, 1.0)))

        # Moving Average Crossovers
        ema_9 = latest.get("ema_9", 0)
        ema_21 = latest.get("ema_21", 0)
        if not pd.isna(ema_9) and not pd.isna(ema_21):
            if ema_9 > ema_21:
                signal = "buy"
                strength = min((ema_9 - ema_21) / ema_21 * 100 if ema_21 != 0 else 0, 1)
            elif ema_9 < ema_21:
                signal = "sell"
                strength = min((ema_21 - ema_9) / ema_21 * 100 if ema_21 != 0 else 0, 1)
            else:
                signal, strength = "neutral", 0.0
            indicators.append(IndicatorResult("EMA Crossover", float(ema_9), signal, strength))

        # ADX (trend strength)
        adx = latest.get("adx", 0)
        di_plus = latest.get("di_plus", 0)
        di_minus = latest.get("di_minus", 0)
        if not pd.isna(adx) and adx > 25:  # Strong trend
            if di_plus > di_minus:
                signal, strength = "buy", min(adx / 50, 1)
            else:
                signal, strength = "sell", min(adx / 50, 1)
            indicators.append(IndicatorResult("ADX", float(adx), signal, strength))

        # Williams %R
        williams = latest.get("williams_r", -50)
        if not pd.isna(williams):
            if williams < -80:
                signal, strength = "buy", (-80 - williams) / 20
            elif williams > -20:
                signal, strength = "sell", (williams + 20) / 20
            else:
                signal, strength = "neutral", 0.0
            indicators.append(IndicatorResult("Williams %R", float(williams), signal, min(abs(strength), 1.0)))

        # CCI
        cci = latest.get("cci", 0)
        if not pd.isna(cci):
            if cci < -100:
                signal, strength = "buy", min(abs(cci + 100) / 100, 1)
            elif cci > 100:
                signal, strength = "sell", min((cci - 100) / 100, 1)
            else:
                signal, strength = "neutral", 0.0
            indicators.append(IndicatorResult("CCI", float(cci), signal, strength))

        return indicators

    def _determine_trend(self, df: pd.DataFrame, latest: pd.Series) -> TrendDirection:
        """Determine overall trend direction."""
        close = latest.get("close", 0)
        sma_20 = latest.get("sma_20", 0)
        sma_50 = latest.get("sma_50", 0)
        sma_200 = latest.get("sma_200", 0)

        bullish_signals = 0
        bearish_signals = 0

        # Price vs moving averages
        if not pd.isna(sma_20) and close > sma_20:
            bullish_signals += 1
        elif not pd.isna(sma_20):
            bearish_signals += 1

        if not pd.isna(sma_50) and close > sma_50:
            bullish_signals += 1
        elif not pd.isna(sma_50):
            bearish_signals += 1

        if not pd.isna(sma_200) and close > sma_200:
            bullish_signals += 2  # More weight to 200 SMA
        elif not pd.isna(sma_200):
            bearish_signals += 2

        # MA alignment
        if not pd.isna(sma_20) and not pd.isna(sma_50) and sma_20 > sma_50:
            bullish_signals += 1
        elif not pd.isna(sma_20) and not pd.isna(sma_50):
            bearish_signals += 1

        # Determine trend
        net_signal = bullish_signals - bearish_signals

        if net_signal >= 4:
            return TrendDirection.STRONG_BULLISH
        elif net_signal >= 2:
            return TrendDirection.BULLISH
        elif net_signal <= -4:
            return TrendDirection.STRONG_BEARISH
        elif net_signal <= -2:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL

    def _determine_momentum(self, latest: pd.Series) -> MomentumState:
        """Determine momentum state."""
        rsi = latest.get("rsi", 50)
        stoch_k = latest.get("stoch_k", 50)

        overbought_score = 0
        oversold_score = 0

        if not pd.isna(rsi):
            if rsi > 70:
                overbought_score += 2
            elif rsi > 60:
                overbought_score += 1
            elif rsi < 30:
                oversold_score += 2
            elif rsi < 40:
                oversold_score += 1

        if not pd.isna(stoch_k):
            if stoch_k > 80:
                overbought_score += 1
            elif stoch_k < 20:
                oversold_score += 1

        if overbought_score >= 2:
            return MomentumState.OVERBOUGHT
        elif oversold_score >= 2:
            return MomentumState.OVERSOLD
        else:
            return MomentumState.NEUTRAL

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate current volatility level."""
        returns = df["close"].pct_change().dropna()
        if len(returns) < 20:
            return 0.0

        # Annualized volatility (assuming hourly data)
        hourly_vol = returns.tail(20).std()
        annualized_vol = hourly_vol * np.sqrt(24 * 365)

        return float(annualized_vol * 100)  # As percentage

    def _find_levels(self, df: pd.DataFrame) -> tuple:
        """Find support and resistance levels."""
        if len(df) < 20:
            return [], []

        recent = df.tail(100)
        current_price = recent["close"].iloc[-1]

        # Find local minima and maxima
        support_levels = []
        resistance_levels = []

        for i in range(5, len(recent) - 5):
            # Support (local minimum)
            if recent["low"].iloc[i] == recent["low"].iloc[i - 5:i + 6].min():
                level = float(recent["low"].iloc[i])
                if level < current_price:
                    support_levels.append(level)

            # Resistance (local maximum)
            if recent["high"].iloc[i] == recent["high"].iloc[i - 5:i + 6].max():
                level = float(recent["high"].iloc[i])
                if level > current_price:
                    resistance_levels.append(level)

        # Sort by distance from current price
        support_levels = sorted(set(support_levels), key=lambda x: current_price - x)
        resistance_levels = sorted(set(resistance_levels), key=lambda x: x - current_price)

        return support_levels, resistance_levels

    def _calculate_overall_signal(
            self,
            indicators: List[IndicatorResult]
    ) -> tuple:
        """Calculate overall signal from all indicators."""
        if not indicators:
            return "neutral", 0.0

        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0

        for ind in indicators:
            weight = 1.0 + ind.strength  # Weight by signal strength
            total_weight += weight

            if ind.signal == "buy":
                buy_score += weight * ind.strength
            elif ind.signal == "sell":
                sell_score += weight * ind.strength

        if total_weight == 0:
            return "neutral", 0.0

        net_score = (buy_score - sell_score) / total_weight
        confidence = abs(net_score)

        if net_score > 0.3:
            signal = "strong_buy" if net_score > 0.6 else "buy"
        elif net_score < -0.3:
            signal = "strong_sell" if net_score < -0.6 else "sell"
        else:
            signal = "neutral"

        return signal, min(confidence, 1.0)

    def _empty_result(self, symbol: str, timeframe: str) -> TechnicalAnalysisResult:
        """Return empty result when analysis fails."""
        return TechnicalAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=None,
            indicators=[],
            trend=TrendDirection.NEUTRAL,
            momentum=MomentumState.NEUTRAL,
            volatility=0.0,
            support_levels=[],
            resistance_levels=[],
            overall_signal="neutral",
            confidence=0.0
        )
