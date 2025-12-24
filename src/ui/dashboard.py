"""
AI Day Trader Dashboard - Enhanced Version
Real-time trading dashboard with AI analysis, news integration, and learning system
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal
import json
import os
import sys
from pathlib import Path

# Add parent path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / '.env'
load_dotenv(env_path)

from src.broker.binance_client import BinanceBroker
from src.learning.database import TradingDatabase, Trade, AIDecision
from src.data.news import NewsAggregator, get_market_sentiment

# Configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'


def get_broker():
    """Get or create Binance broker instance."""
    if 'broker' not in st.session_state:
        if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
            st.session_state.broker_connected = False
            st.session_state.broker_error = "API keys not found in .env file"
            return None

        broker = BinanceBroker(
            api_key=BINANCE_API_KEY,
            secret_key=BINANCE_SECRET_KEY,
            testnet=BINANCE_TESTNET
        )
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        connected = loop.run_until_complete(broker.connect())
        if connected:
            st.session_state.broker = broker
            st.session_state.broker_connected = True
        else:
            st.session_state.broker_connected = False
    return st.session_state.get('broker')


def get_database():
    """Get or create trading database."""
    if 'database' not in st.session_state:
        db_path = project_root / 'data' / 'trading_history.db'
        st.session_state.database = TradingDatabase(str(db_path))
    return st.session_state.database


def run_async(coro):
    """Run async function synchronously."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def fetch_live_data(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Fetch live OHLCV data from Binance."""
    broker = get_broker()
    if not broker:
        return None
    try:
        ohlcv = run_async(broker.get_ohlcv(symbol, timeframe, limit))
        if ohlcv:
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
    except Exception as e:
        pass
    return None


def fetch_ticker(symbol: str):
    """Fetch live ticker data."""
    broker = get_broker()
    if not broker:
        return None
    try:
        return run_async(broker.get_ticker(symbol))
    except:
        return None


def fetch_account():
    """Fetch account info."""
    broker = get_broker()
    if not broker:
        return None
    try:
        return run_async(broker.get_account())
    except:
        return None


