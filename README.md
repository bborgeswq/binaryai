# 🤖 AI Day Trader

An autonomous AI-powered day trading system that analyzes cryptocurrency and stock markets using advanced technical analysis, pattern recognition, and LLM-based reasoning.

## Features

- **Multi-Asset Support**: Trade crypto (BTC, ETH, etc.) and stocks
- **AI-Powered Analysis**: Uses Claude/GPT for market analysis and reasoning
- **Technical Indicators**: RSI, MACD, Bollinger Bands, Stochastic, ADX, and more
- **Pattern Recognition**: Candlestick patterns (Doji, Hammer, Engulfing) and chart patterns (Double Top, Head & Shoulders)
- **Risk Management**: Position sizing, stop losses, daily loss limits, and correlation checks
- **Real-Time Dashboard**: Streamlit-based UI showing live charts, signals, and AI reasoning
- **Paper Trading**: Test strategies without risking real money
- **Multiple Brokers**: Alpaca integration (crypto + stocks), with paper trading fallback

## Quick Start

### 1. Prerequisites

- Python 3.10+
- pip or conda

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-day-trader.git
cd ai-day-trader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use any text editor
```

Required API keys:
- **Alpaca** (free): Sign up at https://alpaca.markets
- **Anthropic** (optional, for LLM): Sign up at https://console.anthropic.com

### 4. Run the Bot

```bash
# Start paper trading (recommended for testing)
python -m src.main trade --paper

# Launch the dashboard
python -m src.main dashboard

# Run backtest (coming soon)
python -m src.main backtest --days 30
```

## Architecture

```
ai-day-trader/
├── config/
│   └── settings.py          # Configuration management
├── src/
│   ├── broker/              # Broker integrations
│   │   ├── alpaca_client.py # Alpaca API client
│   │   └── paper_trading.py # Local paper trading
│   ├── data/                # Market data
│   │   ├── market_data.py   # Real-time data provider
│   │   └── historical.py    # Historical data manager
│   ├── analysis/            # Technical analysis
│   │   ├── technical.py     # Indicators (RSI, MACD, etc.)
│   │   ├── patterns.py      # Pattern recognition
│   │   └── signals.py       # Signal generation
│   ├── ai/                  # AI/ML components
│   │   ├── llm_analyzer.py  # LLM market analysis
│   │   ├── decision_engine.py # Trading decisions
│   │   └── agent.py         # Autonomous agent
│   ├── trading/             # Trade execution
│   │   ├── risk_manager.py  # Risk management
│   │   ├── executor.py      # Trade execution
│   │   └── portfolio.py     # Portfolio management
│   ├── ui/                  # User interface
│   │   └── dashboard.py     # Streamlit dashboard
│   └── main.py              # Entry point
└── requirements.txt
```

## How It Works

### 1. Data Collection
The system collects real-time OHLCV (Open, High, Low, Close, Volume) data from multiple sources:
- Alpaca (stocks and crypto)
- CCXT (60+ crypto exchanges)
- Yahoo Finance (backup for stocks)

### 2. Technical Analysis
Calculates 15+ technical indicators:
- **Trend**: SMA, EMA, ADX
- **Momentum**: RSI, MACD, Stochastic
- **Volatility**: Bollinger Bands, ATR
- **Volume**: OBV, VWAP

### 3. Pattern Recognition
Detects candlestick and chart patterns:
- **Single candle**: Doji, Hammer, Shooting Star
- **Multi-candle**: Engulfing, Morning Star, Three Crows
- **Chart patterns**: Double Top/Bottom, Head & Shoulders, Triangles

### 4. AI Analysis
Uses Claude (or GPT) to:
- Synthesize all technical data
- Identify market sentiment
- Evaluate risk/reward scenarios
- Provide reasoning for decisions

### 5. Decision Engine
Combines all signals with configurable weights:
- Technical Analysis: 40%
- Pattern Recognition: 25%
- LLM Analysis: 35%

### 6. Risk Management
Before any trade:
- Position size limits
- Stop loss requirements
- Daily loss limits
- Correlation checks
- Cool-down after losses

### 7. Execution
Executes trades through the broker with:
- Automatic stop losses
- Take profit targets
- Trailing stops (optional)

## Dashboard

The Streamlit dashboard provides:
- Live candlestick charts with indicators
- Real-time AI signals and reasoning
- Position management
- Trade history
- Performance metrics

Launch it with:
```bash
python -m src.main dashboard
```

## Configuration Options

### Trading Settings
```python
# config/settings.py
trading:
  mode: "paper"               # paper or live
  symbols: ["BTC/USD", "ETH/USD"]
  default_timeframe: "1h"
  max_position_size_pct: 0.1  # 10% max per position
  max_risk_per_trade_pct: 0.02  # 2% risk per trade
  max_daily_loss_pct: 0.05    # Stop if down 5%
  max_open_positions: 3
```

### AI Settings
```python
ai:
  llm_provider: "anthropic"
  llm_model: "claude-sonnet-4-20250514"
  min_confidence_to_trade: 0.7
  use_llm_reasoning: true
```

## Safety Features

1. **Paper Trading First**: Always starts in paper mode
2. **Live Mode Confirmation**: Requires typing "yes" to enable live trading
3. **Emergency Stop**: Auto-closes at 5% daily loss
4. **Position Limits**: Max 3 concurrent positions
5. **Risk Per Trade**: Max 2% of portfolio at risk
6. **Stop Loss Required**: No trades without stop loss
7. **Consecutive Loss Pause**: Pauses after 5 losses

## Development

### Running Tests
```bash
pytest tests/
```

### Adding New Indicators
Add to `src/analysis/technical.py`:
```python
def _calculate_your_indicator(self, df):
    # Your indicator logic
    pass
```

### Adding New Patterns
Add to `src/analysis/patterns.py`:
```python
# In _find_candlestick_patterns or _find_chart_patterns
```

## Disclaimer

**This software is for educational purposes only.**

- Trading involves substantial risk of loss
- Past performance does not guarantee future results
- Never trade with money you can't afford to lose
- This is NOT financial advice

The authors are not responsible for any financial losses incurred through the use of this software.

## License

MIT License - see LICENSE file

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

---

Made with 🤖 and ❤️
