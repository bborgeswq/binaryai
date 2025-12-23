"""
Tests for technical analysis module
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.technical import TechnicalAnalyzer, TrendDirection


def generate_sample_data(n: int = 100) -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="1H")

    base_price = 100
    price = base_price
    data = []

    for i in range(n):
        change = np.random.randn() * 2
        open_price = price
        close_price = price + change
        high_price = max(open_price, close_price) + abs(np.random.randn())
        low_price = min(open_price, close_price) - abs(np.random.randn())
        volume = np.random.randint(1000, 5000)

        data.append({
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume
        })
        price = close_price

    return pd.DataFrame(data, index=dates)


class TestTechnicalAnalyzer:
    """Tests for TechnicalAnalyzer class."""

    def setup_method(self):
        """Setup for each test."""
        self.analyzer = TechnicalAnalyzer()
        self.sample_data = generate_sample_data(100)

    def test_analyze_returns_result(self):
        """Test that analyze returns a result."""
        result = self.analyzer.analyze(self.sample_data, "TEST/USD", "1h")

        assert result is not None
        assert result.symbol == "TEST/USD"
        assert result.timeframe == "1h"
        assert result.trend in TrendDirection

    def test_analyze_with_insufficient_data(self):
        """Test analyze with insufficient data."""
        small_data = generate_sample_data(10)
        result = self.analyzer.analyze(small_data, "TEST/USD", "1h")

        assert result is not None
        assert result.confidence == 0.0

    def test_indicators_calculated(self):
        """Test that indicators are calculated."""
        df = self.analyzer._add_all_indicators(self.sample_data.copy())

        assert "sma_20" in df.columns
        assert "ema_9" in df.columns
        assert "rsi" in df.columns
        assert "macd" in df.columns
        assert "bb_upper" in df.columns
        assert "stoch_k" in df.columns
        assert "atr" in df.columns

    def test_rsi_range(self):
        """Test RSI is in valid range."""
        rsi = self.analyzer._calculate_rsi(self.sample_data["close"])

        # After warmup period
        valid_rsi = rsi.dropna()
        assert all(0 <= r <= 100 for r in valid_rsi)

    def test_support_resistance_levels(self):
        """Test support/resistance detection."""
        df = self.analyzer._add_all_indicators(self.sample_data.copy())
        support, resistance = self.analyzer._find_levels(df)

        assert isinstance(support, list)
        assert isinstance(resistance, list)


class TestPatternRecognizer:
    """Tests for pattern recognition."""

    def test_import(self):
        """Test pattern recognizer imports."""
        from src.analysis.patterns import PatternRecognizer, PatternType
        pr = PatternRecognizer()
        assert pr is not None


class TestSignalGenerator:
    """Tests for signal generation."""

    def test_import(self):
        """Test signal generator imports."""
        from src.analysis.signals import SignalGenerator, SignalType
        sg = SignalGenerator()
        assert sg is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
