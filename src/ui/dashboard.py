"""
Real-Time Trading Dashboard
Streamlit-based dashboard for monitoring AI trading activity
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json


def run_dashboard():
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="AI Day Trader",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS
    st.markdown("""
    <style>
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .metric-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .profit {
        color: #00FF00;
    }
    .loss {
        color: #FF4444;
    }
    .stButton>button {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

    # Header
    st.title("🤖 AI Day Trader Dashboard")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Agent Controls
        st.subheader("Agent Controls")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start", use_container_width=True):
                st.session_state.agent_running = True
        with col2:
            if st.button("⏹️ Stop", use_container_width=True):
                st.session_state.agent_running = False

        if st.button("⏸️ Pause/Resume", use_container_width=True):
            st.session_state.agent_paused = not st.session_state.get("agent_paused", False)

        st.divider()

        # Trading Settings
        st.subheader("Trading Settings")
        mode = st.selectbox("Mode", ["Paper Trading", "Live Trading"])
        if mode == "Live Trading":
            st.warning("⚠️ Live trading uses REAL money!")

        symbols = st.multiselect(
            "Symbols",
            ["BTC/USD", "ETH/USD", "SOL/USD", "AAPL", "TSLA", "NVDA"],
            default=["BTC/USD", "ETH/USD"]
        )

        timeframe = st.selectbox(
            "Timeframe",
            ["1m", "5m", "15m", "1h", "4h", "1d"],
            index=3
        )

        st.divider()

        # Risk Settings
        st.subheader("Risk Settings")
        max_risk = st.slider("Max Risk per Trade (%)", 1.0, 5.0, 2.0, 0.5)
        max_positions = st.slider("Max Positions", 1, 10, 3)
        max_daily_loss = st.slider("Max Daily Loss (%)", 1.0, 10.0, 5.0, 0.5)

        st.divider()

        # API Status
        st.subheader("Connection Status")
        st.success("🟢 Broker Connected")
        st.success("🟢 Data Feed Active")
        st.info("🔵 LLM API Ready")

    # Main Content
    # Top Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Portfolio Value", "$10,250.00", "+$250.00")

    with col2:
        st.metric("Today's P&L", "+$125.50", "+1.24%")

    with col3:
        st.metric("Open Positions", "2")

    with col4:
        st.metric("Win Rate", "68%", "+3%")

    with col5:
        agent_status = "🟢 Running" if st.session_state.get("agent_running", False) else "🔴 Stopped"
        st.metric("Agent Status", agent_status)

    st.divider()

    # Main Trading View
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Live Charts",
        "📈 AI Analysis",
        "💼 Positions",
        "📋 Trade History",
        "🧠 AI Reasoning"
    ])

    with tab1:
        render_live_charts()

    with tab2:
        render_ai_analysis()

    with tab3:
        render_positions()

    with tab4:
        render_trade_history()

    with tab5:
        render_ai_reasoning()

    # Footer with auto-refresh
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()


