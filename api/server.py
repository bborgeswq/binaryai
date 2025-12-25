"""
FastAPI Backend for AI Trading Platform
Real connection to Binance - no fake data
"""
import asyncio
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.broker.binance_client import BinanceBroker
from src.learning.database import TradingDatabase
from src.strategies.liquidity_sweep import LiquiditySweepStrategy
from src.ai.activity_tracker import AIActivityTracker, ActivityType

# Configuration
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
BINANCE_TESTNET = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'

# Global instances
broker: Optional[BinanceBroker] = None
database: Optional[TradingDatabase] = None
strategy: Optional[LiquiditySweepStrategy] = None
tracker: Optional[AIActivityTracker] = None
trading_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global broker, database, strategy, tracker

    # Initialize database
    database = TradingDatabase(str(project_root / 'data' / 'trading_history.db'))
    tracker = AIActivityTracker()

    # Initialize broker
    if BINANCE_API_KEY and BINANCE_SECRET_KEY:
        broker = BinanceBroker(BINANCE_API_KEY, BINANCE_SECRET_KEY, testnet=BINANCE_TESTNET)
        connected = await broker.connect()
        if connected:
            print(f"Connected to Binance {'Testnet' if BINANCE_TESTNET else 'Live'}")

            # Get account info to set account size
            try:
                account_info = await broker.get_account()
                account_size = float(account_info.equity)
            except:
                account_size = 10000.0  # Default

            # Initialize strategy
            strategy = LiquiditySweepStrategy(
                broker=broker,
                symbols=['BTC/USDT', 'ETH/USDT', 'XRP/USDT'],
                risk_per_trade=0.07,  # 7% risk per trade
                min_rr=2.0,  # Minimum 2:1 risk/reward
                account_size=account_size
            )
            print(f"Strategy initialized: TJR Liquidity Sweep")
            print(f"Account size: ${account_size:,.2f}, Risk per trade: 7%")
        else:
            print("Failed to connect to Binance")
    else:
        print("No API keys configured")

    yield

    # Cleanup
    if trading_task and not trading_task.done():
        trading_task.cancel()


