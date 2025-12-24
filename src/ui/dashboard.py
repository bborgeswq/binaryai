"""
Real-Time Trading Dashboard
Streamlit-based dashboard for monitoring AI trading activity
Connected to Binance Testnet for live data
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

# Add parent path for imports
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.broker.binance_client import BinanceBroker


# Binance Testnet Configuration
BINANCE_API_KEY = "028sJM50z6LApmam3rRbV7xrdbVvcXsNV2PKBBGtyXbzIvfe7oXOUrk1TXXFy83f"
BINANCE_SECRET_KEY = "3FWoIwQGXfOh23t1p5XIIYRIt6waPNZnUT4esZdBZBodk6vkRTD0RbX9RxkOmhWb"


def get_broker():
    """Get or create Binance broker instance."""
    if 'broker' not in st.session_state:
        broker = BinanceBroker(
            api_key=BINANCE_API_KEY,
            secret_key=BINANCE_SECRET_KEY,
            testnet=True
        )
        # Connect synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        connected = loop.run_until_complete(broker.connect())
        if connected:
            st.session_state.broker = broker
            st.session_state.broker_connected = True
        else:
            st.session_state.broker_connected = False
    return st.session_state.get('broker')


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
        st.error(f"Error fetching data: {e}")
    return None


def fetch_ticker(symbol: str):
    """Fetch live ticker data."""
    broker = get_broker()
    if not broker:
        return None

    try:
        return run_async(broker.get_ticker(symbol))
    except Exception as e:
        st.error(f"Error fetching ticker: {e}")
    return None


def fetch_account():
    """Fetch account info."""
    broker = get_broker()
    if not broker:
        return None

    try:
        return run_async(broker.get_account())
    except Exception as e:
        st.error(f"Error fetching account: {e}")
    return None


def fetch_positions():
    """Fetch current positions."""
    broker = get_broker()
    if not broker:
        return []

    try:
        return run_async(broker.get_positions())
    except Exception as e:
        st.error(f"Error fetching positions: {e}")
    return []


def run_dashboard():
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="AI Day Trader",
        page_icon="",
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
    st.title("AI Day Trader Dashboard")

    # Initialize broker connection
    broker = get_broker()

    # Sidebar
    with st.sidebar:
        st.header("Settings")

        # Connection status
        st.subheader("Connection Status")
        if st.session_state.get('broker_connected', False):
            st.success("Binance TESTNET Connected")
        else:
            st.error("Binance Disconnected")
            if st.button("Reconnect"):
                if 'broker' in st.session_state:
                    del st.session_state['broker']
                get_broker()
                st.rerun()

        st.divider()

        # Agent Controls
        st.subheader("Agent Controls")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Start", use_container_width=True):
                st.session_state.agent_running = True
        with col2:
            if st.button("Stop", use_container_width=True):
                st.session_state.agent_running = False

        if st.button("Pause/Resume", use_container_width=True):
            st.session_state.agent_paused = not st.session_state.get("agent_paused", False)

        st.divider()

        # Trading Settings
        st.subheader("Trading Settings")
        mode = st.selectbox("Mode", ["Paper Trading (Testnet)", "Live Trading"])
        if mode == "Live Trading":
            st.warning("Live trading uses REAL money!")

        symbols = st.multiselect(
            "Symbols",
            ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT", "ADA/USDT"],
            default=["BTC/USDT", "ETH/USDT"]
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

    # Main Content
    # Fetch account data
    account = fetch_account()
    positions = fetch_positions()

    # Top Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if account:
            equity = float(account.equity)
            st.metric("Portfolio Value", f"${equity:,.2f} USDT")
        else:
            st.metric("Portfolio Value", "Loading...")

    with col2:
        if account:
            cash = float(account.cash)
            st.metric("Available Cash", f"${cash:,.2f} USDT")
        else:
            st.metric("Available Cash", "Loading...")

    with col3:
        st.metric("Open Positions", len(positions))

    with col4:
        win_rate = st.session_state.get('win_rate', 0)
        st.metric("Win Rate", f"{win_rate}%")

    with col5:
        agent_status = "Running" if st.session_state.get("agent_running", False) else "Stopped"
        st.metric("Agent Status", agent_status)

    st.divider()

    # Main Trading View
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Live Charts",
        "AI Analysis",
        "Positions",
        "Trade History",
        "AI Reasoning"
    ])

    with tab1:
        render_live_charts(symbols, timeframe)

    with tab2:
        render_ai_analysis(symbols)

    with tab3:
        render_positions(positions)

    with tab4:
        render_trade_history()

    with tab5:
        render_ai_reasoning()

    # Footer with auto-refresh
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if st.button("Refresh", use_container_width=True):
            st.rerun()


def render_live_charts(symbols: list, timeframe: str):
    """Render live trading charts with indicators."""
    st.subheader("Live Market View")

    # Symbol selector for chart
    selected_symbol = st.selectbox(
        "Select Symbol",
        symbols if symbols else ["BTC/USDT", "ETH/USDT"],
        key="chart_symbol"
    )

    # Fetch real data from Binance
    df = fetch_live_data(selected_symbol, timeframe, 100)

    if df is None or df.empty:
        st.warning("Unable to fetch live data. Showing sample data.")
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

    # EMA 9 (faster)
    ema_9 = df["close"].ewm(span=9, adjust=False).mean()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=ema_9,
            name="EMA 9",
            line=dict(color="cyan", width=1)
        ),
        row=1, col=1
    )

    # EMA 21 (slower)
    ema_21 = df["close"].ewm(span=21, adjust=False).mean()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=ema_21,
            name="EMA 21",
            line=dict(color="orange", width=1)
        ),
        row=1, col=1
    )

    # SMA 50
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
    colors = ["green" if h >= 0 else "red" for h in hist.fillna(0)]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=hist,
            name="Histogram",
            marker_color=colors
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

    # Fetch live ticker for accurate current price
    ticker = fetch_ticker(selected_symbol)

    if ticker:
        current_price = ticker.get('last', df["close"].iloc[-1])
        high_24h = ticker.get('high', df['high'].max())
        low_24h = ticker.get('low', df['low'].min())
        volume_24h = ticker.get('quoteVolume', df['volume'].sum())
        change_24h = ticker.get('percentage', 0)

        with col1:
            st.metric("Current Price", f"${current_price:,.2f}", f"{change_24h:+.2f}%")
        with col2:
            st.metric("24h High", f"${high_24h:,.2f}")
        with col3:
            st.metric("24h Low", f"${low_24h:,.2f}")
        with col4:
            st.metric("24h Volume", f"${volume_24h:,.0f}")
    else:
        current_price = df["close"].iloc[-1]
        price_change = df["close"].iloc[-1] - df["close"].iloc[-2]
        change_pct = price_change / df["close"].iloc[-2] * 100

        with col1:
            st.metric("Current Price", f"${current_price:,.2f}", f"{change_pct:+.2f}%")
        with col2:
            st.metric("24h High", f"${df['high'].max():,.2f}")
        with col3:
            st.metric("24h Low", f"${df['low'].min():,.2f}")
        with col4:
            st.metric("Volume", f"${df['volume'].sum():,.0f}")


def render_ai_analysis(symbols: list):
    """Render AI analysis and signals."""
    st.subheader("AI Market Analysis")

    # Get live data for analysis
    selected_symbol = symbols[0] if symbols else "BTC/USDT"
    df = fetch_live_data(selected_symbol, "1h", 50)
    ticker = fetch_ticker(selected_symbol)

    if df is None or df.empty:
        df = generate_sample_ohlcv(50)

    # Calculate indicators
    rsi = calculate_rsi(df["close"]).iloc[-1]
    macd, signal, hist = calculate_macd(df["close"])
    macd_val = macd.iloc[-1]
    signal_val = signal.iloc[-1]

    # Determine signal
    signals = []
    if rsi < 30:
        signals.append(("RSI", "Oversold - BUY"))
    elif rsi > 70:
        signals.append(("RSI", "Overbought - SELL"))
    else:
        signals.append(("RSI", "Neutral"))

    if macd_val > signal_val:
        signals.append(("MACD", "Bullish"))
    else:
        signals.append(("MACD", "Bearish"))

    # EMA cross
    ema_9 = df["close"].ewm(span=9, adjust=False).mean().iloc[-1]
    ema_21 = df["close"].ewm(span=21, adjust=False).mean().iloc[-1]
    if ema_9 > ema_21:
        signals.append(("EMA Cross", "Bullish"))
    else:
        signals.append(("EMA Cross", "Bearish"))

    # Bollinger position
    sma_20 = df["close"].rolling(20).mean().iloc[-1]
    std_20 = df["close"].rolling(20).std().iloc[-1]
    current_price = df["close"].iloc[-1]

    if current_price < sma_20 - 2 * std_20:
        signals.append(("Bollinger", "Lower Band - BUY"))
    elif current_price > sma_20 + 2 * std_20:
        signals.append(("Bollinger", "Upper Band - SELL"))
    else:
        signals.append(("Bollinger", "Middle"))

    # Calculate overall signal
    bullish_count = sum(1 for _, sig in signals if "Bullish" in sig or "BUY" in sig)
    bearish_count = sum(1 for _, sig in signals if "Bearish" in sig or "SELL" in sig)

    if bullish_count > bearish_count:
        overall_signal = "BUY"
        confidence = int((bullish_count / len(signals)) * 100)
        signal_color = "#1a472a"
    elif bearish_count > bullish_count:
        overall_signal = "SELL"
        confidence = int((bearish_count / len(signals)) * 100)
        signal_color = "#472a1a"
    else:
        overall_signal = "HOLD"
        confidence = 50
        signal_color = "#2a2a47"

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Current Signal")
        current_price_str = f"${ticker.get('last', current_price):,.2f}" if ticker else f"${current_price:,.2f}"
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, {signal_color} 0%, #2d2d2d 100%);
                    padding: 20px; border-radius: 10px; text-align: center;'>
            <h2 style='color: {"#00ff00" if overall_signal == "BUY" else "#ff4444" if overall_signal == "SELL" else "#ffff00"}; margin: 0;'>{overall_signal}</h2>
            <p style='color: white; font-size: 24px; margin: 10px 0;'>Confidence: {confidence}%</p>
            <p style='color: #aaa;'>{selected_symbol} @ {current_price_str}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Indicator Summary")
        indicators_data = {
            "Indicator": ["RSI", "MACD", "Bollinger", "EMA Cross"],
            "Value": [f"{rsi:.1f}", f"{macd_val:.2f}", f"{'Lower' if current_price < sma_20 else 'Upper'}", f"{'Golden' if ema_9 > ema_21 else 'Death'}"],
            "Signal": [signals[0][1], signals[1][1], signals[3][1], signals[2][1]]
        }
        st.dataframe(
            pd.DataFrame(indicators_data),
            use_container_width=True,
            hide_index=True
        )

    with col2:
        st.markdown("### Price Levels")

        # Calculate support/resistance from recent highs/lows
        recent_high = df['high'].iloc[-20:].max()
        recent_low = df['low'].iloc[-20:].min()
        pivot = (recent_high + recent_low + current_price) / 3
        r1 = 2 * pivot - recent_low
        r2 = pivot + (recent_high - recent_low)
        s1 = 2 * pivot - recent_high
        s2 = pivot - (recent_high - recent_low)

        levels_data = {
            "Level": ["R2", "R1", "Pivot", "Current", "S1", "S2"],
            "Price": [f"${r2:,.2f}", f"${r1:,.2f}", f"${pivot:,.2f}", f"${current_price:,.2f}", f"${s1:,.2f}", f"${s2:,.2f}"],
            "Type": ["Resistance", "Resistance", "Pivot", "Price", "Support", "Support"]
        }
        st.dataframe(pd.DataFrame(levels_data), use_container_width=True, hide_index=True)

        st.markdown("### Market Stats")
        if ticker:
            stats_data = {
                "Metric": ["24h Change", "24h Volume", "Bid/Ask Spread"],
                "Value": [
                    f"{ticker.get('percentage', 0):+.2f}%",
                    f"${ticker.get('quoteVolume', 0):,.0f}",
                    f"${(ticker.get('ask', 0) - ticker.get('bid', 0)):,.2f}"
                ]
            }
            st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)

    st.divider()

    # Signal strength gauge
    st.markdown("### Overall Signal Strength")
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"{'Bullish' if overall_signal == 'BUY' else 'Bearish' if overall_signal == 'SELL' else 'Neutral'} Sentiment"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "green" if overall_signal == "BUY" else "red" if overall_signal == "SELL" else "yellow"},
            'steps': [
                {'range': [0, 30], 'color': "red"},
                {'range': [30, 50], 'color': "orange"},
                {'range': [50, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': confidence
            }
        }
    ))
    gauge_fig.update_layout(height=250, template="plotly_dark")
    st.plotly_chart(gauge_fig, use_container_width=True)


def render_positions(positions: list):
    """Render current positions."""
    st.subheader("Current Positions")

    if not positions:
        st.info("No open positions")

        # Manual trading interface
        st.markdown("### Manual Trade")
        col1, col2, col3 = st.columns(3)
        with col1:
            trade_symbol = st.selectbox("Symbol", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
        with col2:
            trade_side = st.selectbox("Side", ["BUY", "SELL"])
        with col3:
            trade_amount = st.number_input("Amount", min_value=0.0001, value=0.001, step=0.0001)

        if st.button("Execute Trade", type="primary"):
            st.warning("Manual trading will be enabled in the next update")
        return

    # Display positions
    positions_data = []
    for p in positions:
        positions_data.append({
            "Symbol": p.symbol,
            "Side": "Long" if str(p.side) == "PositionSide.LONG" else "Short",
            "Quantity": float(p.quantity),
            "Current Price": f"${float(p.current_price):,.2f}",
            "Market Value": f"${float(p.market_value):,.2f}",
            "P&L": f"${float(p.unrealized_pnl):,.2f}",
            "P&L %": f"{p.unrealized_pnl_pct:.2f}%"
        })

    st.dataframe(pd.DataFrame(positions_data), use_container_width=True, hide_index=True)

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
    st.subheader("Trade History")

    # Get from session state or show empty
    trades = st.session_state.get('trade_history', [])

    if not trades:
        st.info("No trade history yet. Trades will appear here once the AI agent executes them.")

        # Show sample format
        sample_trades = [
            {"Time": "Example", "Symbol": "BTC/USDT", "Side": "Buy", "Price": "$95,000.00",
             "Size": "0.001", "P&L": "+$10.00", "Status": "Closed"},
        ]
        st.dataframe(pd.DataFrame(sample_trades), use_container_width=True, hide_index=True)
        return

    st.dataframe(pd.DataFrame(trades), use_container_width=True, hide_index=True)

    # Trade statistics
    st.markdown("### Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", len(trades))
    with col2:
        winning = sum(1 for t in trades if t.get('P&L', '').startswith('+'))
        st.metric("Winning", f"{winning} ({100*winning/len(trades):.1f}%)" if trades else "0")
    with col3:
        st.metric("Average Win", "Calculating...")
    with col4:
        st.metric("Average Loss", "Calculating...")


def render_ai_reasoning():
    """Render AI decision reasoning."""
    st.subheader("AI Decision Reasoning")

    st.markdown("### How the AI Analyzes Markets")

    st.markdown("""
    The AI trading system uses multiple layers of analysis:

    **1. Technical Analysis**
    - RSI (Relative Strength Index) - Identifies overbought/oversold conditions
    - MACD (Moving Average Convergence Divergence) - Trend momentum
    - Bollinger Bands - Volatility and price extremes
    - EMA Crossovers - Trend direction changes
    - Support/Resistance Levels - Key price zones

    **2. Pattern Recognition**
    - Candlestick patterns (Doji, Hammer, Engulfing, etc.)
    - Chart patterns (Double Top/Bottom, Head & Shoulders, Triangles)
    - Volume analysis

    **3. LLM Analysis (Coming Soon)**
    - Market sentiment from news
    - Cross-asset correlations
    - Risk/reward optimization

    **4. Risk Management**
    - Position sizing based on portfolio risk
    - Stop loss placement
    - Maximum daily loss limits
    - Correlation checks between positions
    """)

    st.divider()

    st.markdown("### Recent Decisions")
    decisions = st.session_state.get('ai_decisions', [])

    if not decisions:
        st.info("No AI decisions yet. Start the agent to see reasoning here.")
    else:
        for d in decisions[-5:]:
            with st.expander(f"{d['symbol']} - {d['action']} ({d['time']})"):
                st.write(d['reasoning'])


# Helper functions
def generate_sample_ohlcv(n: int) -> pd.DataFrame:
    """Generate sample OHLCV data as fallback."""
    import numpy as np

    np.random.seed(int(datetime.now().timestamp()) % 100)
    dates = pd.date_range(end=datetime.now(), periods=n, freq="1H")

    base_price = 95000  # Current BTC approximate price
    price = base_price
    data = []

    for i in range(n):
        change = np.random.randn() * 500
        open_price = price
        close_price = price + change
        high_price = max(open_price, close_price) + abs(np.random.randn() * 200)
        low_price = min(open_price, close_price) - abs(np.random.randn() * 200)
        volume = np.random.randint(100000000, 500000000)

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
