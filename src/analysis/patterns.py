"""
Chart Pattern Recognition
Identifies candlestick and chart patterns for trading signals
"""
from dataclasses import dataclass
from typing import List, Optional, Literal, Dict, Any
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger


class PatternType(Enum):
    # Candlestick Patterns
    DOJI = "doji"
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    HANGING_MAN = "hanging_man"
    SHOOTING_STAR = "shooting_star"
    ENGULFING_BULLISH = "engulfing_bullish"
    ENGULFING_BEARISH = "engulfing_bearish"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    HARAMI_BULLISH = "harami_bullish"
    HARAMI_BEARISH = "harami_bearish"
    PIERCING_LINE = "piercing_line"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    SPINNING_TOP = "spinning_top"
    MARUBOZU_BULLISH = "marubozu_bullish"
    MARUBOZU_BEARISH = "marubozu_bearish"

    # Chart Patterns
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_and_shoulders"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    CUP_AND_HANDLE = "cup_and_handle"


@dataclass
class Pattern:
    """Detected pattern information"""
    pattern_type: PatternType
    signal: Literal["bullish", "bearish", "neutral"]
    strength: float  # 0-1 confidence
    start_index: int
    end_index: int
    description: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern_type.value,
            "signal": self.signal,
            "strength": self.strength,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "description": self.description,
            "target_price": self.target_price,
            "stop_loss": self.stop_loss
        }


