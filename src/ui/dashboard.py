"""
AI Day Trader Dashboard - Enhanced Version with Visual AI Activity
Real-time trading dashboard showing AI decisions, markers, and reasoning
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
import os
import sys
from pathlib import Path

# Add parent path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.broker.binance_client import BinanceBroker
from src.learning.database import TradingDatabase, Trade, AIDecision
from src.data.news import NewsAggregator, get_market_sentiment
from src.ai.activity_tracker import AIActivityTracker, ActivityType, ChartMarker, get_tracker

# LLM Integration
LLM_AVAILABLE = False
LLMAnalyzer = None
try:
    from src.ai.llm_analyzer import LLMAnalyzer as _LLMAnalyzer, MarketAnalysis
    LLMAnalyzer = _LLMAnalyzer
    LLM_AVAILABLE = True
except ImportError:
    pass

# Configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')


def get_broker():
    """Get or create Binance broker instance."""
    if 'broker' not in st.session_state:
        if not BINANCE_API_KEY or not BINANCE_SECRET_KEY:
            st.session_state.broker_connected = False
            return None
        broker = BinanceBroker(BINANCE_API_KEY, BINANCE_SECRET_KEY, testnet=BINANCE_TESTNET)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if loop.run_until_complete(broker.connect()):
            st.session_state.broker = broker
            st.session_state.broker_connected = True
        else:
            st.session_state.broker_connected = False
    return st.session_state.get('broker')


def get_database():
    """Get or create trading database."""
    if 'database' not in st.session_state:
        st.session_state.database = TradingDatabase(str(project_root / 'data' / 'trading_history.db'))
    return st.session_state.database


def get_activity_tracker():
    """Get or create AI activity tracker."""
    if 'activity_tracker' not in st.session_state:
        st.session_state.activity_tracker = AIActivityTracker()
    return st.session_state.activity_tracker


def get_llm_analyzer():
    """Get or create LLM analyzer if API key available."""
    if 'llm_analyzer' not in st.session_state:
        if LLM_AVAILABLE and ANTHROPIC_API_KEY:
            try:
                st.session_state.llm_analyzer = LLMAnalyzer(
                    api_key=ANTHROPIC_API_KEY,
                    provider="anthropic"
                )
            except Exception as e:
                st.session_state.llm_analyzer = None
        elif LLM_AVAILABLE and OPENAI_API_KEY:
            try:
                st.session_state.llm_analyzer = LLMAnalyzer(
                    api_key=OPENAI_API_KEY,
                    provider="openai"
                )
            except Exception as e:
                st.session_state.llm_analyzer = None
        else:
            st.session_state.llm_analyzer = None
    return st.session_state.get('llm_analyzer')


def run_async(coro):
    """Run async function synchronously."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def fetch_live_data(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Fetch live OHLCV data."""
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
    except:
        pass
    return None


def fetch_ticker(symbol: str):
    """Fetch ticker data."""
    broker = get_broker()
    if not broker:
        return None
    try:
        return run_async(broker.get_ticker(symbol))
    except:
        return None