def run_dashboard():
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="AI Day Trader",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Enhanced CSS for game-like UI
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@400;500;700&display=swap');

    .main-header {
        font-family: 'Orbitron', monospace;
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00ff88, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 10px;
        margin-bottom: 20px;
    }

    .status-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0, 255, 136, 0.1);
    }

    .signal-buy {
        background: linear-gradient(135deg, #0d4d0d 0%, #1a472a 100%);
        border: 2px solid #00ff00;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        animation: pulse-green 2s infinite;
    }

    .signal-sell {
        background: linear-gradient(135deg, #4d0d0d 0%, #472a1a 100%);
        border: 2px solid #ff0000;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        animation: pulse-red 2s infinite;
    }

    .signal-hold {
        background: linear-gradient(135deg, #4d4d0d 0%, #47471a 100%);
        border: 2px solid #ffff00;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
    }

    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 20px rgba(0, 255, 0, 0.3); }
        50% { box-shadow: 0 0 40px rgba(0, 255, 0, 0.6); }
    }

    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 20px rgba(255, 0, 0, 0.3); }
        50% { box-shadow: 0 0 40px rgba(255, 0, 0, 0.6); }
    }

    .metric-value {
        font-family: 'Rajdhani', sans-serif;
        font-size: 2rem;
        font-weight: 700;
    }

    .news-card {
        background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
        border-left: 4px solid #00d4ff;
        padding: 15px;
        margin: 10px 0;
        border-radius: 0 10px 10px 0;
    }

    .bullish-text { color: #00ff88; }
    .bearish-text { color: #ff4444; }
    .neutral-text { color: #ffff00; }

    .ai-thinking {
        background: linear-gradient(90deg, #1a1a2e, #16213e, #1a1a2e);
        background-size: 200% 100%;
        animation: thinking 2s ease infinite;
        border-radius: 10px;
        padding: 15px;
    }

    @keyframes thinking {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .stMetric > div {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #0f3460;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #1a1a2e;
        border-radius: 10px;
        padding: 10px 20px;
        border: 1px solid #0f3460;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0f3460 0%, #1a472a 100%);
        border-color: #00ff88;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<h1 class="main-header">🤖 AI DAY TRADER</h1>', unsafe_allow_html=True)

    # Initialize connections
    broker = get_broker()
    db = get_database()

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚡ CONTROL CENTER")

        # Connection Status
        if st.session_state.get('broker_connected', False):
            st.success("🟢 BINANCE CONNECTED")
            if BINANCE_TESTNET:
                st.info("📋 TESTNET MODE")
        else:
            st.error("🔴 DISCONNECTED")
            if st.button("🔄 Reconnect"):
                if 'broker' in st.session_state:
                    del st.session_state['broker']
                get_broker()
                st.rerun()

        st.divider()

        # Agent Controls
        st.markdown("### 🎮 AGENT CONTROLS")

        agent_running = st.session_state.get('agent_running', False)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ START" if not agent_running else "🟢 RUNNING",
                        use_container_width=True,
                        type="primary" if not agent_running else "secondary"):
                st.session_state.agent_running = True
        with col2:
            if st.button("⏹️ STOP", use_container_width=True):
                st.session_state.agent_running = False

        # Trading Mode
        st.divider()
        st.markdown("### 📊 SETTINGS")

        symbols = st.multiselect(
            "Trading Pairs",
            ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT", "ADA/USDT", "DOGE/USDT"],
            default=["BTC/USDT", "ETH/USDT"]
        )

        timeframe = st.selectbox(
            "Timeframe",
            ["1m", "5m", "15m", "1h", "4h", "1d"],
            index=3
        )

        st.divider()

        # Risk Settings
        st.markdown("### 🛡️ RISK MANAGEMENT")
        max_risk = st.slider("Risk per Trade", 1.0, 5.0, 2.0, 0.5, format="%.1f%%")
        max_positions = st.slider("Max Positions", 1, 10, 3)
        daily_loss_limit = st.slider("Daily Loss Limit", 1.0, 10.0, 5.0, 0.5, format="%.1f%%")

    # Main Content Area
    # Top Stats Bar
    account = fetch_account()
    stats = db.get_performance_stats(days=30)

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        if account:
            st.metric("💰 Portfolio", f"${float(account.equity):,.2f}")
        else:
            st.metric("💰 Portfolio", "---")

    with col2:
        if account:
            st.metric("💵 Available", f"${float(account.cash):,.2f}")
        else:
            st.metric("💵 Available", "---")

    with col3:
        st.metric("📈 Total Trades", stats.get('total_trades', 0))

    with col4:
        win_rate = stats.get('win_rate', 0)
        st.metric("🎯 Win Rate", f"{win_rate:.1f}%")

    with col5:
        total_pnl = stats.get('total_pnl', 0)
        st.metric("💎 Total P&L", f"${total_pnl:,.2f}",
                  delta=f"{'+' if total_pnl >= 0 else ''}{total_pnl:.2f}")

    with col6:
        status = "🟢 ACTIVE" if st.session_state.get('agent_running', False) else "🔴 STOPPED"
        st.metric("🤖 AI Status", status)

    st.divider()

    # Main Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 LIVE CHARTS",
        "🧠 AI ANALYSIS",
        "📰 NEWS & SENTIMENT",
        "💼 POSITIONS",
        "📜 HISTORY",
        "🎓 LEARNING"
    ])

    with tab1:
        render_live_charts(symbols, timeframe)

    with tab2:
        render_ai_analysis(symbols, db)

    with tab3:
        render_news_section()

    with tab4:
        render_positions()

    with tab5:
        render_trade_history(db)

    with tab6:
        render_learning_section(db)

    # Footer
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.caption(f"⏰ Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if st.button("🔄 REFRESH DATA", use_container_width=True):
            st.rerun()


def render_live_charts(symbols: list, timeframe: str):
    """Render live trading charts."""
    selected = st.selectbox("Select Trading Pair", symbols if symbols else ["BTC/USDT"])

    df = fetch_live_data(selected, timeframe, 100)
    ticker = fetch_ticker(selected)

    if df is None or df.empty:
        df = generate_sample_ohlcv(100)
        st.warning("⚠️ Using sample data - check Binance connection")

    # Price metrics
    col1, col2, col3, col4 = st.columns(4)

    if ticker:
        with col1:
            price = ticker.get('last', df['close'].iloc[-1])
            change = ticker.get('percentage', 0)
            st.metric("💲 Price", f"${price:,.2f}", f"{change:+.2f}%")
        with col2:
            st.metric("📈 24h High", f"${ticker.get('high', df['high'].max()):,.2f}")
        with col3:
            st.metric("📉 24h Low", f"${ticker.get('low', df['low'].min()):,.2f}")
        with col4:
            vol = ticker.get('quoteVolume', df['volume'].sum())
            st.metric("📊 24h Volume", f"${vol:,.0f}")

    # Create chart
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("", "RSI", "MACD")
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price",
        increasing_line_color='#00ff88', decreasing_line_color='#ff4444'
    ), row=1, col=1)

    # EMAs
    ema9 = df["close"].ewm(span=9).mean()
    ema21 = df["close"].ewm(span=21).mean()
    fig.add_trace(go.Scatter(x=df.index, y=ema9, name="EMA 9",
                             line=dict(color="#00d4ff", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ema21, name="EMA 21",
                             line=dict(color="#ff9500", width=1)), row=1, col=1)

    # Bollinger Bands
    sma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    fig.add_trace(go.Scatter(x=df.index, y=sma20 + 2*std20, name="BB Upper",
                             line=dict(color="gray", dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma20 - 2*std20, name="BB Lower",
                             line=dict(color="gray", dash="dash"),
                             fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

    # RSI
    rsi = calculate_rsi(df["close"])
    fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI",
                             line=dict(color="#9966ff")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#ff4444", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00ff88", row=2, col=1)

    # MACD
    macd, signal, hist = calculate_macd(df["close"])
    fig.add_trace(go.Scatter(x=df.index, y=macd, name="MACD",
                             line=dict(color="#00d4ff")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=signal, name="Signal",
                             line=dict(color="#ff9500")), row=3, col=1)
    colors = ["#00ff88" if h >= 0 else "#ff4444" for h in hist.fillna(0)]
    fig.add_trace(go.Bar(x=df.index, y=hist, name="Histogram",
                         marker_color=colors), row=3, col=1)

    fig.update_layout(
        height=700,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26,26,46,0.8)',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=30, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)


def render_ai_analysis(symbols: list, db: TradingDatabase):
    """Render AI analysis section."""
    selected = symbols[0] if symbols else "BTC/USDT"
    df = fetch_live_data(selected, "1h", 50)
    ticker = fetch_ticker(selected)

    if df is None or df.empty:
        df = generate_sample_ohlcv(50)

    # Calculate signals
    rsi = calculate_rsi(df["close"]).iloc[-1]
    macd, signal_line, hist = calculate_macd(df["close"])
    ema9 = df["close"].ewm(span=9).mean().iloc[-1]
    ema21 = df["close"].ewm(span=21).mean().iloc[-1]
    current_price = df["close"].iloc[-1]

    # Determine overall signal
    bullish_signals = 0
    bearish_signals = 0

    if rsi < 30: bullish_signals += 1
    elif rsi > 70: bearish_signals += 1

    if macd.iloc[-1] > signal_line.iloc[-1]: bullish_signals += 1
    else: bearish_signals += 1

    if ema9 > ema21: bullish_signals += 1
    else: bearish_signals += 1

    if bullish_signals > bearish_signals:
        signal = "BUY"
        signal_class = "signal-buy"
        confidence = int((bullish_signals / 3) * 100)
    elif bearish_signals > bullish_signals:
        signal = "SELL"
        signal_class = "signal-sell"
        confidence = int((bearish_signals / 3) * 100)
    else:
        signal = "HOLD"
        signal_class = "signal-hold"
        confidence = 50

    col1, col2 = st.columns([1, 1])

    with col1:
        # Signal Card
        price_str = f"${ticker.get('last', current_price):,.2f}" if ticker else f"${current_price:,.2f}"

        st.markdown(f"""
        <div class="{signal_class}">
            <h1 style="color: {'#00ff88' if signal == 'BUY' else '#ff4444' if signal == 'SELL' else '#ffff00'};
                       font-size: 3rem; margin: 0; font-family: 'Orbitron', monospace;">
                {'📈' if signal == 'BUY' else '📉' if signal == 'SELL' else '⏸️'} {signal}
            </h1>
            <p style="color: white; font-size: 1.5rem; margin: 10px 0;">
                Confidence: <strong>{confidence}%</strong>
            </p>
            <p style="color: #aaa; font-size: 1.2rem;">
                {selected} @ {price_str}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Indicator Summary
        st.markdown("### 📊 Indicator Breakdown")
        indicators = pd.DataFrame({
            "Indicator": ["RSI (14)", "MACD", "EMA Cross", "Bollinger"],
            "Value": [
                f"{rsi:.1f}",
                "Bullish" if macd.iloc[-1] > signal_line.iloc[-1] else "Bearish",
                "Golden" if ema9 > ema21 else "Death",
                "Middle"
            ],
            "Signal": [
                "🟢 BUY" if rsi < 30 else "🔴 SELL" if rsi > 70 else "🟡 NEUTRAL",
                "🟢 BUY" if macd.iloc[-1] > signal_line.iloc[-1] else "🔴 SELL",
                "🟢 BUY" if ema9 > ema21 else "🔴 SELL",
                "🟡 NEUTRAL"
            ]
        })
        st.dataframe(indicators, use_container_width=True, hide_index=True)

    with col2:
        # AI Context from Database
        st.markdown("### 🧠 AI Learning Context")
        context = db.get_context_for_ai(selected)
        st.markdown(f"""
        <div class="ai-thinking">
            <pre style="color: #00ff88; font-family: monospace; white-space: pre-wrap;">{context}</pre>
        </div>
        """, unsafe_allow_html=True)

        # Support/Resistance
        st.markdown("### 📍 Key Levels")
        high = df['high'].iloc[-20:].max()
        low = df['low'].iloc[-20:].min()
        pivot = (high + low + current_price) / 3

        levels = pd.DataFrame({
            "Level": ["Resistance 2", "Resistance 1", "Pivot", "Support 1", "Support 2"],
            "Price": [
                f"${pivot + (high - low):,.2f}",
                f"${2 * pivot - low:,.2f}",
                f"${pivot:,.2f}",
                f"${2 * pivot - high:,.2f}",
                f"${pivot - (high - low):,.2f}"
            ]
        })
        st.dataframe(levels, use_container_width=True, hide_index=True)

    # Confidence Gauge
    st.markdown("### 📈 Signal Strength")
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence,
        title={'text': f"{'Bullish' if signal == 'BUY' else 'Bearish' if signal == 'SELL' else 'Neutral'} Sentiment"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "#00ff88" if signal == "BUY" else "#ff4444" if signal == "SELL" else "#ffff00"},
            'steps': [
                {'range': [0, 30], 'color': "#4d1a1a"},
                {'range': [30, 50], 'color': "#4d3d1a"},
                {'range': [50, 70], 'color': "#4d4d1a"},
                {'range': [70, 100], 'color': "#1a4d1a"}
            ]
        }
    ))
    gauge.update_layout(height=250, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(gauge, use_container_width=True)


def render_news_section():
    """Render news and sentiment section."""
    st.markdown("### 📰 Market News & Sentiment")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Fetch news
        try:
            news_aggregator = NewsAggregator()
            articles = run_async(news_aggregator.fetch_all_news(limit=10))

            if articles:
                for article in articles[:5]:
                    sentiment_color = "#00ff88" if article.sentiment == "positive" else "#ff4444" if article.sentiment == "negative" else "#888"
                    st.markdown(f"""
                    <div class="news-card">
                        <h4 style="color: white; margin: 0 0 10px 0;">{article.title}</h4>
                        <p style="color: #aaa; font-size: 0.9rem; margin: 0;">
                            📰 {article.source} | 🕐 {article.published_at[:10] if article.published_at else 'Unknown'}
                            <span style="color: {sentiment_color}; margin-left: 10px;">
                                {'📈 Bullish' if article.sentiment == 'positive' else '📉 Bearish' if article.sentiment == 'negative' else ''}
                            </span>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("📭 No news available at the moment")
        except Exception as e:
            st.info("📭 News feed loading...")

    with col2:
        st.markdown("### 🎯 Market Sentiment")

        try:
            sentiment = run_async(get_market_sentiment())

            overall = sentiment.get('overall', 'neutral')
            positive = sentiment.get('positive_count', 0)
            negative = sentiment.get('negative_count', 0)
            neutral = sentiment.get('neutral_count', 0)

            # Sentiment gauge
            if overall == "bullish":
                score = 75
                color = "#00ff88"
            elif overall == "bearish":
                score = 25
                color = "#ff4444"
            else:
                score = 50
                color = "#ffff00"

            st.markdown(f"""
            <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 15px;">
                <h2 style="color: {color}; font-family: 'Orbitron', monospace;">
                    {overall.upper()}
                </h2>
                <p style="color: white;">
                    🟢 Bullish: {positive} | 🔴 Bearish: {negative} | 🟡 Neutral: {neutral}
                </p>
            </div>
            """, unsafe_allow_html=True)

        except:
            st.info("Sentiment analysis loading...")

        # Trending coins
        st.markdown("### 🔥 Trending")
        try:
            news_agg = NewsAggregator()
            trending = run_async(news_agg.get_trending_coins())
            if trending:
                for coin in trending[:5]:
                    st.markdown(f"🪙 **{coin.get('symbol', 'N/A')}** - {coin.get('name', 'Unknown')}")
        except:
            st.info("Trending data loading...")


def render_positions():
    """Render positions section."""
    st.markdown("### 💼 Current Positions")

    broker = get_broker()
    if not broker:
        st.warning("⚠️ Connect to Binance to view positions")
        return

    try:
        positions = run_async(broker.get_positions())

        if not positions:
            st.info("📭 No open positions")

            # Manual trade interface
            st.markdown("### ⚡ Quick Trade")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                symbol = st.selectbox("Pair", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
            with col2:
                side = st.selectbox("Side", ["BUY", "SELL"])
            with col3:
                amount = st.number_input("Amount", min_value=0.0001, value=0.001)
            with col4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚀 Execute", type="primary", use_container_width=True):
                    st.info("Trading will be enabled when agent is active")
        else:
            positions_data = []
            for p in positions:
                positions_data.append({
                    "Symbol": p.symbol,
                    "Side": "🟢 LONG" if "LONG" in str(p.side) else "🔴 SHORT",
                    "Quantity": float(p.quantity),
                    "Entry": f"${float(p.entry_price):,.2f}",
                    "Current": f"${float(p.current_price):,.2f}",
                    "P&L": f"${float(p.unrealized_pnl):,.2f}",
                    "P&L %": f"{p.unrealized_pnl_pct:.2f}%"
                })
            st.dataframe(pd.DataFrame(positions_data), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error loading positions: {e}")


def render_trade_history(db: TradingDatabase):
    """Render trade history section."""
    st.markdown("### 📜 Trade History")

    trades = db.get_recent_trades(limit=20)

    if not trades:
        st.info("📭 No trade history yet. Start the AI agent to begin trading.")
        return

    trades_data = []
    for t in trades:
        trades_data.append({
            "Time": t.entry_time[:19] if t.entry_time else "N/A",
            "Symbol": t.symbol,
            "Side": "🟢 BUY" if t.side == "BUY" else "🔴 SELL",
            "Entry": f"${t.entry_price:,.2f}",
            "Exit": f"${t.exit_price:,.2f}" if t.exit_price else "Open",
            "P&L": f"${t.pnl:+,.2f}" if t.status == "closed" else "-",
            "Status": "✅" if t.status == "closed" else "🟡"
        })

    st.dataframe(pd.DataFrame(trades_data), use_container_width=True, hide_index=True)

    # Stats
    stats = db.get_performance_stats(days=30)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", stats.get('total_trades', 0))
    with col2:
        st.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
    with col3:
        st.metric("Avg Win", f"${stats.get('avg_win', 0):,.2f}")
    with col4:
        st.metric("Avg Loss", f"${stats.get('avg_loss', 0):,.2f}")


def render_learning_section(db: TradingDatabase):
    """Render AI learning section."""
    st.markdown("### 🎓 AI Learning & Insights")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Performance by Symbol")
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        perf_data = []
        for sym in symbols:
            p = db.get_symbol_performance(sym, days=30)
            perf_data.append({
                "Symbol": sym,
                "Trades": p.get('total_trades', 0),
                "Win Rate": f"{p.get('win_rate', 0):.1f}%",
                "P&L": f"${p.get('total_pnl', 0):,.2f}"
            })
        st.dataframe(pd.DataFrame(perf_data), use_container_width=True, hide_index=True)

        # Generate new insights
        if st.button("🔄 Generate New Insights"):
            insights = db.learn_from_history()
            st.success(f"Generated {len(insights)} new insights!")
            st.rerun()

    with col2:
        st.markdown("#### 💡 AI Insights")
        insights = db.get_insights(limit=5)

        if insights:
            for insight in insights:
                icon = "📈" if insight.insight_type == "performance" else "🪙" if insight.insight_type == "symbol" else "💡"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1a1a2e, #16213e);
                            padding: 15px; border-radius: 10px; margin: 10px 0;
                            border-left: 4px solid #00ff88;">
                    <p style="color: white; margin: 0;">
                        {icon} {insight.description}
                    </p>
                    <small style="color: #888;">Confidence: {insight.confidence:.0%}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("💡 No insights yet. Trade more to generate learning insights!")

    # Decision Accuracy
    st.markdown("#### 🎯 AI Decision Accuracy")
    accuracy = db.get_decision_accuracy(days=30)

    if accuracy:
        acc_data = []
        for action, data in accuracy.items():
            acc_data.append({
                "Action": action,
                "Decisions": data.get('total_decisions', 0),
                "Accuracy": f"{data.get('accuracy', 0):.1f}%",
                "Avg Confidence": f"{data.get('avg_confidence', 0):.1f}%",
                "Avg P&L": f"${data.get('avg_pnl', 0):,.2f}"
            })
        st.dataframe(pd.DataFrame(acc_data), use_container_width=True, hide_index=True)
    else:
        st.info("📊 Decision data will appear after the AI makes some trades")


# Helper functions
def generate_sample_ohlcv(n: int) -> pd.DataFrame:
    """Generate sample OHLCV data."""
    import numpy as np
    np.random.seed(int(datetime.now().timestamp()) % 100)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="1h")

    price = 95000
    data = []
    for _ in range(n):
        change = np.random.randn() * 500
        o = price
        c = price + change
        h = max(o, c) + abs(np.random.randn() * 200)
        l = min(o, c) - abs(np.random.randn() * 200)
        v = np.random.randint(100000000, 500000000)
        data.append({"open": o, "high": h, "low": l, "close": c, "volume": v})
        price = c

    return pd.DataFrame(data, index=dates)


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: pd.Series):
    """Calculate MACD."""
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    hist = macd - signal
    return macd, signal, hist


if __name__ == "__main__":
    run_dashboard()