class PatternRecognizer:
    """
    Recognizes candlestick and chart patterns.
    """

    def __init__(self, min_pattern_strength: float = 0.6):
        """
        Initialize pattern recognizer.

        Args:
            min_pattern_strength: Minimum strength threshold for patterns
        """
        self.min_strength = min_pattern_strength

    def find_all_patterns(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Find all patterns in the data.

        Args:
            df: OHLCV DataFrame

        Returns:
            List of detected patterns
        """
        if df.empty or len(df) < 5:
            return []

        patterns = []

        # Find candlestick patterns
        patterns.extend(self._find_candlestick_patterns(df))

        # Find chart patterns
        patterns.extend(self._find_chart_patterns(df))

        # Filter by minimum strength
        patterns = [p for p in patterns if p.strength >= self.min_strength]

        return patterns

    def _find_candlestick_patterns(self, df: pd.DataFrame) -> List[Pattern]:
        """Find candlestick patterns in recent candles."""
        patterns = []
        n = len(df)

        if n < 3:
            return patterns

        # Analyze recent candles
        for i in range(max(0, n - 10), n):
            # Get candle data
            o, h, l, c = df.iloc[i][["open", "high", "low", "close"]]
            body = abs(c - o)
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            total_range = h - l

            if total_range == 0:
                continue

            body_pct = body / total_range
            upper_pct = upper_wick / total_range
            lower_pct = lower_wick / total_range

            is_bullish = c > o

            # DOJI
            if body_pct < 0.1:
                patterns.append(Pattern(
                    pattern_type=PatternType.DOJI,
                    signal="neutral",
                    strength=0.7,
                    start_index=i,
                    end_index=i,
                    description="Doji - Market indecision, potential reversal"
                ))

            # HAMMER (bullish reversal)
            if lower_pct > 0.6 and body_pct < 0.3 and upper_pct < 0.1:
                patterns.append(Pattern(
                    pattern_type=PatternType.HAMMER,
                    signal="bullish",
                    strength=0.75,
                    start_index=i,
                    end_index=i,
                    description="Hammer - Bullish reversal signal"
                ))

            # INVERTED HAMMER
            if upper_pct > 0.6 and body_pct < 0.3 and lower_pct < 0.1 and is_bullish:
                patterns.append(Pattern(
                    pattern_type=PatternType.INVERTED_HAMMER,
                    signal="bullish",
                    strength=0.65,
                    start_index=i,
                    end_index=i,
                    description="Inverted Hammer - Potential bullish reversal"
                ))

            # SHOOTING STAR (bearish)
            if upper_pct > 0.6 and body_pct < 0.3 and lower_pct < 0.1 and not is_bullish:
                patterns.append(Pattern(
                    pattern_type=PatternType.SHOOTING_STAR,
                    signal="bearish",
                    strength=0.75,
                    start_index=i,
                    end_index=i,
                    description="Shooting Star - Bearish reversal signal"
                ))

            # HANGING MAN (bearish)
            if lower_pct > 0.6 and body_pct < 0.3 and upper_pct < 0.1 and not is_bullish:
                patterns.append(Pattern(
                    pattern_type=PatternType.HANGING_MAN,
                    signal="bearish",
                    strength=0.7,
                    start_index=i,
                    end_index=i,
                    description="Hanging Man - Bearish reversal warning"
                ))

            # MARUBOZU (strong trend)
            if body_pct > 0.9:
                if is_bullish:
                    patterns.append(Pattern(
                        pattern_type=PatternType.MARUBOZU_BULLISH,
                        signal="bullish",
                        strength=0.8,
                        start_index=i,
                        end_index=i,
                        description="Bullish Marubozu - Strong buying pressure"
                    ))
                else:
                    patterns.append(Pattern(
                        pattern_type=PatternType.MARUBOZU_BEARISH,
                        signal="bearish",
                        strength=0.8,
                        start_index=i,
                        end_index=i,
                        description="Bearish Marubozu - Strong selling pressure"
                    ))

            # SPINNING TOP
            if 0.1 < body_pct < 0.3 and upper_pct > 0.3 and lower_pct > 0.3:
                patterns.append(Pattern(
                    pattern_type=PatternType.SPINNING_TOP,
                    signal="neutral",
                    strength=0.6,
                    start_index=i,
                    end_index=i,
                    description="Spinning Top - Market uncertainty"
                ))

            # Two-candle patterns
            if i > 0:
                prev_o, prev_h, prev_l, prev_c = df.iloc[i - 1][["open", "high", "low", "close"]]
                prev_body = abs(prev_c - prev_o)
                prev_bullish = prev_c > prev_o

                # ENGULFING BULLISH
                if not prev_bullish and is_bullish and o <= prev_c and c >= prev_o and body > prev_body:
                    patterns.append(Pattern(
                        pattern_type=PatternType.ENGULFING_BULLISH,
                        signal="bullish",
                        strength=0.85,
                        start_index=i - 1,
                        end_index=i,
                        description="Bullish Engulfing - Strong reversal signal"
                    ))

                # ENGULFING BEARISH
                if prev_bullish and not is_bullish and o >= prev_c and c <= prev_o and body > prev_body:
                    patterns.append(Pattern(
                        pattern_type=PatternType.ENGULFING_BEARISH,
                        signal="bearish",
                        strength=0.85,
                        start_index=i - 1,
                        end_index=i,
                        description="Bearish Engulfing - Strong reversal signal"
                    ))

                # HARAMI BULLISH
                if not prev_bullish and is_bullish and o > prev_c and c < prev_o and body < prev_body * 0.5:
                    patterns.append(Pattern(
                        pattern_type=PatternType.HARAMI_BULLISH,
                        signal="bullish",
                        strength=0.7,
                        start_index=i - 1,
                        end_index=i,
                        description="Bullish Harami - Potential reversal"
                    ))

                # HARAMI BEARISH
                if prev_bullish and not is_bullish and o < prev_c and c > prev_o and body < prev_body * 0.5:
                    patterns.append(Pattern(
                        pattern_type=PatternType.HARAMI_BEARISH,
                        signal="bearish",
                        strength=0.7,
                        start_index=i - 1,
                        end_index=i,
                        description="Bearish Harami - Potential reversal"
                    ))

                # PIERCING LINE
                if not prev_bullish and is_bullish and o < prev_l and c > (prev_o + prev_c) / 2:
                    patterns.append(Pattern(
                        pattern_type=PatternType.PIERCING_LINE,
                        signal="bullish",
                        strength=0.75,
                        start_index=i - 1,
                        end_index=i,
                        description="Piercing Line - Bullish reversal"
                    ))

                # DARK CLOUD COVER
                if prev_bullish and not is_bullish and o > prev_h and c < (prev_o + prev_c) / 2:
                    patterns.append(Pattern(
                        pattern_type=PatternType.DARK_CLOUD_COVER,
                        signal="bearish",
                        strength=0.75,
                        start_index=i - 1,
                        end_index=i,
                        description="Dark Cloud Cover - Bearish reversal"
                    ))

            # Three-candle patterns
            if i > 1:
                prev2_o, prev2_h, prev2_l, prev2_c = df.iloc[i - 2][["open", "high", "low", "close"]]
                prev2_bullish = prev2_c > prev2_o

                # MORNING STAR
                if (not prev2_bullish and
                        abs(prev_c - prev_o) < abs(prev2_c - prev2_o) * 0.3 and
                        is_bullish and c > (prev2_o + prev2_c) / 2):
                    patterns.append(Pattern(
                        pattern_type=PatternType.MORNING_STAR,
                        signal="bullish",
                        strength=0.9,
                        start_index=i - 2,
                        end_index=i,
                        description="Morning Star - Strong bullish reversal"
                    ))

                # EVENING STAR
                if (prev2_bullish and
                        abs(prev_c - prev_o) < abs(prev2_c - prev2_o) * 0.3 and
                        not is_bullish and c < (prev2_o + prev2_c) / 2):
                    patterns.append(Pattern(
                        pattern_type=PatternType.EVENING_STAR,
                        signal="bearish",
                        strength=0.9,
                        start_index=i - 2,
                        end_index=i,
                        description="Evening Star - Strong bearish reversal"
                    ))

                # THREE WHITE SOLDIERS
                if i > 2:
                    prev3_o, prev3_c = df.iloc[i - 3][["open", "close"]]
                    if (prev3_c > prev3_o and prev2_c > prev2_o and
                            prev_c > prev_o and c > o and
                            prev2_c > prev3_c and prev_c > prev2_c and c > prev_c):
                        patterns.append(Pattern(
                            pattern_type=PatternType.THREE_WHITE_SOLDIERS,
                            signal="bullish",
                            strength=0.9,
                            start_index=i - 2,
                            end_index=i,
                            description="Three White Soldiers - Strong bullish continuation"
                        ))

                    # THREE BLACK CROWS
                    if (prev3_c < prev3_o and prev2_c < prev2_o and
                            prev_c < prev_o and c < o and
                            prev2_c < prev3_c and prev_c < prev2_c and c < prev_c):
                        patterns.append(Pattern(
                            pattern_type=PatternType.THREE_BLACK_CROWS,
                            signal="bearish",
                            strength=0.9,
                            start_index=i - 2,
                            end_index=i,
                            description="Three Black Crows - Strong bearish continuation"
                        ))

        return patterns

    def _find_chart_patterns(self, df: pd.DataFrame) -> List[Pattern]:
        """Find chart patterns in the data."""
        patterns = []
        n = len(df)

        if n < 20:
            return patterns

        # Get highs and lows for pattern detection
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        # Find local maxima and minima
        local_max_idx = self._find_local_extrema(highs, is_max=True)
        local_min_idx = self._find_local_extrema(lows, is_max=False)

        # DOUBLE TOP
        if len(local_max_idx) >= 2:
            for i in range(len(local_max_idx) - 1):
                idx1, idx2 = local_max_idx[i], local_max_idx[i + 1]
                if 5 <= idx2 - idx1 <= 50:
                    peak1, peak2 = highs[idx1], highs[idx2]
                    if abs(peak1 - peak2) / peak1 < 0.03:  # Within 3%
                        # Check for neckline
                        min_between = lows[idx1:idx2 + 1].min()
                        if min_between < peak1 * 0.95:
                            patterns.append(Pattern(
                                pattern_type=PatternType.DOUBLE_TOP,
                                signal="bearish",
                                strength=0.8,
                                start_index=idx1,
                                end_index=idx2,
                                description="Double Top - Bearish reversal pattern",
                                target_price=min_between - (peak1 - min_between),
                                stop_loss=max(peak1, peak2) * 1.02
                            ))

        # DOUBLE BOTTOM
        if len(local_min_idx) >= 2:
            for i in range(len(local_min_idx) - 1):
                idx1, idx2 = local_min_idx[i], local_min_idx[i + 1]
                if 5 <= idx2 - idx1 <= 50:
                    bottom1, bottom2 = lows[idx1], lows[idx2]
                    if abs(bottom1 - bottom2) / bottom1 < 0.03:
                        max_between = highs[idx1:idx2 + 1].max()
                        if max_between > bottom1 * 1.05:
                            patterns.append(Pattern(
                                pattern_type=PatternType.DOUBLE_BOTTOM,
                                signal="bullish",
                                strength=0.8,
                                start_index=idx1,
                                end_index=idx2,
                                description="Double Bottom - Bullish reversal pattern",
                                target_price=max_between + (max_between - bottom1),
                                stop_loss=min(bottom1, bottom2) * 0.98
                            ))

        # HEAD AND SHOULDERS
        if len(local_max_idx) >= 3:
            for i in range(len(local_max_idx) - 2):
                left, head, right = local_max_idx[i], local_max_idx[i + 1], local_max_idx[i + 2]
                if head - left >= 5 and right - head >= 5:
                    left_peak = highs[left]
                    head_peak = highs[head]
                    right_peak = highs[right]

                    if (head_peak > left_peak and head_peak > right_peak and
                            abs(left_peak - right_peak) / left_peak < 0.05):
                        neckline = min(lows[left:right + 1])
                        patterns.append(Pattern(
                            pattern_type=PatternType.HEAD_SHOULDERS,
                            signal="bearish",
                            strength=0.85,
                            start_index=left,
                            end_index=right,
                            description="Head and Shoulders - Major bearish reversal",
                            target_price=neckline - (head_peak - neckline),
                            stop_loss=head_peak * 1.02
                        ))

        # INVERSE HEAD AND SHOULDERS
        if len(local_min_idx) >= 3:
            for i in range(len(local_min_idx) - 2):
                left, head, right = local_min_idx[i], local_min_idx[i + 1], local_min_idx[i + 2]
                if head - left >= 5 and right - head >= 5:
                    left_bottom = lows[left]
                    head_bottom = lows[head]
                    right_bottom = lows[right]

                    if (head_bottom < left_bottom and head_bottom < right_bottom and
                            abs(left_bottom - right_bottom) / left_bottom < 0.05):
                        neckline = max(highs[left:right + 1])
                        patterns.append(Pattern(
                            pattern_type=PatternType.INVERSE_HEAD_SHOULDERS,
                            signal="bullish",
                            strength=0.85,
                            start_index=left,
                            end_index=right,
                            description="Inverse Head and Shoulders - Major bullish reversal",
                            target_price=neckline + (neckline - head_bottom),
                            stop_loss=head_bottom * 0.98
                        ))

        # TRIANGLES (simplified detection)
        if n >= 30:
            recent = df.tail(30)
            recent_highs = recent["high"].values
            recent_lows = recent["low"].values

            # Check for converging trendlines
            high_slope = np.polyfit(range(len(recent_highs)), recent_highs, 1)[0]
            low_slope = np.polyfit(range(len(recent_lows)), recent_lows, 1)[0]

            # ASCENDING TRIANGLE
            if abs(high_slope) < 0.001 and low_slope > 0.001:
                patterns.append(Pattern(
                    pattern_type=PatternType.ASCENDING_TRIANGLE,
                    signal="bullish",
                    strength=0.75,
                    start_index=n - 30,
                    end_index=n - 1,
                    description="Ascending Triangle - Bullish continuation"
                ))

            # DESCENDING TRIANGLE
            if high_slope < -0.001 and abs(low_slope) < 0.001:
                patterns.append(Pattern(
                    pattern_type=PatternType.DESCENDING_TRIANGLE,
                    signal="bearish",
                    strength=0.75,
                    start_index=n - 30,
                    end_index=n - 1,
                    description="Descending Triangle - Bearish continuation"
                ))

            # SYMMETRICAL TRIANGLE
            if high_slope < -0.001 and low_slope > 0.001:
                patterns.append(Pattern(
                    pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                    signal="neutral",
                    strength=0.7,
                    start_index=n - 30,
                    end_index=n - 1,
                    description="Symmetrical Triangle - Breakout pending"
                ))

            # RISING WEDGE (bearish)
            if high_slope > 0 and low_slope > 0 and high_slope < low_slope:
                patterns.append(Pattern(
                    pattern_type=PatternType.RISING_WEDGE,
                    signal="bearish",
                    strength=0.7,
                    start_index=n - 30,
                    end_index=n - 1,
                    description="Rising Wedge - Bearish reversal pattern"
                ))

            # FALLING WEDGE (bullish)
            if high_slope < 0 and low_slope < 0 and high_slope > low_slope:
                patterns.append(Pattern(
                    pattern_type=PatternType.FALLING_WEDGE,
                    signal="bullish",
                    strength=0.7,
                    start_index=n - 30,
                    end_index=n - 1,
                    description="Falling Wedge - Bullish reversal pattern"
                ))

        return patterns

    def _find_local_extrema(
            self,
            data: np.ndarray,
            is_max: bool = True,
            order: int = 5
    ) -> List[int]:
        """Find local maxima or minima."""
        extrema = []

        for i in range(order, len(data) - order):
            if is_max:
                if all(data[i] >= data[i - order:i]) and all(data[i] >= data[i + 1:i + order + 1]):
                    extrema.append(i)
            else:
                if all(data[i] <= data[i - order:i]) and all(data[i] <= data[i + 1:i + order + 1]):
                    extrema.append(i)

        return extrema