def run_dashboard():
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="AI Day Trader",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Enhanced CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@400;500;700&family=JetBrains+Mono&display=swap');

    .main-header {
        font-family: 'Orbitron', monospace;
        font-size: 2.5rem;
        background: linear-gradient(90deg, #00ff88, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 10px;
    }

    .signal-buy {
        background: linear-gradient(135deg, #0d4d0d, #1a472a);
        border: 2px solid #00ff00;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        animation: pulse-green 2s infinite;
    }
    .signal-sell {
        background: linear-gradient(135deg, #4d0d0d, #472a1a);
        border: 2px solid #ff0000;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        animation: pulse-red 2s infinite;
    }
    .signal-hold {
        background: linear-gradient(135deg, #4d4d0d, #47471a);
        border: 2px solid #ffff00;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
    }

    @keyframes pulse-green {
        0%, 100% { box-shadow: 0 0 20px rgba(0,255,0,0.3); }
        50% { box-shadow: 0 0 40px rgba(0,255,0,0.6); }
    }
    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 0 20px rgba(255,0,0,0.3); }
        50% { box-shadow: 0 0 40px rgba(255,0,0,0.6); }
    }

    .ai-console {
        background: #0a0a0f;
        border: 1px solid #00ff88;
        border-radius: 10px;
        padding: 15px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        max-height: 400px;
        overflow-y: auto;
    }
    .ai-line { margin: 5px 0; }
    .ai-time { color: #666; }
    .ai-type-analyzing { color: #00d4ff; }
    .ai-type-signal { color: #00ff88; }
    .ai-type-trade { color: #ff9500; }
    .ai-type-error { color: #ff4444; }
    .ai-type-thinking { color: #9966ff; }

    .ai-thinking-box {
        background: linear-gradient(90deg, #1a1a2e, #16213e, #1a1a2e);
        background-size: 200% 100%;
        animation: thinking 3s ease infinite;
        border-radius: 10px;
        padding: 20px;
        border-left: 4px solid #00ff88;
    }
    @keyframes thinking {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .activity-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        border-left: 4px solid #00d4ff;
    }
    .activity-important {
        border-left-color: #00ff88;
        background: linear-gradient(135deg, #0d2d0d, #1a3d2a);
    }

    .marker-info {
        background: rgba(0,0,0,0.8);
        border: 1px solid #00ff88;
        border-radius: 8px;
        padding: 10px;
        font-size: 0.8rem;
    }

    .stMetric > div {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #0f3460;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<h1 class="main-header">🤖 AI DAY TRADER</h1>', unsafe_allow_html=True)

    # Initialize
    broker = get_broker()
    db = get_database()
    tracker = get_activity_tracker()

    # Sidebar
    with st.sidebar:
        render_sidebar(tracker)

    # Main content
    render_main_content(db, tracker)


def render_sidebar(tracker: AIActivityTracker):
    """Render sidebar controls."""
    st.markdown("### ⚡ CONTROL CENTER")

    # Connection status
    if st.session_state.get('broker_connected'):
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

    # LLM Status
    st.divider()
    st.markdown("### 🧠 AI ENGINE")
    if ANTHROPIC_API_KEY:
        st.success("🟢 Claude API Ready")
    elif OPENAI_API_KEY:
        st.success("🟢 OpenAI API Ready")
    else:
        st.warning("🟡 No LLM (using indicators only)")

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
            tracker.log_activity(ActivityType.THINKING, "SYSTEM", "Agent Started", "AI trading agent is now active")
    with col2:
        if st.button("⏹️ STOP", use_container_width=True):
            st.session_state.agent_running = False
            tracker.log_activity(ActivityType.THINKING, "SYSTEM", "Agent Stopped", "AI trading agent stopped")

    st.divider()

    # Settings
    st.markdown("### 📊 SETTINGS")
    symbols = st.multiselect(
        "Trading Pairs",
        ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT", "ADA/USDT"],
        default=["BTC/USDT", "ETH/USDT"],
        key="symbols"
    )
    st.session_state.selected_symbols = symbols

    timeframe = st.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"], index=3, key="timeframe")
    st.session_state.selected_timeframe = timeframe

    st.divider()

    # Risk
    st.markdown("### 🛡️ RISK")
    st.slider("Risk per Trade", 1.0, 5.0, 2.0, 0.5, format="%.1f%%", key="risk")
    st.slider("Max Positions", 1, 10, 3, key="max_pos")


def render_main_content(db: TradingDatabase, tracker: AIActivityTracker):
    """Render main content area."""
    symbols = st.session_state.get('selected_symbols', ["BTC/USDT"])
    timeframe = st.session_state.get('selected_timeframe', "1h")

    # Top metrics
    render_top_metrics(db)

    st.divider()

    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 LIVE CHARTS",
        "🤖 AI ACTIVITY",
        "🧠 AI ANALYSIS",
        "📰 NEWS",
        "📜 HISTORY",
        "🎓 LEARNING"
    ])

    with tab1:
        render_charts_with_markers(symbols, timeframe, tracker)

    with tab2:
        render_ai_activity_panel(tracker)

    with tab3:
        render_ai_analysis(symbols, db, tracker)

    with tab4:
        render_news_section()

    with tab5:
        render_trade_history(db)

    with tab6:
        render_learning_section(db)

    # Footer
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.caption(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if st.button("🔄 REFRESH", use_container_width=True):
            st.rerun()


def render_top_metrics(db: TradingDatabase):
    """Render top metrics bar."""
    broker = get_broker()
    stats = db.get_performance_stats(days=30)

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        if broker:
            try:
                account = run_async(broker.get_account())
                st.metric("💰 Portfolio", f"${float(account.equity):,.2f}")
            except:
                st.metric("💰 Portfolio", "---")
        else:
            st.metric("💰 Portfolio", "---")

    with col2:
        st.metric("📈 Trades", stats.get('total_trades', 0))

    with col3:
        st.metric("🎯 Win Rate", f"{stats.get('win_rate', 0):.1f}%")

    with col4:
        pnl = stats.get('total_pnl', 0)
        st.metric("💎 P&L", f"${pnl:,.2f}", delta=f"{pnl:+,.2f}")

    with col5:
        st.metric("📊 Avg Win", f"${stats.get('avg_win', 0):,.2f}")

    with col6:
        status = "🟢 ACTIVE" if st.session_state.get('agent_running') else "🔴 STOPPED"
        st.metric("🤖 Status", status)


def render_charts_with_markers(symbols: list, timeframe: str, tracker: AIActivityTracker):
    """Render charts with AI markers."""
    selected = st.selectbox("Select Pair", symbols if symbols else ["BTC/USDT"], key="chart_pair")

    df = fetch_live_data(selected, timeframe, 100)
    ticker = fetch_ticker(selected)

    if df is None or df.empty:
        df = generate_sample_ohlcv(100)
        st.warning("⚠️ Using sample data")

    # Get markers for this symbol
    markers = tracker.get_markers_for_symbol(selected)

    # Price metrics
    if ticker:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💲 Price", f"${ticker.get('last', 0):,.2f}", f"{ticker.get('percentage', 0):+.2f}%")
        with col2:
            st.metric("📈 High", f"${ticker.get('high', 0):,.2f}")
        with col3:
            st.metric("📉 Low", f"${ticker.get('low', 0):,.2f}")
        with col4:
            st.metric("📊 Volume", f"${ticker.get('quoteVolume', 0):,.0f}")

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

    # ADD AI MARKERS TO CHART
    if markers:
        for marker in markers:
            symbol_map = {
                "triangle-up": "triangle-up",
                "triangle-down": "triangle-down",
                "star": "star",
                "diamond": "diamond",
                "circle": "circle"
            }
            fig.add_trace(go.Scatter(
                x=[marker.timestamp],
                y=[marker.price],
                mode='markers+text',
                name=marker.label,
                marker=dict(
                    size=marker.size,
                    color=marker.color,
                    symbol=symbol_map.get(marker.symbol, "circle"),
                    line=dict(width=2, color='white')
                ),
                text=[marker.label],
                textposition="top center",
                textfont=dict(size=10, color=marker.color),
                hovertext=marker.details,
                hoverinfo='text'
            ), row=1, col=1)

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
    fig.add_trace(go.Bar(x=df.index, y=hist, name="Hist", marker_color=colors), row=3, col=1)

    fig.update_layout(
        height=700,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(26,26,46,0.8)',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show marker legend
    if markers:
        st.markdown("### 🎯 AI Markers on Chart")
        cols = st.columns(min(len(markers[-5:]), 5))
        for i, marker in enumerate(markers[-5:]):
            with cols[i % 5]:
                st.markdown(f"""
                <div class="marker-info">
                    <span style="color:{marker.color}">●</span> <b>{marker.label}</b><br>
                    <small>{marker.details[:50]}...</small>
                </div>
                """, unsafe_allow_html=True)


def render_ai_activity_panel(tracker: AIActivityTracker):
    """Render AI activity monitoring panel."""
    st.markdown("### 🤖 AI Activity Monitor")

    col1, col2 = st.columns([2, 1])

    with col1:
        # AI Console (live activity log)
        st.markdown("#### 📺 Live Console")

        activities = tracker.get_recent_activities(30)

        console_html = '<div class="ai-console">'
        for activity in activities:
            type_class = f"ai-type-{activity.activity_type.value}"
            emoji = {
                'analyzing': '🔍',
                'signal_generated': '📊',
                'trade_placed': '💰',
                'trade_closed': '✅',
                'pattern_detected': '📈',
                'thinking': '🧠',
                'error': '❌'
            }.get(activity.activity_type.value, '•')

            console_html += f'''
            <div class="ai-line">
                <span class="ai-time">[{activity.timestamp.strftime("%H:%M:%S")}]</span>
                <span class="{type_class}">{emoji} {activity.title}</span>
                <span style="color:#888"> - {activity.description[:60]}...</span>
            </div>
            '''
        console_html += '</div>'

        st.markdown(console_html, unsafe_allow_html=True)

        # Simulate activity button (for demo)
        if st.button("🔄 Simulate AI Activity"):
            import random
            symbol = random.choice(["BTC/USDT", "ETH/USDT"])
            price = 95000 + random.randint(-1000, 1000) if "BTC" in symbol else 3500 + random.randint(-100, 100)

            # Simulate analysis
            tracker.log_analyzing(symbol, {"rsi": random.uniform(30, 70), "macd": random.uniform(-100, 100)})
            tracker.log_thinking(symbol, f"Evaluating market conditions for {symbol}...")

            # Simulate signal
            signal = random.choice(["BUY", "SELL", "HOLD"])
            confidence = random.uniform(0.5, 0.9)
            tracker.log_signal(
                symbol, signal, confidence, price,
                f"RSI indicates {'oversold' if signal == 'BUY' else 'overbought' if signal == 'SELL' else 'neutral'} conditions",
                {"rsi": 35, "macd": 50}
            )

            st.rerun()

    with col2:
        # Current AI State
        st.markdown("#### 🧠 AI Brain State")

        state = tracker.get_current_state()

        status_color = "#00ff88" if state['status'] == 'analyzing' else "#666"
        st.markdown(f"""
        <div class="ai-thinking-box">
            <p style="color:{status_color}; margin:0;">
                <b>Status:</b> {state['status'].upper()}
            </p>
            <p style="color:#aaa; margin:10px 0 0 0; font-size:0.9rem;">
                {state['thinking'] or 'Waiting for market data...'}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Last Signal
        if state.get('last_signal'):
            sig = state['last_signal']
            sig_color = "#00ff88" if sig['signal'] == 'BUY' else "#ff4444" if sig['signal'] == 'SELL' else "#ffff00"
            st.markdown(f"""
            <div style="margin-top:20px; padding:15px; background:linear-gradient(135deg,#1a1a2e,#16213e); border-radius:10px;">
                <p style="color:#888; margin:0;">Last Signal:</p>
                <h2 style="color:{sig_color}; margin:5px 0;">{sig['signal']}</h2>
                <p style="color:#aaa; margin:0;">{sig['symbol']} | {sig['confidence']:.0%}</p>
            </div>
            """, unsafe_allow_html=True)

        # Important Activities
        st.markdown("#### ⚠️ Important Events")
        important = tracker.get_important_activities(5)
        for act in important:
            st.markdown(f"""
            <div class="activity-card activity-important">
                <b>{act.title}</b><br>
                <small style="color:#888">{act.timestamp.strftime("%H:%M")} | {act.symbol}</small>
            </div>
            """, unsafe_allow_html=True)


def render_ai_analysis(symbols: list, db: TradingDatabase, tracker: AIActivityTracker):
    """Render AI analysis section."""
    selected = symbols[0] if symbols else "BTC/USDT"
    df = fetch_live_data(selected, "1h", 50)
    ticker = fetch_ticker(selected)

    if df is None or df.empty:
        df = generate_sample_ohlcv(50)

    # Calculate signals
    rsi = calculate_rsi(df["close"]).iloc[-1]
    macd, signal_line, _ = calculate_macd(df["close"])
    ema9 = df["close"].ewm(span=9).mean().iloc[-1]
    ema21 = df["close"].ewm(span=21).mean().iloc[-1]
    current_price = df["close"].iloc[-1]

    # Determine signal
    bullish = 0
    bearish = 0
    reasons = []

    if rsi < 30:
        bullish += 1
        reasons.append(f"RSI oversold ({rsi:.1f})")
    elif rsi > 70:
        bearish += 1
        reasons.append(f"RSI overbought ({rsi:.1f})")

    if macd.iloc[-1] > signal_line.iloc[-1]:
        bullish += 1
        reasons.append("MACD bullish")
    else:
        bearish += 1
        reasons.append("MACD bearish")

    if ema9 > ema21:
        bullish += 1
        reasons.append("EMA golden cross")
    else:
        bearish += 1
        reasons.append("EMA death cross")

    if bullish > bearish:
        signal = "BUY"
        confidence = bullish / (bullish + bearish)
        signal_class = "signal-buy"
    elif bearish > bullish:
        signal = "SELL"
        confidence = bearish / (bullish + bearish)
        signal_class = "signal-sell"
    else:
        signal = "HOLD"
        confidence = 0.5
        signal_class = "signal-hold"

    col1, col2 = st.columns(2)

    with col1:
        price_str = f"${ticker.get('last', current_price):,.2f}" if ticker else f"${current_price:,.2f}"
        sig_color = "#00ff88" if signal == "BUY" else "#ff4444" if signal == "SELL" else "#ffff00"

        st.markdown(f"""
        <div class="{signal_class}">
            <h1 style="color:{sig_color}; font-size:3rem; margin:0; font-family:'Orbitron';">
                {'📈' if signal == 'BUY' else '📉' if signal == 'SELL' else '⏸️'} {signal}
            </h1>
            <p style="color:white; font-size:1.5rem; margin:10px 0;">Confidence: <b>{confidence:.0%}</b></p>
            <p style="color:#aaa;">{selected} @ {price_str}</p>
        </div>
        """, unsafe_allow_html=True)

        # Reasons
        st.markdown("### 📋 Signal Reasoning")
        for reason in reasons:
            st.markdown(f"• {reason}")

        # Add signal to tracker button
        if st.button("📊 Log This Signal"):
            tracker.log_signal(selected, signal, confidence, current_price,
                             " | ".join(reasons), {"rsi": rsi, "macd": macd.iloc[-1]})
            st.success("Signal logged and marker added to chart!")
            st.rerun()

    with col2:
        # AI Learning Context
        st.markdown("### 🧠 Learning Context")
        context = db.get_context_for_ai(selected)
        st.markdown(f"""
        <div class="ai-thinking-box">
            <pre style="color:#00ff88; font-family:monospace; white-space:pre-wrap; font-size:0.8rem;">{context}</pre>
        </div>
        """, unsafe_allow_html=True)

        # LLM Analysis (if available)
        if ANTHROPIC_API_KEY or OPENAI_API_KEY:
            st.markdown("### 🤖 LLM Deep Analysis")

            llm = get_llm_analyzer()

            if st.button("🧠 Get AI Analysis", type="primary"):
                if llm:
                    with st.spinner("🧠 AI is analyzing the market..."):
                        tracker.log_thinking(selected, "Performing deep LLM analysis...")

                        try:
                            # Prepare data for LLM
                            technical_data = {
                                "symbol": selected,
                                "price": current_price,
                                "rsi": float(rsi),
                                "macd": float(macd.iloc[-1]),
                                "macd_signal": float(signal_line.iloc[-1]),
                                "ema_9": float(ema9),
                                "ema_21": float(ema21),
                                "trend": "bullish" if ema9 > ema21 else "bearish",
                                "price_change_24h": ticker.get('percentage', 0) if ticker else 0
                            }

                            signal_data = {
                                "signal": signal,
                                "confidence": confidence,
                                "reasons": reasons
                            }

                            # Call LLM
                            analysis = run_async(llm.analyze_market(
                                symbol=selected,
                                technical_data=technical_data,
                                patterns=[],
                                signal=signal_data,
                                additional_context=context
                            ))

                            # Store analysis in session
                            st.session_state.last_llm_analysis = analysis

                            # Log the analysis
                            tracker.log_activity(
                                ActivityType.THINKING,
                                selected,
                                f"LLM Analysis: {analysis.sentiment.upper()}",
                                analysis.summary,
                                confidence=analysis.confidence
                            )

                            st.rerun()

                        except Exception as e:
                            st.error(f"LLM analysis failed: {str(e)}")
                            tracker.log_error(selected, f"LLM error: {str(e)}")
                else:
                    st.warning("LLM not available. Check API keys in .env file.")

            # Display last analysis if exists
            if 'last_llm_analysis' in st.session_state:
                analysis = st.session_state.last_llm_analysis

                sent_color = "#00ff88" if analysis.sentiment == "bullish" else "#ff4444" if analysis.sentiment == "bearish" else "#ffff00"
                action_color = "#00ff88" if analysis.recommended_action == "buy" else "#ff4444" if analysis.recommended_action == "sell" else "#ffff00"

                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#0d1f0d,#1a2d2a); border:1px solid {sent_color};
                            border-radius:10px; padding:15px; margin-top:10px;">
                    <h4 style="color:{sent_color}; margin:0;">
                        {'📈' if analysis.sentiment == 'bullish' else '📉' if analysis.sentiment == 'bearish' else '➡️'}
                        {analysis.sentiment.upper()} ({analysis.confidence:.0%})
                    </h4>
                    <p style="color:#ddd; margin:10px 0;">{analysis.summary}</p>
                    <p style="color:{action_color}; font-weight:bold;">
                        Recommendation: {analysis.recommended_action.upper()}
                    </p>
                </div>
                """, unsafe_allow_html=True)

                # Show details in expander
                with st.expander("📊 Full Analysis Details"):
                    st.markdown("**Key Factors:**")
                    for factor in analysis.key_factors:
                        st.markdown(f"• {factor}")

                    st.markdown("**Risks:**")
                    for risk in analysis.risks:
                        st.markdown(f"⚠️ {risk}")

                    st.markdown("**Opportunities:**")
                    for opp in analysis.opportunities:
                        st.markdown(f"✨ {opp}")

                    st.markdown("**Reasoning:**")
                    st.markdown(f"_{analysis.reasoning}_")
        else:
            st.info("💡 Add ANTHROPIC_API_KEY or OPENAI_API_KEY to .env for AI-powered analysis")


def render_news_section():
    """Render news section."""
    st.markdown("### 📰 Market News")

    try:
        aggregator = NewsAggregator()
        articles = run_async(aggregator.fetch_all_news(limit=10))

        if articles:
            for article in articles[:5]:
                color = "#00ff88" if article.sentiment == "positive" else "#ff4444" if article.sentiment == "negative" else "#888"
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#1e1e2f,#2d2d44); border-left:4px solid {color};
                            padding:15px; margin:10px 0; border-radius:0 10px 10px 0;">
                    <b style="color:white;">{article.title}</b><br>
                    <small style="color:#888;">📰 {article.source} | {article.published_at[:10] if article.published_at else ''}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No news available")
    except:
        st.info("News loading...")


def render_trade_history(db: TradingDatabase):
    """Render trade history."""
    st.markdown("### 📜 Trade History")

    trades = db.get_recent_trades(20)
    if not trades:
        st.info("No trade history yet")
        return

    data = [{
        "Time": t.entry_time[:19] if t.entry_time else "N/A",
        "Symbol": t.symbol,
        "Side": "🟢 BUY" if t.side == "BUY" else "🔴 SELL",
        "Entry": f"${t.entry_price:,.2f}",
        "Exit": f"${t.exit_price:,.2f}" if t.exit_price else "Open",
        "P&L": f"${t.pnl:+,.2f}" if t.status == "closed" else "-"
    } for t in trades]

    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


def render_learning_section(db: TradingDatabase):
    """Render learning section."""
    st.markdown("### 🎓 AI Learning")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Performance by Symbol")
        perf = []
        for sym in ["BTC/USDT", "ETH/USDT", "SOL/USDT"]:
            p = db.get_symbol_performance(sym)
            perf.append({"Symbol": sym, "Trades": p['total_trades'], "Win Rate": f"{p['win_rate']:.1f}%"})
        st.dataframe(pd.DataFrame(perf), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### AI Insights")
        insights = db.get_insights(5)
        if insights:
            for i in insights:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#1a1a2e,#16213e); padding:10px;
                            border-radius:10px; margin:5px 0; border-left:4px solid #00ff88;">
                    💡 {i.description}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No insights yet")


# Helper functions
def generate_sample_ohlcv(n: int) -> pd.DataFrame:
    import numpy as np
    np.random.seed(int(datetime.now().timestamp()) % 100)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="1h")
    price = 95000
    data = []
    for _ in range(n):
        c = price + np.random.randn() * 500
        data.append({"open": price, "high": max(price, c) + 200, "low": min(price, c) - 200, "close": c, "volume": np.random.randint(1e8, 5e8)})
        price = c
    return pd.DataFrame(data, index=dates)


def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    return 100 - (100 / (1 + gain / loss))


def calculate_macd(prices):
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd, signal, macd - signal


if __name__ == "__main__":
    run_dashboard()
