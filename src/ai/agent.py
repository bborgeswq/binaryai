"""
Trading Agent
Main autonomous agent that monitors markets and executes trades
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from decimal import Decimal
from enum import Enum
from loguru import logger

from config.settings import Settings, get_settings
from src.broker import BaseBroker, Order, Position, OrderSide, OrderType
from src.data import MarketDataProvider
from src.analysis import SignalGenerator
from .decision_engine import DecisionEngine, TradingDecision, DecisionAction
from .llm_analyzer import LLMAnalyzer


class AgentState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class AgentDecision:
    """Record of an agent decision"""
    timestamp: datetime
    symbol: str
    decision: TradingDecision
    action_taken: str
    order: Optional[Order] = None
    notes: str = ""


@dataclass
class AgentStats:
    """Agent performance statistics"""
    start_time: datetime
    total_decisions: int = 0
    trades_executed: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: Decimal = Decimal("0")
    best_trade: Optional[Decimal] = None
    worst_trade: Optional[Decimal] = None
    current_positions: int = 0
    decisions_history: List[AgentDecision] = field(default_factory=list)

    @property
    def win_rate(self) -> float:
        total = self.winning_trades + self.losing_trades
        return self.winning_trades / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": str(self.start_time),
            "runtime_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
            "total_decisions": self.total_decisions,
            "trades_executed": self.trades_executed,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": f"{self.win_rate:.1%}",
            "total_pnl": float(self.total_pnl),
            "best_trade": float(self.best_trade) if self.best_trade else None,
            "worst_trade": float(self.worst_trade) if self.worst_trade else None,
            "current_positions": self.current_positions
        }


class TradingAgent:
    """
    Autonomous trading agent.
    Monitors markets, analyzes opportunities, and executes trades.
    """

    def __init__(
            self,
            broker: BaseBroker,
            data_provider: MarketDataProvider,
            decision_engine: DecisionEngine,
            settings: Optional[Settings] = None,
            symbols: Optional[List[str]] = None,
            timeframe: str = "1h",
            check_interval: int = 60,  # seconds
            on_decision: Optional[Callable[[AgentDecision], None]] = None,
            on_trade: Optional[Callable[[Order], None]] = None,
            on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Initialize trading agent.

        Args:
            broker: Broker for executing trades
            data_provider: Market data provider
            decision_engine: AI decision engine
            settings: Trading settings
            symbols: Symbols to trade
            timeframe: Analysis timeframe
            check_interval: How often to check markets (seconds)
            on_decision: Callback when decision is made
            on_trade: Callback when trade is executed
            on_error: Callback on error
        """
        self.broker = broker
        self.data = data_provider
        self.engine = decision_engine
        self.settings = settings or get_settings()

        self.symbols = symbols or self.settings.trading.symbols
        self.timeframe = timeframe
        self.check_interval = check_interval

        # Callbacks
        self.on_decision = on_decision
        self.on_trade = on_trade
        self.on_error = on_error

        # State
        self.state = AgentState.STOPPED
        self.stats = AgentStats(start_time=datetime.now())
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        logger.info(f"Trading Agent initialized for {len(self.symbols)} symbols")

    async def start(self):
        """Start the trading agent."""
        if self.state == AgentState.RUNNING:
            logger.warning("Agent is already running")
            return

        self.state = AgentState.STARTING
        self._stop_event.clear()

        # Connect to broker
        if not self.broker.is_connected:
            connected = await self.broker.connect()
            if not connected:
                self.state = AgentState.ERROR
                raise ConnectionError("Failed to connect to broker")

        # Start main loop
        self.state = AgentState.RUNNING
        self.stats = AgentStats(start_time=datetime.now())
        self._task = asyncio.create_task(self._main_loop())

        logger.info("Trading Agent started")

    async def stop(self):
        """Stop the trading agent."""
        if self.state == AgentState.STOPPED:
            return

        logger.info("Stopping Trading Agent...")
        self._stop_event.set()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.state = AgentState.STOPPED
        logger.info("Trading Agent stopped")

    async def pause(self):
        """Pause the agent (stop making new trades)."""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.PAUSED
            logger.info("Trading Agent paused")

    async def resume(self):
        """Resume the agent."""
        if self.state == AgentState.PAUSED:
            self.state = AgentState.RUNNING
            logger.info("Trading Agent resumed")

    async def _main_loop(self):
        """Main agent loop."""
        logger.info(f"Agent main loop started - checking every {self.check_interval}s")

        while not self._stop_event.is_set():
            try:
                if self.state == AgentState.RUNNING:
                    await self._analyze_and_trade()

                # Wait for next interval
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent loop error: {e}")
                if self.on_error:
                    self.on_error(e)
                # Don't crash the loop, just continue
                await asyncio.sleep(self.check_interval)

    async def _analyze_and_trade(self):
        """Analyze markets and make trading decisions."""
        logger.debug("Running analysis cycle...")

        # Get account info
        account = await self.broker.get_account()
        portfolio_value = account.equity

        # Get current positions
        positions = await self.broker.get_positions()
        position_symbols = {p.symbol for p in positions}
        self.stats.current_positions = len(positions)

        # Fetch market data for all symbols
        market_data = {}
        for symbol in self.symbols:
            try:
                df = await self.data.get_ohlcv(
                    symbol=symbol,
                    timeframe=self.timeframe,
                    limit=200
                )
                if not df.empty:
                    market_data[symbol] = df
            except Exception as e:
                logger.warning(f"Failed to get data for {symbol}: {e}")

        if not market_data:
            logger.warning("No market data available")
            return

        # Make decisions for each symbol
        for symbol, df in market_data.items():
            try:
                # Get current position for this symbol
                current_position = None
                for p in positions:
                    if p.symbol == symbol:
                        current_position = {
                            "side": "long" if p.side.value == "long" else "short",
                            "quantity": p.quantity,
                            "entry_price": p.entry_price,
                            "unrealized_pnl": p.unrealized_pnl
                        }
                        break

                # Make decision
                decision = await self.engine.make_decision(
                    df=df,
                    symbol=symbol,
                    timeframe=self.timeframe,
                    current_position=current_position,
                    portfolio_value=portfolio_value,
                    max_position_pct=self.settings.trading.max_position_size_pct
                )

                self.stats.total_decisions += 1

                # Execute decision
                order = await self._execute_decision(decision, current_position)

                # Record decision
                agent_decision = AgentDecision(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    decision=decision,
                    action_taken=decision.action.value,
                    order=order
                )
                self.stats.decisions_history.append(agent_decision)

                # Limit history size
                if len(self.stats.decisions_history) > 1000:
                    self.stats.decisions_history = self.stats.decisions_history[-500:]

                if self.on_decision:
                    self.on_decision(agent_decision)

            except Exception as e:
                logger.error(f"Decision error for {symbol}: {e}")
                if self.on_error:
                    self.on_error(e)

        # Check and manage existing positions
        await self._manage_positions(positions)

    async def _execute_decision(
            self,
            decision: TradingDecision,
            current_position: Optional[Dict[str, Any]]
    ) -> Optional[Order]:
        """Execute a trading decision."""
        if decision.action == DecisionAction.WAIT:
            logger.debug(f"{decision.symbol}: WAIT (conf: {decision.confidence:.1%})")
            return None

        if decision.action == DecisionAction.HOLD:
            logger.debug(f"{decision.symbol}: HOLD (conf: {decision.confidence:.1%})")
            return None

        # Check if we're at max positions
        positions = await self.broker.get_positions()
        if len(positions) >= self.settings.trading.max_open_positions:
            if decision.action in [DecisionAction.BUY, DecisionAction.SELL]:
                logger.info(f"Max positions ({self.settings.trading.max_open_positions}) reached - skipping {decision.symbol}")
                return None

        order = None

        if decision.action == DecisionAction.BUY:
            if not decision.quantity or decision.quantity <= 0:
                logger.warning(f"{decision.symbol}: No quantity calculated for BUY")
                return None

            logger.info(
                f"{decision.symbol}: BUY {decision.quantity} @ ${decision.entry_price:.2f} "
                f"(conf: {decision.confidence:.1%})"
            )

            order = await self.broker.submit_order(
                symbol=decision.symbol,
                side=OrderSide.BUY,
                quantity=decision.quantity,
                order_type=OrderType.MARKET
            )
            self.stats.trades_executed += 1

        elif decision.action == DecisionAction.SELL:
            # For selling (shorting), we need to have short selling enabled
            # Most crypto doesn't support shorting easily, so we'll skip for now
            logger.info(f"{decision.symbol}: SELL signal received (shorting not implemented)")
            return None

        elif decision.action == DecisionAction.CLOSE_LONG:
            if current_position:
                logger.info(
                    f"{decision.symbol}: CLOSING LONG position "
                    f"(PnL: ${current_position.get('unrealized_pnl', 0):.2f})"
                )

                order = await self.broker.close_position(decision.symbol)
                self.stats.trades_executed += 1

                # Update stats
                pnl = Decimal(str(current_position.get('unrealized_pnl', 0)))
                self.stats.total_pnl += pnl
                if pnl > 0:
                    self.stats.winning_trades += 1
                else:
                    self.stats.losing_trades += 1

                if self.stats.best_trade is None or pnl > self.stats.best_trade:
                    self.stats.best_trade = pnl
                if self.stats.worst_trade is None or pnl < self.stats.worst_trade:
                    self.stats.worst_trade = pnl

        elif decision.action == DecisionAction.CLOSE_SHORT:
            if current_position:
                logger.info(f"{decision.symbol}: CLOSING SHORT position")
                order = await self.broker.close_position(decision.symbol)
                self.stats.trades_executed += 1

        if order and self.on_trade:
            self.on_trade(order)

        return order

    async def _manage_positions(self, positions: List[Position]):
        """
        Manage existing positions - check stop loss and take profit.
        Note: This is a simplified version. In production, you'd use
        broker's native stop orders.
        """
        for position in positions:
            # Check for large losses (emergency stop)
            if position.unrealized_pnl_pct < -5.0:  # 5% loss
                logger.warning(
                    f"Emergency stop triggered for {position.symbol} "
                    f"(loss: {position.unrealized_pnl_pct:.1f}%)"
                )
                try:
                    await self.broker.close_position(position.symbol)
                    self.stats.trades_executed += 1
                    self.stats.losing_trades += 1
                    self.stats.total_pnl += position.unrealized_pnl
                except Exception as e:
                    logger.error(f"Failed to close position {position.symbol}: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "state": self.state.value,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "check_interval": self.check_interval,
            "broker_connected": self.broker.is_connected,
            "stats": self.stats.to_dict()
        }

    async def get_recent_decisions(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get recent decisions."""
        return [
            {
                "timestamp": str(d.timestamp),
                "symbol": d.symbol,
                "action": d.decision.action.value,
                "confidence": d.decision.confidence,
                "reasons": d.decision.primary_reasons[:3]
            }
            for d in self.stats.decisions_history[-n:]
        ]


class MultiAgentOrchestrator:
    """
    Orchestrates multiple trading agents for different strategies.
    """

    def __init__(self):
        self.agents: Dict[str, TradingAgent] = {}
        self._running = False

    def add_agent(self, name: str, agent: TradingAgent):
        """Add an agent to the orchestrator."""
        self.agents[name] = agent
        logger.info(f"Added agent: {name}")

    def remove_agent(self, name: str):
        """Remove an agent."""
        if name in self.agents:
            del self.agents[name]
            logger.info(f"Removed agent: {name}")

    async def start_all(self):
        """Start all agents."""
        self._running = True
        for name, agent in self.agents.items():
            await agent.start()
            logger.info(f"Started agent: {name}")

    async def stop_all(self):
        """Stop all agents."""
        self._running = False
        for name, agent in self.agents.items():
            await agent.stop()
            logger.info(f"Stopped agent: {name}")

    async def get_all_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        status = {}
        for name, agent in self.agents.items():
            status[name] = await agent.get_status()
        return status

    async def get_combined_stats(self) -> Dict[str, Any]:
        """Get combined statistics from all agents."""
        total_decisions = 0
        total_trades = 0
        total_pnl = Decimal("0")
        winning = 0
        losing = 0

        for agent in self.agents.values():
            total_decisions += agent.stats.total_decisions
            total_trades += agent.stats.trades_executed
            total_pnl += agent.stats.total_pnl
            winning += agent.stats.winning_trades
            losing += agent.stats.losing_trades

        return {
            "agents_count": len(self.agents),
            "total_decisions": total_decisions,
            "total_trades": total_trades,
            "total_pnl": float(total_pnl),
            "winning_trades": winning,
            "losing_trades": losing,
            "overall_win_rate": f"{winning / (winning + losing):.1%}" if (winning + losing) > 0 else "N/A"
        }
