"""
Signal Generator
Combines technical analysis and pattern recognition to generate trading signals
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
import pandas as pd
from loguru import logger

from .technical import TechnicalAnalyzer, TechnicalAnalysisResult, TrendDirection
from .patterns import PatternRecognizer, Pattern


class SignalType(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    NEUTRAL = "neutral"
    WEAK_SELL = "weak_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class Signal:
    """Trading signal with all relevant information"""
    symbol: str
    signal_type: SignalType
    confidence: float  # 0-1
    price: float
    timestamp: datetime

    # Analysis components
    technical_signal: str
    pattern_signals: List[str]
    trend: str
    momentum: str

    # Suggested trade parameters
    suggested_entry: Optional[float] = None
    suggested_stop_loss: Optional[float] = None
    suggested_take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "signal": self.signal_type.value,
            "confidence": self.confidence,
            "price": self.price,
            "timestamp": str(self.timestamp),
            "technical_signal": self.technical_signal,
            "pattern_signals": self.pattern_signals,
            "trend": self.trend,
            "momentum": self.momentum,
            "suggested_entry": self.suggested_entry,
            "suggested_stop_loss": self.suggested_stop_loss,
            "suggested_take_profit": self.suggested_take_profit,
            "risk_reward_ratio": self.risk_reward_ratio,
            "reasons": self.reasons,
            "warnings": self.warnings
        }

    @property
    def is_actionable(self) -> bool:
        """Check if signal is strong enough to act on."""
        return (
                self.signal_type not in [SignalType.NEUTRAL, SignalType.WEAK_BUY, SignalType.WEAK_SELL]
                and self.confidence >= 0.6
        )

    @property
    def is_buy(self) -> bool:
        return self.signal_type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WEAK_BUY]

    @property
    def is_sell(self) -> bool:
        return self.signal_type in [SignalType.STRONG_SELL, SignalType.SELL, SignalType.WEAK_SELL]


class SignalGenerator:
    """
    Generates trading signals by combining multiple analysis methods.
    """

    def __init__(
            self,
            technical_analyzer: Optional[TechnicalAnalyzer] = None,
            pattern_recognizer: Optional[PatternRecognizer] = None,
            min_confidence: float = 0.5,
            default_risk_pct: float = 0.02,  # 2% risk per trade
            default_rr_ratio: float = 2.0  # 2:1 reward:risk
    ):
        """
        Initialize signal generator.

        Args:
            technical_analyzer: Technical analysis engine
            pattern_recognizer: Pattern recognition engine
            min_confidence: Minimum confidence for signals
            default_risk_pct: Default risk percentage
            default_rr_ratio: Default reward/risk ratio
        """
        self.ta = technical_analyzer or TechnicalAnalyzer()
        self.pr = pattern_recognizer or PatternRecognizer()
        self.min_confidence = min_confidence
        self.default_risk_pct = default_risk_pct
        self.default_rr_ratio = default_rr_ratio

    def generate_signal(
            self,
            df: pd.DataFrame,
            symbol: str = "UNKNOWN",
            timeframe: str = "1h"
    ) -> Signal:
        """
        Generate a trading signal from OHLCV data.

        Args:
            df: OHLCV DataFrame
            symbol: Trading symbol
            timeframe: Data timeframe

        Returns:
            Signal object with trading recommendation
        """
        if df.empty or len(df) < 50:
            return self._neutral_signal(symbol)

        current_price = float(df["close"].iloc[-1])
        timestamp = df.index[-1] if hasattr(df.index[-1], 'isoformat') else datetime.now()

        # Run technical analysis
        ta_result = self.ta.analyze(df, symbol, timeframe)

        # Find patterns
        patterns = self.pr.find_all_patterns(df)

        # Combine signals
        signal_type, confidence, reasons = self._combine_signals(ta_result, patterns)

        # Generate warnings
        warnings = self._generate_warnings(ta_result, patterns, df)

        # Calculate trade parameters
        entry, stop_loss, take_profit = self._calculate_trade_params(
            signal_type, current_price, ta_result, patterns
        )

        # Calculate risk/reward
        rr_ratio = None
        if entry and stop_loss and take_profit:
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
            rr_ratio = reward / risk if risk > 0 else None

        return Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price=current_price,
            timestamp=timestamp,
            technical_signal=ta_result.overall_signal,
            pattern_signals=[p.pattern_type.value for p in patterns],
            trend=ta_result.trend.value,
            momentum=ta_result.momentum.value,
            suggested_entry=entry,
            suggested_stop_loss=stop_loss,
            suggested_take_profit=take_profit,
            risk_reward_ratio=rr_ratio,
            reasons=reasons,
            warnings=warnings
        )

    def _combine_signals(
            self,
            ta_result: TechnicalAnalysisResult,
            patterns: List[Pattern]
    ) -> tuple:
        """Combine technical and pattern signals."""
        reasons = []

        # Start with technical analysis signal
        ta_score = {
            "strong_buy": 2,
            "buy": 1,
            "neutral": 0,
            "sell": -1,
            "strong_sell": -2
        }.get(ta_result.overall_signal, 0)

        reasons.append(f"Technical analysis: {ta_result.overall_signal} (conf: {ta_result.confidence:.0%})")

        # Add pattern signals
        pattern_score = 0
        for pattern in patterns:
            if pattern.signal == "bullish":
                pattern_score += pattern.strength
                reasons.append(f"Bullish pattern: {pattern.pattern_type.value}")
            elif pattern.signal == "bearish":
                pattern_score -= pattern.strength
                reasons.append(f"Bearish pattern: {pattern.pattern_type.value}")

        # Trend alignment bonus
        trend_bonus = 0
        if ta_result.trend == TrendDirection.STRONG_BULLISH:
            trend_bonus = 0.5
            reasons.append("Strong bullish trend")
        elif ta_result.trend == TrendDirection.BULLISH:
            trend_bonus = 0.25
            reasons.append("Bullish trend")
        elif ta_result.trend == TrendDirection.STRONG_BEARISH:
            trend_bonus = -0.5
            reasons.append("Strong bearish trend")
        elif ta_result.trend == TrendDirection.BEARISH:
            trend_bonus = -0.25
            reasons.append("Bearish trend")

        # Calculate final score
        total_score = ta_score + pattern_score + trend_bonus

        # Determine signal type
        if total_score >= 2.5:
            signal_type = SignalType.STRONG_BUY
        elif total_score >= 1.5:
            signal_type = SignalType.BUY
        elif total_score >= 0.5:
            signal_type = SignalType.WEAK_BUY
        elif total_score <= -2.5:
            signal_type = SignalType.STRONG_SELL
        elif total_score <= -1.5:
            signal_type = SignalType.SELL
        elif total_score <= -0.5:
            signal_type = SignalType.WEAK_SELL
        else:
            signal_type = SignalType.NEUTRAL

        # Calculate confidence
        base_confidence = ta_result.confidence
        pattern_confidence = sum(p.strength for p in patterns) / max(len(patterns), 1) if patterns else 0
        confidence = (base_confidence * 0.6 + pattern_confidence * 0.4) if patterns else base_confidence

        return signal_type, min(confidence, 1.0), reasons

    def _generate_warnings(
            self,
            ta_result: TechnicalAnalysisResult,
            patterns: List[Pattern],
            df: pd.DataFrame
    ) -> List[str]:
        """Generate warnings about the signal."""
        warnings = []

        # Volatility warning
        if ta_result.volatility > 50:
            warnings.append(f"High volatility: {ta_result.volatility:.1f}%")

        # Overbought/oversold warning
        if ta_result.momentum.value == "overbought":
            warnings.append("Market is overbought - potential reversal")
        elif ta_result.momentum.value == "oversold":
            warnings.append("Market is oversold - potential reversal")

        # Conflicting signals
        bullish_patterns = [p for p in patterns if p.signal == "bullish"]
        bearish_patterns = [p for p in patterns if p.signal == "bearish"]
        if bullish_patterns and bearish_patterns:
            warnings.append("Conflicting pattern signals detected")

        # Low volume warning
        if "volume" in df.columns:
            recent_vol = df["volume"].tail(5).mean()
            avg_vol = df["volume"].mean()
            if recent_vol < avg_vol * 0.5:
                warnings.append("Low volume - signal may be weaker")

        # Approaching support/resistance
        current_price = df["close"].iloc[-1]
        for level in ta_result.resistance_levels[:2]:
            if abs(current_price - level) / current_price < 0.02:
                warnings.append(f"Near resistance at {level:.2f}")
        for level in ta_result.support_levels[:2]:
            if abs(current_price - level) / current_price < 0.02:
                warnings.append(f"Near support at {level:.2f}")

        return warnings

    def _calculate_trade_params(
            self,
            signal_type: SignalType,
            current_price: float,
            ta_result: TechnicalAnalysisResult,
            patterns: List[Pattern]
    ) -> tuple:
        """Calculate suggested entry, stop loss, and take profit."""
        if signal_type == SignalType.NEUTRAL:
            return None, None, None

        is_buy = signal_type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WEAK_BUY]

        # Entry price (market or slight improvement)
        entry = current_price

        # Stop loss based on support/resistance or ATR
        if is_buy:
            # Stop below recent support
            if ta_result.support_levels:
                stop_loss = ta_result.support_levels[0] * 0.99
            else:
                stop_loss = current_price * (1 - self.default_risk_pct)

            # Take profit at resistance or using R:R ratio
            if ta_result.resistance_levels:
                take_profit = ta_result.resistance_levels[0]
            else:
                risk = entry - stop_loss
                take_profit = entry + (risk * self.default_rr_ratio)
        else:
            # Stop above recent resistance
            if ta_result.resistance_levels:
                stop_loss = ta_result.resistance_levels[0] * 1.01
            else:
                stop_loss = current_price * (1 + self.default_risk_pct)

            # Take profit at support
            if ta_result.support_levels:
                take_profit = ta_result.support_levels[0]
            else:
                risk = stop_loss - entry
                take_profit = entry - (risk * self.default_rr_ratio)

        # Override with pattern targets if available
        for pattern in patterns:
            if pattern.target_price and pattern.signal == ("bullish" if is_buy else "bearish"):
                take_profit = pattern.target_price
            if pattern.stop_loss:
                stop_loss = pattern.stop_loss

        return entry, stop_loss, take_profit

    def _neutral_signal(self, symbol: str) -> Signal:
        """Return a neutral signal when analysis fails."""
        return Signal(
            symbol=symbol,
            signal_type=SignalType.NEUTRAL,
            confidence=0.0,
            price=0.0,
            timestamp=datetime.now(),
            technical_signal="neutral",
            pattern_signals=[],
            trend="neutral",
            momentum="neutral",
            reasons=["Insufficient data for analysis"],
            warnings=["Cannot generate reliable signal"]
        )

    def analyze_multiple(
            self,
            data: Dict[str, pd.DataFrame],
            timeframe: str = "1h"
    ) -> Dict[str, Signal]:
        """
        Generate signals for multiple symbols.

        Args:
            data: Dict mapping symbol to OHLCV DataFrame
            timeframe: Data timeframe

        Returns:
            Dict mapping symbol to Signal
        """
        signals = {}
        for symbol, df in data.items():
            signals[symbol] = self.generate_signal(df, symbol, timeframe)
        return signals

    def get_best_opportunities(
            self,
            signals: Dict[str, Signal],
            min_confidence: float = 0.7,
            top_n: int = 5
    ) -> List[Signal]:
        """
        Get the best trading opportunities from multiple signals.

        Args:
            signals: Dict of signals
            min_confidence: Minimum confidence threshold
            top_n: Number of top opportunities to return

        Returns:
            List of best Signal objects
        """
        # Filter actionable signals
        actionable = [
            s for s in signals.values()
            if s.is_actionable and s.confidence >= min_confidence
        ]

        # Sort by confidence
        actionable.sort(key=lambda x: x.confidence, reverse=True)

        return actionable[:top_n]