app = FastAPI(
    title="Vertex Trading API",
    description="Real-time trading API with TJR Liquidity Sweep Strategy",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Pydantic Models ==============

class ConnectionStatus(BaseModel):
    connected: bool
    exchange: str
    testnet: bool
    message: str


class AccountInfo(BaseModel):
    equity: float
    available_balance: float
    currency: str
    positions_count: int


class MarketData(BaseModel):
    symbol: str
    price: float
    change_24h: float
    change_percent: float
    high_24h: float
    low_24h: float
    volume_24h: float
    timestamp: str


class Position(BaseModel):
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float


class TradeRecord(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    status: str
    strategy: str
    entry_time: str
    exit_time: Optional[str]


class AgentStatus(BaseModel):
    running: bool
    strategy: str
    symbols: List[str]
    risk_percent: float
    last_signal: Optional[Dict[str, Any]]


class SignalInfo(BaseModel):
    symbol: str
    signal_type: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confluences: List[str]
    timeframes_aligned: List[str]
    timestamp: str


# ============== API Endpoints ==============

@app.get("/")
async def root():
    return {"message": "Vertex Trading API", "status": "running"}


@app.get("/api/status", response_model=ConnectionStatus)
async def get_status():
    """Get connection status"""
    if broker and await broker.connect():
        return ConnectionStatus(
            connected=True,
            exchange="Binance",
            testnet=BINANCE_TESTNET,
            message="Connected successfully"
        )
    return ConnectionStatus(
        connected=False,
        exchange="Binance",
        testnet=BINANCE_TESTNET,
        message="Not connected - check API keys"
    )


@app.get("/api/account", response_model=AccountInfo)
async def get_account():
    """Get real account information"""
    if not broker:
        raise HTTPException(status_code=503, detail="Broker not connected")

    try:
        account = await broker.get_account()
        positions = await broker.get_positions()
        return AccountInfo(
            equity=float(account.equity),
            available_balance=float(account.cash),
            currency="USDT",
            positions_count=len([p for p in positions if float(p.quantity) > 0])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/{symbol}", response_model=MarketData)
async def get_market_data(symbol: str):
    """Get real-time market data for a symbol"""
    if not broker:
        raise HTTPException(status_code=503, detail="Broker not connected")

    try:
        ticker = await broker.get_ticker(symbol)
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        return MarketData(
            symbol=symbol,
            price=ticker.get('last', 0),
            change_24h=ticker.get('last', 0) - ticker.get('open', 0),
            change_percent=ticker.get('percentage', 0),
            high_24h=ticker.get('high', 0),
            low_24h=ticker.get('low', 0),
            volume_24h=ticker.get('quoteVolume', 0),
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/prices")
async def get_all_prices():
    """Get prices for all tracked symbols"""
    if not broker:
        raise HTTPException(status_code=503, detail="Broker not connected")

    symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']
    prices = {}

    for symbol in symbols:
        try:
            ticker = await broker.get_ticker(symbol)
            if ticker:
                prices[symbol] = {
                    'price': ticker.get('last', 0),
                    'change_percent': ticker.get('percentage', 0),
                    'high': ticker.get('high', 0),
                    'low': ticker.get('low', 0),
                    'volume': ticker.get('quoteVolume', 0)
                }
        except:
            pass

    return {"prices": prices, "timestamp": datetime.now().isoformat()}


@app.get("/api/ohlcv/{symbol}")
async def get_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 100):
    """Get OHLCV candle data"""
    if not broker:
        raise HTTPException(status_code=503, detail="Broker not connected")

    try:
        ohlcv = await broker.get_ohlcv(symbol, timeframe, limit)
        if not ohlcv:
            return {"candles": [], "symbol": symbol, "timeframe": timeframe}

        candles = []
        for candle in ohlcv:
            candles.append({
                "timestamp": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5]
            })

        return {"candles": candles, "symbol": symbol, "timeframe": timeframe}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/positions", response_model=List[Position])
async def get_positions():
    """Get current open positions"""
    if not broker:
        raise HTTPException(status_code=503, detail="Broker not connected")

    try:
        positions = await broker.get_positions()
        result = []
        for pos in positions:
            qty = float(pos.quantity)
            if qty > 0:
                entry = float(pos.entry_price) if pos.entry_price else 0
                current = float(pos.current_price) if pos.current_price else entry
                pnl = (current - entry) * qty if pos.side == 'long' else (entry - current) * qty
                pnl_pct = (pnl / (entry * qty) * 100) if entry > 0 else 0

                result.append(Position(
                    symbol=pos.symbol,
                    side=pos.side,
                    quantity=qty,
                    entry_price=entry,
                    current_price=current,
                    pnl=pnl,
                    pnl_percent=pnl_pct
                ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trades", response_model=List[TradeRecord])
async def get_trades(limit: int = 20):
    """Get trade history from database (real trades only)"""
    if not database:
        raise HTTPException(status_code=503, detail="Database not initialized")

    trades = database.get_recent_trades(limit)
    return [
        TradeRecord(
            id=t.id or 0,
            symbol=t.symbol,
            side=t.side,
            quantity=t.quantity,
            entry_price=t.entry_price,
            exit_price=t.exit_price,
            pnl=t.pnl,
            status=t.status,
            strategy=t.strategy or "TJR_Liquidity_Sweep",
            entry_time=t.entry_time or "",
            exit_time=t.exit_time
        )
        for t in trades
    ]


@app.get("/api/stats")
async def get_stats():
    """Get real trading statistics"""
    if not database:
        raise HTTPException(status_code=503, detail="Database not initialized")

    stats = database.get_performance_stats(days=30)
    return {
        "total_trades": stats.get('total_trades', 0),
        "winning_trades": stats.get('winning_trades', 0),
        "losing_trades": stats.get('losing_trades', 0),
        "win_rate": stats.get('win_rate', 0),
        "total_pnl": stats.get('total_pnl', 0),
        "avg_win": stats.get('avg_win', 0),
        "avg_loss": stats.get('avg_loss', 0),
        "profit_factor": stats.get('profit_factor', 0),
        "period_days": 30
    }


# ============== Agent Control ==============

@app.get("/api/agent/status", response_model=AgentStatus)
async def get_agent_status():
    """Get trading agent status"""
    global strategy, trading_task

    running = trading_task is not None and not trading_task.done()

    # Get last signal from active setups
    last_signal = None
    if strategy and strategy.active_setups:
        for symbol, setup in strategy.active_setups.items():
            last_signal = {
                "symbol": symbol,
                "signal": setup.signal.value,
                "entry": setup.entry_price,
                "stop_loss": setup.stop_loss,
                "take_profit": setup.take_profit,
                "confidence": setup.confidence
            }
            break

    return AgentStatus(
        running=running,
        strategy="TJR Liquidity Sweep",
        symbols=["BTC/USDT", "ETH/USDT", "XRP/USDT"],
        risk_percent=7.0,
        last_signal=last_signal
    )


@app.post("/api/agent/start")
async def start_agent():
    """Start the trading agent"""
    global trading_task, strategy, tracker

    if not strategy:
        raise HTTPException(status_code=503, detail="Strategy not initialized")

    if trading_task and not trading_task.done():
        return {"message": "Agent already running", "status": "running"}

    # Start trading loop (analyzes every 60 seconds)
    trading_task = asyncio.create_task(strategy.run_analysis_loop(interval_seconds=60))
    tracker.log_activity(ActivityType.THINKING, "SYSTEM", "Agent Started", "TJR Liquidity Sweep strategy activated")

    return {"message": "Agent started", "status": "running"}


@app.post("/api/agent/stop")
async def stop_agent():
    """Stop the trading agent"""
    global trading_task, tracker

    if trading_task and not trading_task.done():
        trading_task.cancel()
        try:
            await trading_task
        except asyncio.CancelledError:
            pass
        trading_task = None
        tracker.log_activity(ActivityType.THINKING, "SYSTEM", "Agent Stopped", "Trading agent deactivated")

    return {"message": "Agent stopped", "status": "stopped"}


@app.get("/api/signals/current")
async def get_current_signals():
    """Get current analysis and signals from strategy"""
    if not strategy:
        raise HTTPException(status_code=503, detail="Strategy not initialized")

    try:
        signals = []
        for symbol in strategy.symbols:
            setup = await strategy.analyze_symbol(symbol)
            if setup:
                signals.append({
                    "symbol": symbol,
                    "signal": setup.signal.value,
                    "entry_price": setup.entry_price,
                    "stop_loss": setup.stop_loss,
                    "take_profit": setup.take_profit,
                    "risk_reward": setup.risk_reward,
                    "confidence": setup.confidence,
                    "reasoning": setup.reasoning,
                    "setup_type": setup.setup_type
                })

        return {"signals": signals, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/activity")
async def get_activity():
    """Get recent AI activity"""
    if not tracker:
        return {"activities": []}

    activities = tracker.get_recent_activities(30)
    return {
        "activities": [
            {
                "type": a.activity_type.value,
                "symbol": a.symbol,
                "title": a.title,
                "description": a.description,
                "timestamp": a.timestamp.isoformat()
            }
            for a in activities
        ]
    }


@app.get("/api/strategy/status")
async def get_strategy_status():
    """Get detailed strategy status including detected patterns"""
    if not strategy:
        raise HTTPException(status_code=503, detail="Strategy not initialized")

    return {
        "status": strategy.get_status(),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/strategy/zones/{symbol}")
async def get_liquidity_zones(symbol: str):
    """Get liquidity zones for a symbol"""
    if not strategy:
        raise HTTPException(status_code=503, detail="Strategy not initialized")

    # Normalize symbol format
    if '/' not in symbol:
        symbol = symbol[:3] + '/' + symbol[3:] if len(symbol) > 3 else symbol

    zones = strategy.liquidity_zones.get(symbol, [])
    order_blocks = strategy.order_blocks.get(symbol, [])
    fvgs = strategy.fvgs.get(symbol, [])

    return {
        "symbol": symbol,
        "liquidity_zones": [
            {
                "price_low": z.price_low,
                "price_high": z.price_high,
                "type": z.zone_type,
                "strength": z.strength,
                "swept": z.swept
            }
            for z in zones
        ],
        "order_blocks": [
            {
                "high": ob.high,
                "low": ob.low,
                "type": ob.block_type,
                "strength": ob.strength,
                "mitigated": ob.mitigated
            }
            for ob in order_blocks
        ],
        "fair_value_gaps": [
            {
                "high": fvg.high,
                "low": fvg.low,
                "type": fvg.gap_type,
                "filled": fvg.filled
            }
            for fvg in fvgs
        ],
        "timestamp": datetime.now().isoformat()
    }


# ============== WebSocket for Real-Time Data ==============

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """WebSocket for real-time price updates"""
    await manager.connect(websocket)
    try:
        while True:
            if broker:
                prices = {}
                for symbol in ['BTCUSDT', 'ETHUSDT', 'XRPUSDT']:
                    try:
                        ticker = await broker.get_ticker(symbol)
                        if ticker:
                            prices[symbol] = {
                                'price': ticker.get('last', 0),
                                'change': ticker.get('percentage', 0)
                            }
                    except:
                        pass

                await websocket.send_json({
                    "type": "prices",
                    "data": prices,
                    "timestamp": datetime.now().isoformat()
                })

            await asyncio.sleep(2)  # Update every 2 seconds
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
