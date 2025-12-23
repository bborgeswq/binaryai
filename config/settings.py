"""
AI Day Trader - Configuration Settings
"""
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


class APIKeys(BaseModel):
    """API Keys configuration"""
    alpaca_api_key: str = Field(default_factory=lambda: os.getenv("ALPACA_API_KEY", ""))
    alpaca_secret_key: str = Field(default_factory=lambda: os.getenv("ALPACA_SECRET_KEY", ""))
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))


class TradingConfig(BaseModel):
    """Trading configuration"""
    # Mode
    mode: Literal["paper", "live"] = "paper"  # ALWAYS start with paper

    # Markets
    markets: list[str] = ["crypto"]  # crypto, stocks, forex

    # Risk Management
    max_position_size_pct: float = 0.1  # Max 10% of portfolio per position
    max_risk_per_trade_pct: float = 0.02  # Max 2% risk per trade
    max_daily_loss_pct: float = 0.05  # Stop trading if down 5% daily
    max_open_positions: int = 3

    # Trading Parameters
    default_timeframe: str = "1h"  # 1 hour candles
    symbols: list[str] = ["BTC/USD", "ETH/USD"]  # Default trading pairs

    # Stop Loss / Take Profit
    default_stop_loss_pct: float = 0.02  # 2% stop loss
    default_take_profit_pct: float = 0.04  # 4% take profit (2:1 R/R)
    use_trailing_stop: bool = True
    trailing_stop_pct: float = 0.015  # 1.5% trailing


class AIConfig(BaseModel):
    """AI/ML configuration"""
    # LLM Settings
    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.3  # Lower = more consistent

    # Analysis Settings
    use_technical_analysis: bool = True
    use_pattern_recognition: bool = True
    use_sentiment_analysis: bool = True
    use_llm_reasoning: bool = True

    # Confidence Thresholds
    min_confidence_to_trade: float = 0.7  # 70% confidence minimum

    # Technical Indicators to Use
    indicators: list[str] = [
        "RSI", "MACD", "BB", "EMA", "SMA",
        "ATR", "VWAP", "OBV", "ADX", "STOCH"
    ]


class DashboardConfig(BaseModel):
    """Dashboard configuration"""
    host: str = "localhost"
    port: int = 8501
    refresh_rate_seconds: int = 5
    show_ai_reasoning: bool = True
    chart_theme: Literal["dark", "light"] = "dark"


class Settings(BaseModel):
    """Main settings container"""
    api_keys: APIKeys = Field(default_factory=APIKeys)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings


def update_settings(**kwargs):
    """Update settings dynamically"""
    global settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