def render_live_charts():
    """Render live trading charts with indicators."""
    st.subheader("Live Market View")

    # Symbol selector for chart
    selected_symbol = st.selectbox(
        "Select Symbol",
        ["BTC/USD", "ETH/USD"],
        key="chart_symbol"
    )

    # Generate sample data (in production, this comes from data provider)
    df = generate_sample_ohlcv(100)

    # Create candlestick chart with indicators
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("Price Action", "RSI", "MACD")
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price"
        ),
        row=1, col=1
    )

    # Moving averages
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["close"].rolling(20).mean(),
            name="SMA 20",
            line=dict(color="orange", width=1)
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["close"].rolling(50).mean(),
            name="SMA 50",
            line=dict(color="blue", width=1)
        ),
        row=1, col=1
    )

    # Bollinger Bands
    sma = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=sma + 2 * std,
            name="BB Upper",
            line=dict(color="gray", width=1, dash="dash")
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=sma - 2 * std,
            name="BB Lower",
            line=dict(color="gray", width=1, dash="dash"),
            fill="tonexty",
            fillcolor="rgba(128,128,128,0.1)"
        ),
        row=1, col=1
    )

    # RSI
    rsi = calculate_rsi(df["close"])
    fig.add_trace(
        go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color="purple")),
        row=2, col=1
    )
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # MACD
    macd, signal, hist = calculate_macd(df["close"])
    fig.add_trace(
        go.Scatter(x=df.index, y=macd, name="MACD", line=dict(color="blue")),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=signal, name="Signal", line=dict(color="orange")),
        row=3, col=1
    )
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=hist,
            name="Histogram",
            marker_color=["green" if h >= 0 else "red" for h in hist]
        ),
        row=3, col=1
    )

    # Update layout
    fig.update_layout(
        height=700,
        template="plotly_dark",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Quick stats below chart
    col1, col2, col3, col4 = st.columns(4)
    current_price = df["close"].iloc[-1]
    price_change = df["close"].iloc[-1] - df["close"].iloc[-2]
    change_pct = price_change / df["close"].iloc[-2] * 100

    with col1:
        st.metric("Current Price", f"${current_price:,.2f}", f"{price_change:+.2f} ({change_pct:+.2f}%)")
    with col2:
        st.metric("24h High", f"${df['high'].max():,.2f}")
    with col3:
        st.metric("24h Low", f"${df['low'].min():,.2f}")
    with col4:
        st.metric("Volume", f"${df['volume'].sum():,.0f}")


def render_ai_analysis():
    """Render AI analysis and signals."""
    st.subheader("🤖 AI Market Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Current Signal")
        signal_box = st.container()
        with signal_box:
            # Sample signal data
            st.markdown("""
            <div style='background: linear-gradient(135deg, #1a472a 0%, #2d5a3d 100%);
                        padding: 20px; border-radius: 10px; text-align: center;'>
                <h2 style='color: #00ff00; margin: 0;'>📈 BUY</h2>
                <p style='color: white; font-size: 24px; margin: 10px 0;'>Confidence: 78%</p>
                <p style='color: #aaa;'>BTC/USD @ $45,230.00</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### Indicator Summary")
        indicators_data = {
            "Indicator": ["RSI", "MACD", "Bollinger", "EMA Cross", "Stochastic"],
            "Value": ["42.5", "Bullish", "Lower Band", "Golden", "25.3"],
            "Signal": ["🟢 Buy", "🟢 Buy", "🟢 Buy", "🟢 Buy", "🟢 Buy"]
        }
        st.dataframe(
            pd.DataFrame(indicators_data),
            use_container_width=True,
            hide_index=True
        )

    with col2:
        st.markdown("### Pattern Recognition")
        patterns = [
            {"pattern": "Morning Star", "confidence": "85%", "signal": "🟢 Bullish"},
            {"pattern": "Double Bottom", "confidence": "72%", "signal": "🟢 Bullish"},
            {"pattern": "RSI Divergence", "confidence": "68%", "signal": "🟢 Bullish"}
        ]
        st.dataframe(pd.DataFrame(patterns), use_container_width=True, hide_index=True)

        st.markdown("### Support & Resistance")
        levels_data = {
            "Level": ["R3", "R2", "R1", "Current", "S1", "S2", "S3"],
            "Price": ["$46,500", "$45,800", "$45,400", "$45,230", "$44,800", "$44,200", "$43,500"],
            "Type": ["🔴", "🔴", "🔴", "📍", "🟢", "🟢", "🟢"]
        }
        st.dataframe(pd.DataFrame(levels_data), use_container_width=True, hide_index=True)

    st.divider()

    # Signal strength gauge
    st.markdown("### Overall Signal Strength")
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=78,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Bullish Sentiment"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "green"},
            'steps': [
                {'range': [0, 30], 'color': "red"},
                {'range': [30, 50], 'color': "orange"},
                {'range': [50, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 78
            }
        }
    ))
    gauge_fig.update_layout(height=250, template="plotly_dark")
    st.plotly_chart(gauge_fig, use_container_width=True)


def render_positions():
    """Render current positions."""
    st.subheader("💼 Current Positions")

    positions = [
        {
            "Symbol": "BTC/USD",
            "Side": "🟢 Long",
            "Entry": "$44,850.00",
            "Current": "$45,230.00",
            "Size": "0.05 BTC",
            "P&L": "+$19.00",
            "P&L %": "+0.85%",
            "Stop Loss": "$44,000.00",
            "Take Profit": "$47,000.00"
        },
        {
            "Symbol": "ETH/USD",
            "Side": "🟢 Long",
            "Entry": "$2,480.00",
            "Current": "$2,525.00",
            "Size": "0.5 ETH",
            "P&L": "+$22.50",
            "P&L %": "+1.81%",
            "Stop Loss": "$2,400.00",
            "Take Profit": "$2,700.00"
        }
    ]

    st.dataframe(pd.DataFrame(positions), use_container_width=True, hide_index=True)

    # Position actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Close All Positions", type="secondary"):
            st.warning("This will close all open positions!")
    with col2:
        if st.button("Update Stop Losses"):
            st.info("Stop losses updated to trailing")
    with col3:
        if st.button("Take Partial Profits"):
            st.success("Took 50% profits on winning positions")


def render_trade_history():
    """Render trade history."""
    st.subheader("📋 Trade History")

    trades = [
        {"Time": "14:32:15", "Symbol": "BTC/USD", "Side": "Buy", "Price": "$44,850.00",
         "Size": "0.05", "P&L": "-", "Status": "🟡 Open"},
        {"Time": "13:15:22", "Symbol": "ETH/USD", "Side": "Buy", "Price": "$2,480.00",
         "Size": "0.5", "P&L": "-", "Status": "🟡 Open"},
        {"Time": "11:45:30", "Symbol": "BTC/USD", "Side": "Sell", "Price": "$45,100.00",
         "Size": "0.03", "P&L": "+$45.30", "Status": "🟢 Closed"},
        {"Time": "10:22:18", "Symbol": "ETH/USD", "Side": "Sell", "Price": "$2,510.00",
         "Size": "0.3", "P&L": "+$18.00", "Status": "🟢 Closed"},
        {"Time": "09:05:45", "Symbol": "BTC/USD", "Side": "Buy", "Price": "$44,500.00",
         "Size": "0.03", "P&L": "-", "Status": "🔵 Filled"},
    ]

    st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)

    # Trade statistics
    st.markdown("### Today's Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", "12")
    with col2:
        st.metric("Winning", "8 (66.7%)")
    with col3:
        st.metric("Average Win", "+$32.50")
    with col4:
        st.metric("Average Loss", "-$15.20")


def render_ai_reasoning():
    """Render AI decision reasoning."""
    st.subheader("🧠 AI Decision Reasoning")

    st.markdown("### Latest Decision")

    with st.expander("BTC/USD - BUY Signal (14:32:15)", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Technical Analysis**")
            st.markdown("""
            - RSI at 42.5 (neutral-bullish zone)
            - MACD crossed above signal line
            - Price bounced off lower Bollinger Band
            - EMA 9 crossed above EMA 21
            - Volume increasing on upward movement
            """)

            st.markdown("**Pattern Recognition**")
            st.markdown("""
            - Morning Star pattern detected (85% confidence)
            - Double bottom forming on 4H chart
            - Bullish RSI divergence on 1H
            """)

        with col2:
            st.markdown("**LLM Analysis**")
            st.info("""
            "The market is showing strong signs of a potential reversal from the recent
            downtrend. Multiple technical indicators are converging on a bullish signal,
            supported by a Morning Star candlestick pattern. The RSI divergence suggests
            that selling pressure is weakening.

            Key Factors:
            1. Technical confluence of bullish signals
            2. Pattern formation suggesting reversal
            3. Decreasing sell volume
            4. Price holding above key support at $44,500

            Recommendation: BUY with 2% position size
            Target: $47,000 (R:R 2.5:1)
            Stop Loss: $44,000"
            """)

        st.markdown("**Risk Assessment**")
        risk_data = {
            "Check": ["Position Size", "Daily Loss Limit", "Correlation", "Volatility", "R:R Ratio"],
            "Status": ["✅ Pass", "✅ Pass", "✅ Pass", "⚠️ Medium", "✅ Pass"],
            "Details": ["2% of portfolio", "1.2% used of 5%", "Low BTC correlation", "ATR 3.2%", "2.5:1"]
        }
        st.dataframe(pd.DataFrame(risk_data), use_container_width=True, hide_index=True)

    # Previous decisions
    st.markdown("### Decision History")
    decisions = [
        {"Time": "13:15:22", "Symbol": "ETH/USD", "Decision": "BUY", "Confidence": "75%",
         "Outcome": "🟢 Winning (+1.8%)"},
        {"Time": "11:45:30", "Symbol": "BTC/USD", "Decision": "CLOSE", "Confidence": "82%",
         "Outcome": "🟢 Profit Taken (+$45)"},
        {"Time": "10:22:18", "Symbol": "ETH/USD", "Decision": "CLOSE", "Confidence": "68%",
         "Outcome": "🟢 Profit Taken (+$18)"},
    ]
    st.dataframe(pd.DataFrame(decisions), use_container_width=True, hide_index=True)


# Helper functions for sample data
def generate_sample_ohlcv(n: int) -> pd.DataFrame:
    """Generate sample OHLCV data."""
    import numpy as np

    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="1H")

    base_price = 45000
    price = base_price
    data = []

    for i in range(n):
        change = np.random.randn() * 100
        open_price = price
        close_price = price + change
        high_price = max(open_price, close_price) + abs(np.random.randn() * 50)
        low_price = min(open_price, close_price) - abs(np.random.randn() * 50)
        volume = np.random.randint(1000000, 5000000)

        data.append({
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume
        })
        price = close_price

    df = pd.DataFrame(data, index=dates)
    return df


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: pd.Series):
    """Calculate MACD."""
    ema_12 = prices.ewm(span=12, adjust=False).mean()
    ema_26 = prices.ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


if __name__ == "__main__":
    run_dashboard()
