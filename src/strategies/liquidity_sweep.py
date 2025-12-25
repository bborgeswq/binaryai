"""
TJR Liquidity Sweep Strategy
Based on The Trading Rush methodology for identifying and trading liquidity sweeps.

Multi-timeframe approach:
- Daily/4H: Overall trend direction
- 1H: Session structure and key levels
- 15m: Liquidity sweep identification
- 5m: Entry confirmation

Entry criteria:
1. Identify liquidity zones (swing highs/lows with multiple touches)
2. Wait for liquidity sweep (price takes out the level)
3. Confirm break of structure in opposite direction
4. Enter on retracement to Order Block or Fair Value Gap
5. Stop loss below/above sweep extreme
6. Take profit at opposite liquidity zone (minimum 2:1 R:R)
"""

import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
from loguru import logger

from src.broker.binance_client import BinanceBroker
from src.broker.base import OrderSide, OrderType
from src.learning.database import TradingDatabase, Trade, AIDecision
from src.ai.activity_tracker import get_tracker, ActivityType


class TrendDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class SwingPoint:
    """Represents a swing high or low."""
    timestamp: datetime
    price: float
    is_high: bool
    strength: int  # Number of candles on each side
    touches: int = 1  # Times price came near this level
    swept: bool = False


@dataclass
class LiquidityZone:
    """A zone where liquidity is likely resting."""
    price_low: float
    price_high: float
    zone_type: str  # "above_highs" or "below_lows"
    swing_points: List[SwingPoint] = field(default_factory=list)
    strength: float = 0.0  # 0-1 strength rating
    created_at: datetime = None
    swept: bool = False
    swept_at: datetime = None


@dataclass
class OrderBlock:
    """Order block (last opposing candle before impulsive move)."""
    timestamp: datetime
    high: float
    low: float
    block_type: str  # "bullish" or "bearish"
    strength: float = 0.0
    mitigated: bool = False


@dataclass
class FairValueGap:
    """Fair Value Gap / Imbalance."""
    timestamp: datetime
    high: float  # Top of gap
    low: float   # Bottom of gap
    gap_type: str  # "bullish" or "bearish"
    filled: bool = False
    fill_percentage: float = 0.0


@dataclass
class TradeSetup:
    """A complete trade setup."""
    symbol: str
    signal: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence: float
    reasoning: str
    timeframe: str
    setup_type: str  # "liquidity_sweep", "order_block", "fvg"
    order_block: Optional[OrderBlock] = None
    fvg: Optional[FairValueGap] = None
    liquidity_zone: Optional[LiquidityZone] = None
    created_at: datetime = None


