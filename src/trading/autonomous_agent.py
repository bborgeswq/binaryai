"""
Autonomous Trading Agent
Executes trades automatically based on AI analysis
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal
from pathlib import Path
from loguru import logger

# Add parent path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.broker.binance_client import BinanceBroker
from src.broker.base import OrderSide, OrderType
from src.learning.database import TradingDatabase, Trade, AIDecision
from src.data.news import NewsAggregator, get_market_sentiment


class TradingAgent:
    """Autonomous AI trading agent."""

    def __init__(
        self,
        symbols: List[str] = None,
        timeframe: str = "1h",
        max_risk_per_trade: float = 0.02,  # 2% of portfolio
        max_positions: int = 3,
        max_daily_loss: float = 0.05,  # 5% of portfolio
        min_confidence: float = 0.6,  # 60% confidence threshold
        testnet: bool = True
    ):
        self.symbols = symbols or ["BTC/USDT", "ETH/USDT"]
        self.timeframe = timeframe
        self.max_risk_per_trade = max_risk_per_trade
        self.max_positions = max_positions
        self.max_daily_loss = max_daily_loss
        self.min_confidence = min_confidence
        self.testnet = testnet

        # Initialize components
        self.broker: Optional[BinanceBroker] = None
        self.db: Optional[TradingDatabase] = None
        self.news_aggregator: Optional[NewsAggregator] = None

        # State
        self.running = False
        self.paused = False
        self.daily_pnl = 0.0
        self.today_trades = 0

        # Callbacks for UI updates
        self.on_signal = None
        self.on_trade = None
        self.on_decision = None

    async def initialize(self) -> bool:
        """Initialize all connections."""
        try:
            # Initialize broker
            api_key = os.getenv('BINANCE_API_KEY', '')
            secret_key = os.getenv('BINANCE_SECRET_KEY', '')

            if not api_key or not secret_key:
                logger.error("Binance API keys not found in .env")
                return False

            self.broker = BinanceBroker(
                api_key=api_key,
                secret_key=secret_key,
                testnet=self.testnet
            )

            connected = await self.broker.connect()
            if not connected:
                logger.error("Failed to connect to Binance")
                return False

            # Initialize database
            db_path = project_root / 'data' / 'trading_history.db'
            self.db = TradingDatabase(str(db_path))

            # Initialize news
            self.news_aggregator = NewsAggregator()

            logger.info("Trading agent initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            return False

    async def start(self):
        """Start the trading agent."""
        if not self.broker or not self.db:
            if not await self.initialize():
                return

        self.running = True
        self.paused = False

        logger.info("🤖 Trading agent started")
        logger.info(f"📊 Monitoring: {', '.join(self.symbols)}")
        logger.info(f"⏰ Timeframe: {self.timeframe}")

        while self.running:
            try:
                if not self.paused:
                    await self._trading_cycle()

                # Wait before next cycle (based on timeframe)
                wait_time = self._get_cycle_interval()
                await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"Error in trading cycle: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def stop(self):
        """Stop the trading agent."""
        self.running = False
        logger.info("🛑 Trading agent stopped")

    def pause(self):
        """Pause trading."""
        self.paused = True
        logger.info("⏸️ Trading agent paused")

    def resume(self):
        """Resume trading."""
        self.paused = False
        logger.info("▶️ Trading agent resumed")

    async def _trading_cycle(self):
        """Execute one trading cycle."""
        logger.info(f"📡 Starting trading cycle at {datetime.now().strftime('%H:%M:%S')}")

        # Check daily loss limit
        if self._check_daily_loss_limit():
            logger.warning("⚠️ Daily loss limit reached, skipping cycle")
            return

        # Get current positions
        positions = await self.broker.get_positions()
        open_positions = len(positions)

        # Analyze each symbol
        for symbol in self.symbols:
            try:
                # Skip if max positions reached
                if open_positions >= self.max_positions:
                    logger.info(f"Max positions ({self.max_positions}) reached")
                    break

                # Check if we already have a position in this symbol
                has_position = any(p.symbol == symbol for p in positions)

                # Analyze the market
                analysis = await self._analyze_symbol(symbol)

                if analysis['signal'] == 'HOLD':
                    continue

                # Check confidence threshold
                if analysis['confidence'] < self.min_confidence:
                    logger.info(f"{symbol}: Signal {analysis['signal']} but confidence too low ({analysis['confidence']:.0%})")
                    continue

                # Execute trade logic
                if analysis['signal'] == 'BUY' and not has_position:
                    await self._execute_buy(symbol, analysis)
                    open_positions += 1

                elif analysis['signal'] == 'SELL' and has_position:
                    await self._execute_sell(symbol, analysis, positions)
                    open_positions -= 1

            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")

    async def _analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Analyze a symbol and generate trading signal."""

        # Fetch market data
        ohlcv = await self.broker.get_ohlcv(symbol, self.timeframe, 100)
        ticker = await self.broker.get_ticker(symbol)

        if not ohlcv or not ticker:
            return {'signal': 'HOLD', 'confidence': 0, 'reasoning': 'No data'}

        # Calculate indicators
        closes = [candle[4] for candle in ohlcv]
        highs = [candle[2] for candle in ohlcv]
        lows = [candle[3] for candle in ohlcv]

        rsi = self._calculate_rsi(closes)
        macd, signal_line, histogram = self._calculate_macd(closes)
        ema_9 = self._calculate_ema(closes, 9)
        ema_21 = self._calculate_ema(closes, 21)
        current_price = closes[-1]

        # Generate signals
        bullish_signals = 0
        bearish_signals = 0
        reasons = []

        # RSI
        if rsi < 30:
            bullish_signals += 1
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > 70:
            bearish_signals += 1
            reasons.append(f"RSI overbought ({rsi:.1f})")

        # MACD
        if macd > signal_line:
            bullish_signals += 1
            reasons.append("MACD bullish crossover")
        else:
            bearish_signals += 1
            reasons.append("MACD bearish")

        # EMA Cross
        if ema_9 > ema_21:
            bullish_signals += 1
            reasons.append("EMA golden cross")
        else:
            bearish_signals += 1
            reasons.append("EMA death cross")

        # Price action
        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])
        price_position = (current_price - recent_low) / (recent_high - recent_low) if recent_high != recent_low else 0.5

        if price_position < 0.3:
            bullish_signals += 1
            reasons.append("Price near support")
        elif price_position > 0.7:
            bearish_signals += 1
            reasons.append("Price near resistance")

        # Get news sentiment
        try:
            sentiment = await get_market_sentiment()
            if sentiment.get('overall') == 'bullish':
                bullish_signals += 0.5
                reasons.append("News sentiment bullish")
            elif sentiment.get('overall') == 'bearish':
                bearish_signals += 0.5
                reasons.append("News sentiment bearish")
        except:
            pass

        # Determine signal
        total_signals = bullish_signals + bearish_signals
        if bullish_signals > bearish_signals + 1:
            signal = 'BUY'
            confidence = bullish_signals / (total_signals + 1)
        elif bearish_signals > bullish_signals + 1:
            signal = 'SELL'
            confidence = bearish_signals / (total_signals + 1)
        else:
            signal = 'HOLD'
            confidence = 0.5

        # Get learning context
        context = self.db.get_context_for_ai(symbol) if self.db else ""

        analysis = {
            'signal': signal,
            'confidence': min(confidence, 1.0),
            'price': current_price,
            'rsi': rsi,
            'macd': macd,
            'ema_9': ema_9,
            'ema_21': ema_21,
            'reasoning': ' | '.join(reasons),
            'context': context,
            'indicators': {
                'rsi': rsi,
                'macd': macd,
                'macd_signal': signal_line,
                'ema_9': ema_9,
                'ema_21': ema_21
            }
        }

        # Record AI decision
        if self.db:
            decision = AIDecision(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                action=signal,
                confidence=confidence,
                reasoning=analysis['reasoning'],
                indicators=str(analysis['indicators']),
                market_context=context
            )
            self.db.add_decision(decision)

        # Callback
        if self.on_signal:
            self.on_signal(symbol, analysis)

        logger.info(f"📊 {symbol}: {signal} (confidence: {confidence:.0%}) - {analysis['reasoning']}")

        return analysis

    async def _execute_buy(self, symbol: str, analysis: Dict[str, Any]):
        """Execute a buy order."""
        try:
            # Get account info for position sizing
            account = await self.broker.get_account()
            equity = float(account.equity)

            # Calculate position size based on risk
            risk_amount = equity * self.max_risk_per_trade
            price = analysis['price']

            # For crypto, calculate quantity
            quantity = risk_amount / price

            # Round to appropriate precision
            quantity = round(quantity, 6)

            logger.info(f"🟢 Executing BUY: {quantity} {symbol} @ ${price:,.2f}")

            # Place market order
            order = await self.broker.place_order(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                order_type=OrderType.MARKET
            )

            if order:
                # Record trade
                trade = Trade(
                    symbol=symbol,
                    side="BUY",
                    entry_price=price,
                    quantity=quantity,
                    entry_time=datetime.now().isoformat(),
                    status="open",
                    strategy="AI_AUTO",
                    timeframe=self.timeframe,
                    indicators_at_entry=str(analysis['indicators']),
                    notes=analysis['reasoning']
                )

                if self.db:
                    trade_id = self.db.add_trade(trade)
                    logger.info(f"✅ Trade #{trade_id} recorded")

                self.today_trades += 1

                # Callback
                if self.on_trade:
                    self.on_trade('BUY', symbol, quantity, price)

        except Exception as e:
            logger.error(f"❌ Failed to execute buy: {e}")

    async def _execute_sell(self, symbol: str, analysis: Dict[str, Any], positions: list):
        """Execute a sell order to close position."""
        try:
            # Find the position
            position = next((p for p in positions if p.symbol == symbol), None)
            if not position:
                return

            quantity = float(position.quantity)
            price = analysis['price']

            logger.info(f"🔴 Executing SELL: {quantity} {symbol} @ ${price:,.2f}")

            # Place market sell order
            order = await self.broker.place_order(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=OrderType.MARKET
            )

            if order:
                # Calculate P&L
                entry_price = float(position.entry_price) if hasattr(position, 'entry_price') else price
                pnl = (price - entry_price) * quantity

                # Update trade in database
                if self.db:
                    # Find and close the open trade
                    open_trades = self.db.get_open_trades()
                    for trade in open_trades:
                        if trade.symbol == symbol:
                            self.db.close_trade(
                                trade.id,
                                exit_price=price,
                                indicators_at_exit=analysis['indicators']
                            )
                            break

                # Update daily P&L
                self.daily_pnl += pnl

                logger.info(f"✅ Position closed. P&L: ${pnl:,.2f}")

                # Callback
                if self.on_trade:
                    self.on_trade('SELL', symbol, quantity, price, pnl)

        except Exception as e:
            logger.error(f"❌ Failed to execute sell: {e}")

    def _check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit is reached."""
        if not self.broker:
            return False

        # Reset at midnight
        now = datetime.now()
        if now.hour == 0 and now.minute < 5:
            self.daily_pnl = 0.0
            self.today_trades = 0

        # Check limit
        try:
            # Get initial equity (simplified - should store at day start)
            loop = asyncio.get_event_loop()
            account = loop.run_until_complete(self.broker.get_account())
            equity = float(account.equity)

            max_loss = equity * self.max_daily_loss

            if self.daily_pnl < -max_loss:
                return True

        except:
            pass

        return False

    def _get_cycle_interval(self) -> int:
        """Get wait time between cycles based on timeframe."""
        intervals = {
            "1m": 30,      # 30 seconds
            "5m": 120,     # 2 minutes
            "15m": 300,    # 5 minutes
            "1h": 600,     # 10 minutes
            "4h": 1800,    # 30 minutes
            "1d": 3600     # 1 hour
        }
        return intervals.get(self.timeframe, 600)

    # Technical Analysis Helpers
    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, prices: list) -> tuple:
        """Calculate MACD."""
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd = ema_12 - ema_26

        # Signal line (9-period EMA of MACD)
        signal = macd  # Simplified

        return macd, signal, macd - signal

    def _calculate_ema(self, prices: list, period: int) -> float:
        """Calculate EMA."""
        if len(prices) < period:
            return prices[-1] if prices else 0

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema


async def run_agent():
    """Run the trading agent."""
    agent = TradingAgent(
        symbols=["BTC/USDT", "ETH/USDT"],
        timeframe="1h",
        max_risk_per_trade=0.02,
        max_positions=3,
        testnet=True
    )

    def on_signal(symbol, analysis):
        print(f"📊 Signal: {symbol} - {analysis['signal']} ({analysis['confidence']:.0%})")

    def on_trade(action, symbol, quantity, price, pnl=None):
        pnl_str = f" P&L: ${pnl:,.2f}" if pnl else ""
        print(f"💰 Trade: {action} {quantity} {symbol} @ ${price:,.2f}{pnl_str}")

    agent.on_signal = on_signal
    agent.on_trade = on_trade

    await agent.start()


if __name__ == "__main__":
    print("🤖 Starting AI Trading Agent...")
    print("=" * 50)
    asyncio.run(run_agent())
