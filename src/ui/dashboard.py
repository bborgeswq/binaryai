"""
AI Day Trader Dashboard - Professional Edition
Clean, minimalist trading interface
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

# Color Palette - Professional & Minimal
COLORS = {
    'bg_primary': '#0f1419',
    'bg_secondary': '#1a1f26',
    'bg_card': '#1e252e',
    'border': '#2d3640',
    'text_primary': '#e7e9ea',
    'text_secondary': '#8b98a5',
    'text_muted': '#5c6b7a',
    'accent': '#3b82f6',
    'success': '#22c55e',
    'danger': '#ef4444',
    'warning': '#f59e0b',
    'neutral': '#6b7280',
}


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
            except Exception:
                st.session_state.llm_analyzer = None
        elif LLM_AVAILABLE and OPENAI_API_KEY:
            try:
                st.session_state.llm_analyzer = LLMAnalyzer(
                    api_key=OPENAI_API_KEY,
                    provider="openai"
                )
            except Exception:
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
    except Exception:
        pass
    return None


def fetch_ticker(symbol: str):
    """Fetch ticker data."""
    broker = get_broker()
    if not broker:
        return None
    try:
        return run_async(broker.get_ticker(symbol))
    except Exception:
        return None


def run_dashboard():
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="AI Trader",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Professional CSS
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    * {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .main-header {{
        font-size: 1.5rem;
        font-weight: 600;
        color: {COLORS['text_primary']};
        padding: 0;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}

    .status-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
    }}
    .status-connected {{
        background: rgba(34, 197, 94, 0.1);
        color: {COLORS['success']};
        border: 1px solid rgba(34, 197, 94, 0.2);
    }}
    .status-disconnected {{
        background: rgba(239, 68, 68, 0.1);
        color: {COLORS['danger']};
        border: 1px solid rgba(239, 68, 68, 0.2);
    }}

    .card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }}

    .signal-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 24px;
        text-align: center;
    }}
    .signal-buy {{
        border-left: 4px solid {COLORS['success']};
    }}
    .signal-sell {{
        border-left: 4px solid {COLORS['danger']};
    }}
    .signal-hold {{
        border-left: 4px solid {COLORS['warning']};
    }}

    .signal-label {{
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }}
    .signal-buy .signal-label {{ color: {COLORS['success']}; }}
    .signal-sell .signal-label {{ color: {COLORS['danger']}; }}
    .signal-hold .signal-label {{ color: {COLORS['warning']}; }}

    .metric-card {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 12px 16px;
    }}
    .metric-label {{
        font-size: 0.75rem;
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }}
    .metric-value {{
        font-size: 1.25rem;
        font-weight: 600;
        color: {COLORS['text_primary']};
    }}
    .metric-delta-positive {{ color: {COLORS['success']}; font-size: 0.85rem; }}
    .metric-delta-negative {{ color: {COLORS['danger']}; font-size: 0.85rem; }}

    .console {{
        background: {COLORS['bg_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        max-height: 350px;
        overflow-y: auto;
    }}
    .console-line {{
        padding: 4px 0;
        border-bottom: 1px solid {COLORS['border']};
    }}
    .console-time {{
        color: {COLORS['text_muted']};
        margin-right: 8px;
    }}
    .console-type-analyzing {{ color: {COLORS['accent']}; }}
    .console-type-signal {{ color: {COLORS['success']}; }}
    .console-type-trade {{ color: {COLORS['warning']}; }}
    .console-type-error {{ color: {COLORS['danger']}; }}
    .console-type-thinking {{ color: #a78bfa; }}

    .news-item {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
    }}
    .news-positive {{ border-left: 3px solid {COLORS['success']}; }}
    .news-negative {{ border-left: 3px solid {COLORS['danger']}; }}
    .news-neutral {{ border-left: 3px solid {COLORS['neutral']}; }}

    .section-header {{
        font-size: 1rem;
        font-weight: 600;
        color: {COLORS['text_primary']};
        margin: 16px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid {COLORS['border']};
    }}

    .sidebar-section {{
        margin-bottom: 24px;
    }}
    .sidebar-title {{
        font-size: 0.7rem;
        font-weight: 600;
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 12px;
    }}

    .insight-card {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-left: 3px solid {COLORS['accent']};
        border-radius: 6px;
        padding: 10px 12px;
        margin: 6px 0;
        font-size: 0.85rem;
        color: {COLORS['text_secondary']};
    }}

    .stMetric > div {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 12px;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px 16px;
        color: {COLORS['text_secondary']};
    }}
    .stTabs [aria-selected="true"] {{
        background: {COLORS['accent']};
        border-color: {COLORS['accent']};
        color: white;
    }}

    .stButton > button {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        color: {COLORS['text_primary']};
        font-weight: 500;
        border-radius: 6px;
        transition: all 0.2s;
    }}
    .stButton > button:hover {{
        background: {COLORS['bg_card']};
        border-color: {COLORS['accent']};
    }}
    .stButton > button[kind="primary"] {{
        background: {COLORS['accent']};
        border-color: {COLORS['accent']};
    }}

    div[data-testid="stExpander"] {{
        background: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
    }}
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.markdown('<div class="main-header">AI Trader</div>', unsafe_allow_html=True)

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

    # Connection Status
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">Connection</div>', unsafe_allow_html=True)

    if st.session_state.get('broker_connected'):
        status_class = "status-connected"
        status_text = "Connected" + (" (Testnet)" if BINANCE_TESTNET else "")
        st.markdown(f'<div class="status-badge {status_class}">● {status_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-badge status-disconnected">● Disconnected</div>', unsafe_allow_html=True)
        if st.button("Reconnect", key="reconnect"):
            if 'broker' in st.session_state:
                del st.session_state['broker']
            get_broker()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # AI Status
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">AI Engine</div>', unsafe_allow_html=True)
    if ANTHROPIC_API_KEY:
        st.markdown('<div class="status-badge status-connected">● Claude Active</div>', unsafe_allow_html=True)
    elif OPENAI_API_KEY:
        st.markdown('<div class="status-badge status-connected">● GPT Active</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-badge" style="background:rgba(245,158,11,0.1);color:{COLORS["warning"]};border:1px solid rgba(245,158,11,0.2);">○ Indicators Only</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # Agent Controls
    st.markdown('<div class="sidebar-title">Agent Control</div>', unsafe_allow_html=True)
    agent_running = st.session_state.get('agent_running', False)

    col1, col2 = st.columns(2)
    with col1:
        start_label = "Running" if agent_running else "Start"
        if st.button(start_label, use_container_width=True, type="primary" if not agent_running else "secondary", key="start"):
            st.session_state.agent_running = True
            tracker.log_activity(ActivityType.THINKING, "SYSTEM", "Agent Started", "Trading agent activated")
            st.rerun()
    with col2:
        if st.button("Stop", use_container_width=True, key="stop"):
            st.session_state.agent_running = False
            tracker.log_activity(ActivityType.THINKING, "SYSTEM", "Agent Stopped", "Trading agent deactivated")
            st.rerun()

    st.divider()

    # Settings
    st.markdown('<div class="sidebar-title">Settings</div>', unsafe_allow_html=True)
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

    # Risk Settings
    st.markdown('<div class="sidebar-title">Risk Management</div>', unsafe_allow_html=True)
    st.slider("Risk per Trade (%)", 1.0, 5.0, 2.0, 0.5, key="risk")
    st.slider("Max Positions", 1, 10, 3, key="max_pos")


def render_main_content(db: TradingDatabase, tracker: AIActivityTracker):
    """Render main content area."""
    symbols = st.session_state.get('selected_symbols', ["BTC/USDT"])
    timeframe = st.session_state.get('selected_timeframe', "1h")

    # Top metrics
    render_top_metrics(db)

    # Main tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Charts", "AI Activity", "Analysis", "News", "History", "Learning"
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
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        if st.button("Refresh", use_container_width=True, key="refresh"):
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
                equity = float(account.equity)
                st.metric("Portfolio", f"${equity:,.2f}")
            except Exception:
                st.metric("Portfolio", "---")
        else:
            st.metric("Portfolio", "---")

    with col2:
        st.metric("Total Trades", stats.get('total_trades', 0))

    with col3:
        win_rate = stats.get('win_rate', 0)
        st.metric("Win Rate", f"{win_rate:.1f}%")

    with col4:
        pnl = stats.get('total_pnl', 0)
        delta_str = f"{pnl:+,.2f}" if pnl != 0 else None
        st.metric("Total P&L", f"${pnl:,.2f}", delta=delta_str)

    with col5:
        st.metric("Avg Win", f"${stats.get('avg_win', 0):,.2f}")

    with col6:
        status = "Active" if st.session_state.get('agent_running') else "Stopped"
        st.metric("Agent", status)


def render_charts_with_markers(symbols: list, timeframe: str, tracker: AIActivityTracker):
    """Render charts with AI markers."""
    selected = st.selectbox("Select Pair", symbols if symbols else ["BTC/USDT"], key="chart_pair")

    df = fetch_live_data(selected, timeframe, 100)
    ticker = fetch_ticker(selected)

    if df is None or df.empty:
        df = generate_sample_ohlcv(100)
        st.info("Using sample data - check connection")

    # Get markers for this symbol
    markers = tracker.get_markers_for_symbol(selected)

    # Price metrics row
    if ticker:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            change = ticker.get('percentage', 0)
            st.metric("Price", f"${ticker.get('last', 0):,.2f}", f"{change:+.2f}%")
        with col2:
            st.metric("24h High", f"${ticker.get('high', 0):,.2f}")
        with col3:
            st.metric("24h Low", f"${ticker.get('low', 0):,.2f}")
        with col4:
            vol = ticker.get('quoteVolume', 0)
            st.metric("Volume", f"${vol:,.0f}")

    # Create chart
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("", "RSI", "MACD")
    )

    # Candlesticks - Using professional colors
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="Price",
        increasing_line_color=COLORS['success'],
        decreasing_line_color=COLORS['danger'],
        increasing_fillcolor=COLORS['success'],
        decreasing_fillcolor=COLORS['danger']
    ), row=1, col=1)

    # EMAs
    ema9 = df["close"].ewm(span=9).mean()
    ema21 = df["close"].ewm(span=21).mean()
    fig.add_trace(go.Scatter(x=df.index, y=ema9, name="EMA 9",
                             line=dict(color=COLORS['accent'], width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=ema21, name="EMA 21",
                             line=dict(color=COLORS['warning'], width=1)), row=1, col=1)

    # Bollinger Bands
    sma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    fig.add_trace(go.Scatter(x=df.index, y=sma20 + 2*std20, name="BB Upper",
                             line=dict(color=COLORS['text_muted'], dash="dash", width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=sma20 - 2*std20, name="BB Lower",
                             line=dict(color=COLORS['text_muted'], dash="dash", width=1),
                             fill='tonexty', fillcolor='rgba(107,114,128,0.1)'), row=1, col=1)

    # AI Markers
    if markers:
        for marker in markers:
            # Use more professional marker colors
            marker_color = COLORS['success'] if 'BUY' in marker.label else COLORS['danger'] if 'SELL' in marker.label else COLORS['accent']
            fig.add_trace(go.Scatter(
                x=[marker.timestamp],
                y=[marker.price],
                mode='markers',
                name=marker.label,
                marker=dict(
                    size=10,
                    color=marker_color,
                    symbol="circle",
                    line=dict(width=1, color='white')
                ),
                hovertext=f"{marker.label}: {marker.details}",
                hoverinfo='text'
            ), row=1, col=1)

    # RSI
    rsi = calculate_rsi(df["close"])
    fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI",
                             line=dict(color="#a78bfa", width=1)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS['danger'], line_width=1, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS['success'], line_width=1, row=2, col=1)

    # MACD
    macd, signal, hist = calculate_macd(df["close"])
    fig.add_trace(go.Scatter(x=df.index, y=macd, name="MACD",
                             line=dict(color=COLORS['accent'], width=1)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=signal, name="Signal",
                             line=dict(color=COLORS['warning'], width=1)), row=3, col=1)
    colors = [COLORS['success'] if h >= 0 else COLORS['danger'] for h in hist.fillna(0)]
    fig.add_trace(go.Bar(x=df.index, y=hist, name="Histogram", marker_color=colors, opacity=0.6), row=3, col=1)

    fig.update_layout(
        height=600,
        template="plotly_dark",
        paper_bgcolor=COLORS['bg_primary'],
        plot_bgcolor=COLORS['bg_secondary'],
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
        xaxis_rangeslider_visible=False,
        margin=dict(l=0, r=0, t=30, b=0),
        font=dict(family="Inter", color=COLORS['text_secondary'])
    )

    fig.update_xaxes(gridcolor=COLORS['border'], zerolinecolor=COLORS['border'])
    fig.update_yaxes(gridcolor=COLORS['border'], zerolinecolor=COLORS['border'])

    st.plotly_chart(fig, use_container_width=True)

    # Marker legend
    if markers:
        st.markdown('<div class="section-header">Recent Signals</div>', unsafe_allow_html=True)
        cols = st.columns(min(len(markers[-4:]), 4))
        for i, marker in enumerate(markers[-4:]):
            with cols[i]:
                st.caption(f"{marker.label} @ ${marker.price:,.2f}")


def render_ai_activity_panel(tracker: AIActivityTracker):
    """Render AI activity monitoring panel."""
    st.markdown('<div class="section-header">Activity Monitor</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Console**")
        activities = tracker.get_recent_activities(20)

        console_html = '<div class="console">'
        if not activities:
            console_html += f'<div style="color:{COLORS["text_muted"]}">No activity yet. Start the agent or simulate activity.</div>'
        else:
            for activity in activities:
                type_class = f"console-type-{activity.activity_type.value}"
                console_html += f'''
                <div class="console-line">
                    <span class="console-time">{activity.timestamp.strftime("%H:%M:%S")}</span>
                    <span class="{type_class}">[{activity.activity_type.value.upper()}]</span>
                    <span style="color:{COLORS['text_secondary']}">{activity.title}</span>
                </div>
                '''
        console_html += '</div>'
        st.markdown(console_html, unsafe_allow_html=True)

        if st.button("Simulate Activity", key="simulate"):
            import random
            symbol = random.choice(["BTC/USDT", "ETH/USDT"])
            price = 95000 + random.randint(-1000, 1000) if "BTC" in symbol else 3500 + random.randint(-100, 100)

            tracker.log_analyzing(symbol, {"rsi": random.uniform(30, 70)})
            tracker.log_thinking(symbol, f"Analyzing {symbol} market conditions")

            signal = random.choice(["BUY", "SELL", "HOLD"])
            tracker.log_signal(symbol, signal, random.uniform(0.6, 0.9), price,
                             "Technical indicators analysis", {"rsi": random.uniform(30, 70)})
            st.rerun()

    with col2:
        st.markdown("**Agent State**")
        state = tracker.get_current_state()

        status = state['status'].upper()
        status_color = COLORS['success'] if state['status'] == 'analyzing' else COLORS['text_muted']

        st.markdown(f"""
        <div class="card">
            <div class="metric-label">Status</div>
            <div style="color:{status_color}; font-weight:600;">{status}</div>
            <div style="color:{COLORS['text_muted']}; font-size:0.85rem; margin-top:8px;">
                {state['thinking'] or 'Idle'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if state.get('last_signal'):
            sig = state['last_signal']
            sig_color = COLORS['success'] if sig['signal'] == 'BUY' else COLORS['danger'] if sig['signal'] == 'SELL' else COLORS['warning']
            st.markdown(f"""
            <div class="card" style="margin-top:12px;">
                <div class="metric-label">Last Signal</div>
                <div style="color:{sig_color}; font-size:1.5rem; font-weight:700;">{sig['signal']}</div>
                <div style="color:{COLORS['text_muted']}; font-size:0.85rem;">
                    {sig['symbol']} · {sig['confidence']:.0%} confidence
                </div>
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
    else:
        reasons.append(f"RSI neutral ({rsi:.1f})")

    if macd.iloc[-1] > signal_line.iloc[-1]:
        bullish += 1
        reasons.append("MACD bullish crossover")
    else:
        bearish += 1
        reasons.append("MACD bearish crossover")

    if ema9 > ema21:
        bullish += 1
        reasons.append("EMA trend: bullish")
    else:
        bearish += 1
        reasons.append("EMA trend: bearish")

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
        st.markdown('<div class="section-header">Signal</div>', unsafe_allow_html=True)
        price_str = f"${ticker.get('last', current_price):,.2f}" if ticker else f"${current_price:,.2f}"

        st.markdown(f"""
        <div class="signal-card {signal_class}">
            <div class="signal-label">{signal}</div>
            <div style="color:{COLORS['text_secondary']}; margin-top:8px;">
                Confidence: {confidence:.0%}
            </div>
            <div style="color:{COLORS['text_muted']}; font-size:0.85rem; margin-top:4px;">
                {selected} @ {price_str}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Reasoning</div>', unsafe_allow_html=True)
        for reason in reasons:
            st.markdown(f"- {reason}")

        if st.button("Log Signal", key="log_signal"):
            tracker.log_signal(selected, signal, confidence, current_price,
                             " | ".join(reasons), {"rsi": rsi, "macd": macd.iloc[-1]})
            st.success("Signal logged")
            st.rerun()

    with col2:
        st.markdown('<div class="section-header">Learning Context</div>', unsafe_allow_html=True)
        context = db.get_context_for_ai(selected)
        st.code(context, language=None)

        # LLM Analysis
        if ANTHROPIC_API_KEY or OPENAI_API_KEY:
            st.markdown('<div class="section-header">AI Analysis</div>', unsafe_allow_html=True)

            llm = get_llm_analyzer()

            if st.button("Get AI Analysis", type="primary", key="llm_analyze"):
                if llm:
                    with st.spinner("Analyzing..."):
                        tracker.log_thinking(selected, "Running LLM analysis...")
                        try:
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
                            signal_data = {"signal": signal, "confidence": confidence, "reasons": reasons}

                            analysis = run_async(llm.analyze_market(
                                symbol=selected,
                                technical_data=technical_data,
                                patterns=[],
                                signal=signal_data,
                                additional_context=context
                            ))

                            st.session_state.last_llm_analysis = analysis
                            tracker.log_activity(ActivityType.THINKING, selected,
                                                f"Analysis: {analysis.sentiment.upper()}", analysis.summary,
                                                confidence=analysis.confidence)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Analysis failed: {str(e)}")
                else:
                    st.warning("LLM not available")

            if 'last_llm_analysis' in st.session_state:
                analysis = st.session_state.last_llm_analysis
                sent_color = COLORS['success'] if analysis.sentiment == "bullish" else COLORS['danger'] if analysis.sentiment == "bearish" else COLORS['warning']

                st.markdown(f"""
                <div class="card" style="border-left:3px solid {sent_color};">
                    <div style="color:{sent_color}; font-weight:600; font-size:1.1rem;">
                        {analysis.sentiment.upper()} ({analysis.confidence:.0%})
                    </div>
                    <div style="color:{COLORS['text_secondary']}; margin-top:8px;">
                        {analysis.summary}
                    </div>
                    <div style="color:{COLORS['text_primary']}; font-weight:500; margin-top:12px;">
                        Recommendation: {analysis.recommended_action.upper()}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("Full Analysis"):
                    st.write("**Key Factors:**")
                    for factor in analysis.key_factors:
                        st.write(f"- {factor}")
                    st.write("**Risks:**")
                    for risk in analysis.risks:
                        st.write(f"- {risk}")
                    st.write("**Opportunities:**")
                    for opp in analysis.opportunities:
                        st.write(f"- {opp}")
                    st.write("**Reasoning:**")
                    st.write(analysis.reasoning)
        else:
            st.info("Add API keys to .env for AI analysis")


def render_news_section():
    """Render news section."""
    st.markdown('<div class="section-header">Market News</div>', unsafe_allow_html=True)

    try:
        aggregator = NewsAggregator()
        articles = run_async(aggregator.fetch_all_news(limit=10))

        if articles:
            for article in articles[:5]:
                sentiment_class = "news-positive" if article.sentiment == "positive" else "news-negative" if article.sentiment == "negative" else "news-neutral"
                st.markdown(f"""
                <div class="news-item {sentiment_class}">
                    <div style="color:{COLORS['text_primary']}; font-weight:500;">{article.title}</div>
                    <div style="color:{COLORS['text_muted']}; font-size:0.8rem; margin-top:4px;">
                        {article.source} · {article.published_at[:10] if article.published_at else ''}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No news available")
    except Exception:
        st.info("Loading news...")


def render_trade_history(db: TradingDatabase):
    """Render trade history."""
    st.markdown('<div class="section-header">Trade History</div>', unsafe_allow_html=True)

    trades = db.get_recent_trades(20)
    if not trades:
        st.info("No trade history yet")
        return

    data = []
    for t in trades:
        pnl_str = f"${t.pnl:+,.2f}" if t.status == "closed" and t.pnl else "-"
        data.append({
            "Time": t.entry_time[:16] if t.entry_time else "N/A",
            "Symbol": t.symbol,
            "Side": t.side,
            "Entry": f"${t.entry_price:,.2f}",
            "Exit": f"${t.exit_price:,.2f}" if t.exit_price else "-",
            "P&L": pnl_str,
            "Status": t.status.capitalize()
        })

    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


def render_learning_section(db: TradingDatabase):
    """Render learning section."""
    st.markdown('<div class="section-header">Performance Analytics</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Performance by Symbol**")
        perf = []
        for sym in ["BTC/USDT", "ETH/USDT", "SOL/USDT"]:
            p = db.get_symbol_performance(sym)
            perf.append({
                "Symbol": sym,
                "Trades": p['total_trades'],
                "Win Rate": f"{p['win_rate']:.1f}%",
                "P&L": f"${p.get('total_pnl', 0):,.2f}"
            })
        st.dataframe(pd.DataFrame(perf), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**AI Insights**")
        insights = db.get_insights(5)
        if insights:
            for i in insights:
                st.markdown(f"""
                <div class="insight-card">{i.description}</div>
                """, unsafe_allow_html=True)
        else:
            st.info("No insights yet. Trade more to generate insights.")


# Helper functions
def generate_sample_ohlcv(n: int) -> pd.DataFrame:
    import numpy as np
    np.random.seed(int(datetime.now().timestamp()) % 100)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="1h")
    price = 95000
    data = []
    for _ in range(n):
        c = price + np.random.randn() * 500
        data.append({
            "open": price,
            "high": max(price, c) + 200,
            "low": min(price, c) - 200,
            "close": c,
            "volume": np.random.randint(1e8, 5e8)
        })
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