class LiquiditySweepStrategy:
    """
    TJR-style liquidity sweep trading strategy.
    Identifies liquidity zones, waits for sweeps, and enters on confirmation.
    """

    def __init__(
        self,
        broker: BinanceBroker,
        symbols: List[str] = None,
        risk_per_trade: float = 0.07,  # 7% risk
        min_rr: float = 2.0,           # Minimum 2:1 R:R
        account_size: float = 10000.0
    ):
        self.broker = broker
        self.symbols = symbols or ["BTC/USDT", "ETH/USDT", "XRP/USDT"]
        self.risk_per_trade = risk_per_trade
        self.min_rr = min_rr
        self.account_size = account_size

        self.db = TradingDatabase()
        self.tracker = get_tracker()

        # Timeframes for multi-timeframe analysis
        self.timeframes = {
            "trend": "4h",      # Overall trend
            "structure": "1h",  # Market structure
            "sweep": "15m",     # Sweep identification
            "entry": "5m"       # Entry confirmation
        }

        # Cache for market data
        self.candle_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.swing_points: Dict[str, List[SwingPoint]] = {}
        self.liquidity_zones: Dict[str, List[LiquidityZone]] = {}
        self.order_blocks: Dict[str, List[OrderBlock]] = {}
        self.fvgs: Dict[str, List[FairValueGap]] = {}

        # Strategy state
        self.active_setups: Dict[str, TradeSetup] = {}
        self.pending_entries: Dict[str, TradeSetup] = {}

        # Parameters for detection
        self.swing_lookback = 5  # Candles on each side for swing detection
        self.liquidity_zone_tolerance = 0.001  # 0.1% tolerance for zone clustering
        self.ob_min_move = 0.005  # 0.5% minimum move after OB
        self.fvg_min_size = 0.001  # 0.1% minimum gap size

        logger.info(f"LiquiditySweepStrategy initialized for {self.symbols}")
        logger.info(f"Risk per trade: {self.risk_per_trade*100}%, Min R:R: {self.min_rr}")

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """Fetch OHLCV data and convert to DataFrame."""
        try:
            ohlcv = await self.broker.get_ohlcv(symbol, timeframe, limit)

            if not ohlcv:
                logger.warning(f"No candle data for {symbol} {timeframe}")
                return pd.DataFrame()

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Cache the data
            if symbol not in self.candle_cache:
                self.candle_cache[symbol] = {}
            self.candle_cache[symbol][timeframe] = df

            return df

        except Exception as e:
            logger.error(f"Error fetching candles for {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def detect_swing_points(self, df: pd.DataFrame, lookback: int = 5) -> List[SwingPoint]:
        """Detect swing highs and lows."""
        swings = []

        if len(df) < lookback * 2 + 1:
            return swings

        highs = df['high'].values
        lows = df['low'].values
        timestamps = df.index

        for i in range(lookback, len(df) - lookback):
            # Check for swing high
            is_swing_high = True
            for j in range(1, lookback + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_swing_high = False
                    break

            if is_swing_high:
                swings.append(SwingPoint(
                    timestamp=timestamps[i],
                    price=highs[i],
                    is_high=True,
                    strength=lookback
                ))

            # Check for swing low
            is_swing_low = True
            for j in range(1, lookback + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_swing_low = False
                    break

            if is_swing_low:
                swings.append(SwingPoint(
                    timestamp=timestamps[i],
                    price=lows[i],
                    is_high=False,
                    strength=lookback
                ))

        return swings

    def identify_liquidity_zones(self, swings: List[SwingPoint], current_price: float) -> List[LiquidityZone]:
        """Cluster swing points into liquidity zones."""
        zones = []

        if not swings:
            return zones

        # Separate highs and lows
        swing_highs = [s for s in swings if s.is_high]
        swing_lows = [s for s in swings if not s.is_high]

        # Cluster swing highs (liquidity above)
        if swing_highs:
            zones.extend(self._cluster_swings(swing_highs, "above_highs", current_price))

        # Cluster swing lows (liquidity below)
        if swing_lows:
            zones.extend(self._cluster_swings(swing_lows, "below_lows", current_price))

        # Sort by strength
        zones.sort(key=lambda z: z.strength, reverse=True)

        return zones

    def _cluster_swings(self, swings: List[SwingPoint], zone_type: str, current_price: float) -> List[LiquidityZone]:
        """Cluster nearby swing points into zones."""
        zones = []
        tolerance = current_price * self.liquidity_zone_tolerance

        used = set()

        for i, swing in enumerate(swings):
            if i in used:
                continue

            cluster = [swing]
            used.add(i)

            for j, other in enumerate(swings):
                if j in used:
                    continue
                if abs(swing.price - other.price) <= tolerance:
                    cluster.append(other)
                    used.add(j)

            if cluster:
                prices = [s.price for s in cluster]
                zone = LiquidityZone(
                    price_low=min(prices) - tolerance * 0.5,
                    price_high=max(prices) + tolerance * 0.5,
                    zone_type=zone_type,
                    swing_points=cluster,
                    strength=len(cluster) / 10.0,  # Normalize strength
                    created_at=min(s.timestamp for s in cluster)
                )
                zones.append(zone)

        return zones

    def detect_sweep(self, df: pd.DataFrame, zone: LiquidityZone) -> Tuple[bool, Optional[datetime]]:
        """Check if a liquidity zone has been swept."""
        if zone.swept:
            return True, zone.swept_at

        recent_candles = df.tail(10)

        for idx, row in recent_candles.iterrows():
            if zone.zone_type == "above_highs":
                # Sweep above highs: price goes above zone then closes below
                if row['high'] > zone.price_high and row['close'] < zone.price_high:
                    return True, idx
            else:
                # Sweep below lows: price goes below zone then closes above
                if row['low'] < zone.price_low and row['close'] > zone.price_low:
                    return True, idx

        return False, None

    def detect_order_blocks(self, df: pd.DataFrame, lookback: int = 50) -> List[OrderBlock]:
        """Detect order blocks (last opposing candle before impulsive move)."""
        blocks = []

        if len(df) < lookback:
            return blocks

        recent = df.tail(lookback)

        for i in range(2, len(recent) - 1):
            current = recent.iloc[i]
            prev = recent.iloc[i - 1]
            next_candle = recent.iloc[i + 1]

            # Calculate move size
            move_size = abs(next_candle['close'] - current['close']) / current['close']

            if move_size < self.ob_min_move:
                continue

            # Bullish OB: bearish candle followed by strong bullish move
            if current['close'] < current['open'] and next_candle['close'] > current['high']:
                blocks.append(OrderBlock(
                    timestamp=recent.index[i],
                    high=current['high'],
                    low=current['low'],
                    block_type="bullish",
                    strength=move_size
                ))

            # Bearish OB: bullish candle followed by strong bearish move
            elif current['close'] > current['open'] and next_candle['close'] < current['low']:
                blocks.append(OrderBlock(
                    timestamp=recent.index[i],
                    high=current['high'],
                    low=current['low'],
                    block_type="bearish",
                    strength=move_size
                ))

        return blocks

    def detect_fvgs(self, df: pd.DataFrame, lookback: int = 50) -> List[FairValueGap]:
        """Detect Fair Value Gaps (imbalances)."""
        fvgs = []

        if len(df) < lookback:
            return fvgs

        recent = df.tail(lookback)

        for i in range(2, len(recent)):
            candle1 = recent.iloc[i - 2]
            candle2 = recent.iloc[i - 1]  # Middle candle (gap creator)
            candle3 = recent.iloc[i]

            # Bullish FVG: candle3 low > candle1 high
            if candle3['low'] > candle1['high']:
                gap_size = (candle3['low'] - candle1['high']) / candle1['high']
                if gap_size >= self.fvg_min_size:
                    fvgs.append(FairValueGap(
                        timestamp=recent.index[i - 1],
                        high=candle3['low'],
                        low=candle1['high'],
                        gap_type="bullish"
                    ))

            # Bearish FVG: candle3 high < candle1 low
            elif candle3['high'] < candle1['low']:
                gap_size = (candle1['low'] - candle3['high']) / candle1['low']
                if gap_size >= self.fvg_min_size:
                    fvgs.append(FairValueGap(
                        timestamp=recent.index[i - 1],
                        high=candle1['low'],
                        low=candle3['high'],
                        gap_type="bearish"
                    ))

        return fvgs

    def detect_break_of_structure(self, df: pd.DataFrame, direction: str) -> bool:
        """Detect break of structure in the given direction."""
        if len(df) < 20:
            return False

        recent = df.tail(20)
        swings = self.detect_swing_points(recent, lookback=3)

        if len(swings) < 2:
            return False

        # Get recent swing highs and lows
        recent_highs = [s for s in swings if s.is_high][-3:]
        recent_lows = [s for s in swings if not s.is_high][-3:]

        current_close = recent.iloc[-1]['close']

        if direction == "bullish":
            # Break of structure up: close above recent swing high
            if recent_highs:
                highest = max(s.price for s in recent_highs)
                return current_close > highest
        else:
            # Break of structure down: close below recent swing low
            if recent_lows:
                lowest = min(s.price for s in recent_lows)
                return current_close < lowest

        return False

    def get_trend_direction(self, df: pd.DataFrame) -> TrendDirection:
        """Determine overall trend direction from higher timeframe."""
        if len(df) < 50:
            return TrendDirection.NEUTRAL

        # Use EMA 20 and 50 for trend
        ema20 = df['close'].ewm(span=20).mean()
        ema50 = df['close'].ewm(span=50).mean()

        current_ema20 = ema20.iloc[-1]
        current_ema50 = ema50.iloc[-1]
        current_price = df['close'].iloc[-1]

        # Strong trend: price and EMAs aligned
        if current_price > current_ema20 > current_ema50:
            return TrendDirection.BULLISH
        elif current_price < current_ema20 < current_ema50:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.NEUTRAL

    async def analyze_symbol(self, symbol: str) -> Optional[TradeSetup]:
        """Perform full multi-timeframe analysis on a symbol."""
        self.tracker.log_thinking(symbol, f"Starting multi-timeframe analysis for {symbol}")

        # Fetch data for all timeframes
        df_trend = await self.fetch_candles(symbol, self.timeframes["trend"], 100)
        df_structure = await self.fetch_candles(symbol, self.timeframes["structure"], 100)
        df_sweep = await self.fetch_candles(symbol, self.timeframes["sweep"], 200)
        df_entry = await self.fetch_candles(symbol, self.timeframes["entry"], 100)

        if df_sweep.empty or df_entry.empty:
            logger.warning(f"Insufficient data for {symbol}")
            return None

        current_price = df_entry['close'].iloc[-1]

        # Step 1: Determine trend direction
        trend = self.get_trend_direction(df_trend) if not df_trend.empty else TrendDirection.NEUTRAL
        self.tracker.log_thinking(symbol, f"Trend direction: {trend.value}")

        # Step 2: Detect swing points and liquidity zones
        swings = self.detect_swing_points(df_sweep, self.swing_lookback)
        self.swing_points[symbol] = swings

        zones = self.identify_liquidity_zones(swings, current_price)
        self.liquidity_zones[symbol] = zones

        self.tracker.log_thinking(symbol, f"Found {len(zones)} liquidity zones")

        # Step 3: Check for recent liquidity sweeps
        swept_zones = []
        for zone in zones:
            swept, sweep_time = self.detect_sweep(df_sweep, zone)
            if swept and sweep_time:
                zone.swept = True
                zone.swept_at = sweep_time
                swept_zones.append(zone)

        if not swept_zones:
            self.tracker.log_thinking(symbol, "No recent liquidity sweeps detected")
            return None

        self.tracker.log_thinking(symbol, f"Found {len(swept_zones)} swept liquidity zones")

        # Step 4: Check for break of structure after sweep
        for swept_zone in swept_zones:
            # Determine expected direction after sweep
            expected_direction = "bullish" if swept_zone.zone_type == "below_lows" else "bearish"

            # Only trade with the trend
            if trend != TrendDirection.NEUTRAL:
                if expected_direction == "bullish" and trend == TrendDirection.BEARISH:
                    continue
                if expected_direction == "bearish" and trend == TrendDirection.BULLISH:
                    continue

            bos = self.detect_break_of_structure(df_entry, expected_direction)

            if not bos:
                self.tracker.log_thinking(symbol, f"No break of structure for {expected_direction} setup")
                continue

            self.tracker.log_thinking(symbol, f"Break of structure confirmed for {expected_direction}")

            # Step 5: Find Order Block or FVG for entry
            order_blocks = self.detect_order_blocks(df_entry)
            fvgs = self.detect_fvgs(df_entry)

            self.order_blocks[symbol] = order_blocks
            self.fvgs[symbol] = fvgs

            # Find valid entry zone
            entry_zone = None
            entry_type = None

            # Prefer Order Block
            valid_obs = [ob for ob in order_blocks if ob.block_type == expected_direction and not ob.mitigated]
            if valid_obs:
                entry_zone = valid_obs[-1]  # Most recent
                entry_type = "order_block"

            # Fallback to FVG
            if not entry_zone:
                valid_fvgs = [fvg for fvg in fvgs if fvg.gap_type == expected_direction and not fvg.filled]
                if valid_fvgs:
                    entry_zone = valid_fvgs[-1]
                    entry_type = "fvg"

            if not entry_zone:
                self.tracker.log_thinking(symbol, "No valid entry zone (OB/FVG) found")
                continue

            # Step 6: Calculate trade parameters
            setup = self._calculate_trade_setup(
                symbol=symbol,
                direction=expected_direction,
                current_price=current_price,
                swept_zone=swept_zone,
                entry_zone=entry_zone,
                entry_type=entry_type,
                trend=trend
            )

            if setup and setup.risk_reward >= self.min_rr:
                self.tracker.log_activity(
                    ActivityType.SIGNAL_GENERATED,
                    symbol,
                    f"Trade Setup: {setup.signal.value}",
                    setup.reasoning,
                    confidence=setup.confidence,
                    is_important=True
                )
                return setup
            elif setup:
                self.tracker.log_thinking(symbol, f"Setup rejected: R:R {setup.risk_reward:.2f} < {self.min_rr}")

        return None

    def _calculate_trade_setup(
        self,
        symbol: str,
        direction: str,
        current_price: float,
        swept_zone: LiquidityZone,
        entry_zone: Any,
        entry_type: str,
        trend: TrendDirection
    ) -> Optional[TradeSetup]:
        """Calculate complete trade setup with entry, SL, TP."""

        # Determine entry price based on entry zone type
        if entry_type == "order_block":
            if direction == "bullish":
                entry_price = (entry_zone.high + entry_zone.low) / 2
                stop_loss = entry_zone.low * 0.998  # Slightly below OB
            else:
                entry_price = (entry_zone.high + entry_zone.low) / 2
                stop_loss = entry_zone.high * 1.002  # Slightly above OB
        else:  # FVG
            if direction == "bullish":
                entry_price = (entry_zone.high + entry_zone.low) / 2
                stop_loss = entry_zone.low * 0.998
            else:
                entry_price = (entry_zone.high + entry_zone.low) / 2
                stop_loss = entry_zone.high * 1.002

        # Calculate risk in price terms
        risk_amount = abs(entry_price - stop_loss)

        # Find opposite liquidity zone for take profit
        opposite_zones = [z for z in self.liquidity_zones.get(symbol, [])
                        if z.zone_type != swept_zone.zone_type and not z.swept]

        if opposite_zones:
            if direction == "bullish":
                # Target highest liquidity above
                target_zone = max(opposite_zones, key=lambda z: z.price_high)
                take_profit = target_zone.price_low
            else:
                # Target lowest liquidity below
                target_zone = min(opposite_zones, key=lambda z: z.price_low)
                take_profit = target_zone.price_high
        else:
            # Default to 2.5:1 R:R if no opposite zone found
            if direction == "bullish":
                take_profit = entry_price + (risk_amount * 2.5)
            else:
                take_profit = entry_price - (risk_amount * 2.5)

        # Calculate risk:reward
        reward_amount = abs(take_profit - entry_price)
        risk_reward = reward_amount / risk_amount if risk_amount > 0 else 0

        # Calculate confidence
        confidence = self._calculate_confidence(
            trend=trend,
            direction=direction,
            swept_zone=swept_zone,
            entry_type=entry_type,
            risk_reward=risk_reward
        )

        # Build reasoning
        reasoning = self._build_reasoning(
            direction=direction,
            trend=trend,
            swept_zone=swept_zone,
            entry_type=entry_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward
        )

        return TradeSetup(
            symbol=symbol,
            signal=SignalType.BUY if direction == "bullish" else SignalType.SELL,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            confidence=confidence,
            reasoning=reasoning,
            timeframe=self.timeframes["entry"],
            setup_type=f"liquidity_sweep_{entry_type}",
            order_block=entry_zone if entry_type == "order_block" else None,
            fvg=entry_zone if entry_type == "fvg" else None,
            liquidity_zone=swept_zone,
            created_at=datetime.now()
        )

    def _calculate_confidence(
        self,
        trend: TrendDirection,
        direction: str,
        swept_zone: LiquidityZone,
        entry_type: str,
        risk_reward: float
    ) -> float:
        """Calculate confidence score 0-1."""
        confidence = 0.5

        # Trend alignment (+20%)
        if trend == TrendDirection.BULLISH and direction == "bullish":
            confidence += 0.2
        elif trend == TrendDirection.BEARISH and direction == "bearish":
            confidence += 0.2

        # Strong liquidity zone (+15%)
        if swept_zone.strength > 0.3:
            confidence += 0.15

        # Order block preferred over FVG (+10%)
        if entry_type == "order_block":
            confidence += 0.1

        # Good R:R (+15%)
        if risk_reward >= 3:
            confidence += 0.15
        elif risk_reward >= 2.5:
            confidence += 0.1

        return min(confidence, 0.95)

    def _build_reasoning(
        self,
        direction: str,
        trend: TrendDirection,
        swept_zone: LiquidityZone,
        entry_type: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_reward: float
    ) -> str:
        """Build human-readable reasoning for the trade."""
        zone_desc = "swing lows" if swept_zone.zone_type == "below_lows" else "swing highs"
        trend_alignment = "with trend" if (
            (trend == TrendDirection.BULLISH and direction == "bullish") or
            (trend == TrendDirection.BEARISH and direction == "bearish")
        ) else "counter-trend"

        entry_desc = "Order Block" if entry_type == "order_block" else "Fair Value Gap"

        return (
            f"Liquidity sweep detected at {zone_desc} (strength: {swept_zone.strength:.0%}). "
            f"Break of structure confirms {direction} reversal ({trend_alignment}). "
            f"Entry at {entry_desc}. "
            f"Entry: ${entry_price:,.2f}, SL: ${stop_loss:,.2f}, TP: ${take_profit:,.2f}. "
            f"Risk:Reward = 1:{risk_reward:.1f}"
        )

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk parameters."""
        risk_amount = self.account_size * self.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit == 0:
            return 0

        position_size = risk_amount / risk_per_unit

        # Convert to asset quantity
        quantity = position_size / entry_price

        return quantity

    async def execute_trade(self, setup: TradeSetup) -> Optional[Trade]:
        """Execute a trade based on the setup."""
        try:
            quantity = self.calculate_position_size(setup.entry_price, setup.stop_loss)

            if quantity <= 0:
                logger.warning(f"Invalid position size for {setup.symbol}")
                return None

            self.tracker.log_activity(
                ActivityType.TRADE_PLACED,
                setup.symbol,
                f"Executing {setup.signal.value}",
                f"Quantity: {quantity:.6f} at ${setup.entry_price:,.2f}",
                is_important=True
            )

            # Submit market order
            side = OrderSide.BUY if setup.signal == SignalType.BUY else OrderSide.SELL

            order = await self.broker.submit_order(
                symbol=setup.symbol,
                side=side,
                quantity=Decimal(str(quantity)),
                order_type=OrderType.MARKET
            )

            if order:
                # Record trade in database
                trade = Trade(
                    symbol=setup.symbol,
                    side=setup.signal.value,
                    entry_price=float(order.filled_avg_price or setup.entry_price),
                    quantity=float(quantity),
                    entry_time=datetime.now().isoformat(),
                    status="open",
                    strategy="TJR_LiquiditySweep",
                    timeframe=setup.timeframe,
                    indicators_at_entry=setup.reasoning,
                    notes=f"SL: {setup.stop_loss}, TP: {setup.take_profit}, R:R: {setup.risk_reward:.2f}"
                )

                trade_id = self.db.add_trade(trade)
                trade.id = trade_id

                # Record AI decision
                decision = AIDecision(
                    timestamp=datetime.now().isoformat(),
                    symbol=setup.symbol,
                    action=setup.signal.value,
                    confidence=setup.confidence,
                    reasoning=setup.reasoning,
                    patterns_detected=setup.setup_type,
                    market_context=f"Trend: {self.get_trend_direction(self.candle_cache.get(setup.symbol, {}).get(self.timeframes['trend'], pd.DataFrame())).value}",
                    was_executed=True,
                    trade_id=trade_id
                )
                self.db.add_decision(decision)

                # Track active setup for exit management
                self.active_setups[setup.symbol] = setup

                logger.info(f"Trade executed: {setup.signal.value} {quantity:.6f} {setup.symbol}")

                return trade

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            self.tracker.log_activity(
                ActivityType.ERROR,
                setup.symbol,
                "Trade Execution Failed",
                str(e),
                is_important=True
            )

        return None

    async def check_exit_conditions(self, symbol: str) -> Optional[str]:
        """Check if position should be closed (hit SL or TP)."""
        if symbol not in self.active_setups:
            return None

        setup = self.active_setups[symbol]

        try:
            ticker = await self.broker.get_ticker(symbol)
            current_price = ticker.get('last', 0)

            if not current_price:
                return None

            # Check stop loss
            if setup.signal == SignalType.BUY:
                if current_price <= setup.stop_loss:
                    return "stop_loss"
                if current_price >= setup.take_profit:
                    return "take_profit"
            else:
                if current_price >= setup.stop_loss:
                    return "stop_loss"
                if current_price <= setup.take_profit:
                    return "take_profit"

        except Exception as e:
            logger.error(f"Error checking exit for {symbol}: {e}")

        return None

    async def close_position(self, symbol: str, exit_reason: str) -> Optional[Trade]:
        """Close an open position."""
        try:
            position = await self.broker.get_position(symbol)

            if not position:
                logger.warning(f"No position to close for {symbol}")
                return None

            order = await self.broker.close_position(symbol)

            if order and order.filled_avg_price:
                # Update trade in database
                setup = self.active_setups.get(symbol)
                open_trades = self.db.get_open_trades()

                for trade in open_trades:
                    if trade.symbol == symbol:
                        closed_trade = self.db.close_trade(
                            trade.id,
                            float(order.filled_avg_price),
                            datetime.now().isoformat()
                        )

                        # Log the closure
                        pnl = closed_trade.pnl
                        self.tracker.log_activity(
                            ActivityType.TRADE_CLOSED,
                            symbol,
                            f"Position Closed ({exit_reason})",
                            f"P&L: ${pnl:.2f} ({closed_trade.pnl_percent:.2f}%)",
                            is_important=True
                        )

                        # Remove from active setups
                        if symbol in self.active_setups:
                            del self.active_setups[symbol]

                        return closed_trade

        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")

        return None

    async def run_analysis_loop(self, interval_seconds: int = 60):
        """Main loop for continuous market analysis."""
        logger.info("Starting TJR Liquidity Sweep analysis loop")

        while True:
            try:
                for symbol in self.symbols:
                    # Check exit conditions for open positions
                    exit_reason = await self.check_exit_conditions(symbol)
                    if exit_reason:
                        await self.close_position(symbol, exit_reason)
                        continue

                    # Skip if we already have an active position
                    if symbol in self.active_setups:
                        continue

                    # Analyze for new setups
                    setup = await self.analyze_symbol(symbol)

                    if setup:
                        logger.info(f"Valid setup found for {symbol}: {setup.signal.value}")

                        # Auto-execute the trade
                        await self.execute_trade(setup)

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
                await asyncio.sleep(10)

    def get_status(self) -> Dict[str, Any]:
        """Get current strategy status."""
        return {
            "active": True,
            "symbols": self.symbols,
            "risk_per_trade": self.risk_per_trade,
            "min_rr": self.min_rr,
            "active_setups": {
                symbol: {
                    "signal": setup.signal.value,
                    "entry": setup.entry_price,
                    "stop_loss": setup.stop_loss,
                    "take_profit": setup.take_profit,
                    "rr": setup.risk_reward
                }
                for symbol, setup in self.active_setups.items()
            },
            "liquidity_zones": {
                symbol: len(zones)
                for symbol, zones in self.liquidity_zones.items()
            },
            "order_blocks": {
                symbol: len(blocks)
                for symbol, blocks in self.order_blocks.items()
            }
        }
