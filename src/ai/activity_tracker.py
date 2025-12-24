"""
AI Activity Tracker
Tracks and visualizes AI decisions, actions, and reasoning in real-time
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import asyncio


class ActivityType(Enum):
    """Types of AI activities."""
    ANALYZING = "analyzing"
    SIGNAL_GENERATED = "signal_generated"
    TRADE_PLACED = "trade_placed"
    TRADE_CLOSED = "trade_closed"
    PATTERN_DETECTED = "pattern_detected"
    NEWS_ANALYZED = "news_analyzed"
    RISK_CHECK = "risk_check"
    LEARNING = "learning"
    THINKING = "thinking"
    MARKER_PLACED = "marker_placed"
    ERROR = "error"


@dataclass
class ChartMarker:
    """A marker to display on the chart."""
    timestamp: datetime
    price: float
    marker_type: str  # "buy", "sell", "signal_buy", "signal_sell", "pattern", "support", "resistance"
    label: str
    color: str
    size: int = 15
    symbol: str = "circle"  # circle, triangle-up, triangle-down, star, diamond
    details: str = ""


@dataclass
class AIActivity:
    """Represents an AI activity/action."""
    id: str
    timestamp: datetime
    activity_type: ActivityType
    symbol: str
    title: str
    description: str
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    markers: List[ChartMarker] = field(default_factory=list)
    is_important: bool = False


class AIActivityTracker:
    """
    Tracks AI activities and provides real-time updates for visualization.
    """

    def __init__(self, max_activities: int = 100):
        self.activities: List[AIActivity] = []
        self.markers: Dict[str, List[ChartMarker]] = {}  # symbol -> markers
        self.max_activities = max_activities
        self._activity_id = 0

        # Callbacks for real-time updates
        self.on_activity: Optional[Callable[[AIActivity], None]] = None
        self.on_marker: Optional[Callable[[str, ChartMarker], None]] = None

        # Current AI state for visualization
        self.current_state = {
            "status": "idle",
            "thinking": "",
            "analyzing_symbol": None,
            "last_signal": None,
            "confidence": 0.0
        }

    def _generate_id(self) -> str:
        """Generate unique activity ID."""
        self._activity_id += 1
        return f"act_{self._activity_id}_{datetime.now().strftime('%H%M%S')}"

    def log_activity(
        self,
        activity_type: ActivityType,
        symbol: str,
        title: str,
        description: str,
        confidence: float = 0.0,
        details: Dict[str, Any] = None,
        markers: List[ChartMarker] = None,
        is_important: bool = False
    ) -> AIActivity:
        """Log a new AI activity."""
        activity = AIActivity(
            id=self._generate_id(),
            timestamp=datetime.now(),
            activity_type=activity_type,
            symbol=symbol,
            title=title,
            description=description,
            confidence=confidence,
            details=details or {},
            markers=markers or [],
            is_important=is_important
        )

        self.activities.append(activity)

        # Trim old activities
        if len(self.activities) > self.max_activities:
            self.activities = self.activities[-self.max_activities:]

        # Add markers to chart
        for marker in activity.markers:
            if symbol not in self.markers:
                self.markers[symbol] = []
            self.markers[symbol].append(marker)

            # Keep only last 50 markers per symbol
            if len(self.markers[symbol]) > 50:
                self.markers[symbol] = self.markers[symbol][-50:]

            # Callback
            if self.on_marker:
                self.on_marker(symbol, marker)

        # Callback
        if self.on_activity:
            self.on_activity(activity)

        logger.info(f"🤖 [{activity_type.value}] {symbol}: {title}")

        return activity

    def log_analyzing(self, symbol: str, indicators: Dict[str, float]) -> AIActivity:
        """Log that AI is analyzing a symbol."""
        self.current_state["status"] = "analyzing"
        self.current_state["analyzing_symbol"] = symbol
        self.current_state["thinking"] = f"Analyzing {symbol} market data..."

        return self.log_activity(
            ActivityType.ANALYZING,
            symbol,
            f"Analyzing {symbol}",
            f"Calculating indicators: RSI={indicators.get('rsi', 0):.1f}, MACD={indicators.get('macd', 0):.2f}",
            details=indicators
        )

    def log_thinking(self, symbol: str, thought: str) -> AIActivity:
        """Log AI thinking process."""
        self.current_state["thinking"] = thought

        return self.log_activity(
            ActivityType.THINKING,
            symbol,
            "AI Thinking",
            thought
        )

    def log_signal(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        price: float,
        reasoning: str,
        indicators: Dict[str, Any]
    ) -> AIActivity:
        """Log a generated signal with chart marker."""
        self.current_state["last_signal"] = {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "price": price,
            "time": datetime.now().isoformat()
        }
        self.current_state["confidence"] = confidence

        # Create marker for chart
        marker = ChartMarker(
            timestamp=datetime.now(),
            price=price,
            marker_type=f"signal_{signal.lower()}",
            label=f"{signal} ({confidence:.0%})",
            color="#00ff88" if signal == "BUY" else "#ff4444" if signal == "SELL" else "#ffff00",
            size=20,
            symbol="triangle-up" if signal == "BUY" else "triangle-down" if signal == "SELL" else "circle",
            details=reasoning
        )

        return self.log_activity(
            ActivityType.SIGNAL_GENERATED,
            symbol,
            f"{'📈' if signal == 'BUY' else '📉' if signal == 'SELL' else '⏸️'} {signal} Signal",
            reasoning,
            confidence=confidence,
            details={"price": price, "indicators": indicators},
            markers=[marker],
            is_important=True
        )

    def log_trade(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        reasoning: str
    ) -> AIActivity:
        """Log a trade execution with chart marker."""
        # Create trade marker
        marker = ChartMarker(
            timestamp=datetime.now(),
            price=price,
            marker_type=side.lower(),
            label=f"{side} @ ${price:,.2f}",
            color="#00ff88" if side == "BUY" else "#ff4444",
            size=25,
            symbol="star",
            details=f"Qty: {quantity} | {reasoning}"
        )

        return self.log_activity(
            ActivityType.TRADE_PLACED,
            symbol,
            f"{'🟢' if side == 'BUY' else '🔴'} Trade Executed: {side}",
            f"{side} {quantity} {symbol} @ ${price:,.2f}",
            details={"side": side, "price": price, "quantity": quantity},
            markers=[marker],
            is_important=True
        )

    def log_trade_closed(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float
    ) -> AIActivity:
        """Log a closed trade with markers."""
        # Exit marker
        marker = ChartMarker(
            timestamp=datetime.now(),
            price=exit_price,
            marker_type="exit",
            label=f"EXIT ${pnl:+,.2f}",
            color="#00ff88" if pnl >= 0 else "#ff4444",
            size=25,
            symbol="diamond",
            details=f"Entry: ${entry_price:,.2f} | P&L: {pnl_pct:+.2f}%"
        )

        return self.log_activity(
            ActivityType.TRADE_CLOSED,
            symbol,
            f"{'✅' if pnl >= 0 else '❌'} Trade Closed: ${pnl:+,.2f}",
            f"Entry: ${entry_price:,.2f} → Exit: ${exit_price:,.2f} | P&L: {pnl_pct:+.2f}%",
            details={"entry": entry_price, "exit": exit_price, "pnl": pnl, "pnl_pct": pnl_pct},
            markers=[marker],
            is_important=True
        )

    def log_pattern(
        self,
        symbol: str,
        pattern_name: str,
        pattern_type: str,
        confidence: float,
        price: float,
        description: str
    ) -> AIActivity:
        """Log a detected pattern."""
        marker = ChartMarker(
            timestamp=datetime.now(),
            price=price,
            marker_type="pattern",
            label=pattern_name,
            color="#9966ff",
            size=18,
            symbol="star",
            details=f"{pattern_type} | {confidence:.0%} confidence"
        )

        return self.log_activity(
            ActivityType.PATTERN_DETECTED,
            symbol,
            f"📊 Pattern: {pattern_name}",
            description,
            confidence=confidence,
            details={"pattern": pattern_name, "type": pattern_type},
            markers=[marker]
        )

    def log_support_resistance(
        self,
        symbol: str,
        level_type: str,
        price: float,
        strength: float
    ) -> AIActivity:
        """Log support/resistance level."""
        marker = ChartMarker(
            timestamp=datetime.now(),
            price=price,
            marker_type=level_type.lower(),
            label=f"{level_type} ${price:,.0f}",
            color="#00d4ff" if level_type == "Support" else "#ff9500",
            size=12,
            symbol="circle",
            details=f"Strength: {strength:.0%}"
        )

        return self.log_activity(
            ActivityType.MARKER_PLACED,
            symbol,
            f"📍 {level_type} Level",
            f"{level_type} at ${price:,.2f} (strength: {strength:.0%})",
            confidence=strength,
            details={"type": level_type, "price": price},
            markers=[marker]
        )

    def log_news_analyzed(
        self,
        symbol: str,
        headline: str,
        sentiment: str,
        impact: str
    ) -> AIActivity:
        """Log news analysis."""
        return self.log_activity(
            ActivityType.NEWS_ANALYZED,
            symbol,
            f"📰 News: {sentiment.capitalize()}",
            headline[:100],
            details={"sentiment": sentiment, "impact": impact}
        )

    def log_risk_check(
        self,
        symbol: str,
        check_type: str,
        passed: bool,
        details: str
    ) -> AIActivity:
        """Log risk management check."""
        return self.log_activity(
            ActivityType.RISK_CHECK,
            symbol,
            f"{'✅' if passed else '⚠️'} Risk: {check_type}",
            details,
            details={"check": check_type, "passed": passed}
        )

    def log_learning(self, insight: str, confidence: float) -> AIActivity:
        """Log AI learning insight."""
        return self.log_activity(
            ActivityType.LEARNING,
            "SYSTEM",
            "🧠 Learning Insight",
            insight,
            confidence=confidence,
            is_important=True
        )

    def log_error(self, symbol: str, error: str) -> AIActivity:
        """Log an error."""
        return self.log_activity(
            ActivityType.ERROR,
            symbol,
            "❌ Error",
            error,
            is_important=True
        )

    def get_recent_activities(self, limit: int = 20, symbol: str = None) -> List[AIActivity]:
        """Get recent activities, optionally filtered by symbol."""
        activities = self.activities
        if symbol:
            activities = [a for a in activities if a.symbol == symbol]
        return list(reversed(activities[-limit:]))

    def get_important_activities(self, limit: int = 10) -> List[AIActivity]:
        """Get important activities (signals, trades, errors)."""
        important = [a for a in self.activities if a.is_important]
        return list(reversed(important[-limit:]))

    def get_markers_for_symbol(self, symbol: str, limit: int = 50) -> List[ChartMarker]:
        """Get chart markers for a symbol."""
        return self.markers.get(symbol, [])[-limit:]

    def get_current_state(self) -> Dict[str, Any]:
        """Get current AI state for UI display."""
        return self.current_state.copy()

    def clear_markers(self, symbol: str = None):
        """Clear markers for a symbol or all symbols."""
        if symbol:
            self.markers[symbol] = []
        else:
            self.markers.clear()

    def to_dict_for_display(self) -> Dict[str, Any]:
        """Get data formatted for UI display."""
        return {
            "state": self.current_state,
            "recent_activities": [
                {
                    "id": a.id,
                    "time": a.timestamp.strftime("%H:%M:%S"),
                    "type": a.activity_type.value,
                    "symbol": a.symbol,
                    "title": a.title,
                    "description": a.description,
                    "confidence": a.confidence,
                    "important": a.is_important
                }
                for a in self.get_recent_activities(20)
            ],
            "markers": {
                symbol: [
                    {
                        "time": m.timestamp.isoformat(),
                        "price": m.price,
                        "type": m.marker_type,
                        "label": m.label,
                        "color": m.color
                    }
                    for m in markers
                ]
                for symbol, markers in self.markers.items()
            }
        }


# Global tracker instance
_tracker: Optional[AIActivityTracker] = None


def get_tracker() -> AIActivityTracker:
    """Get or create the global activity tracker."""
    global _tracker
    if _tracker is None:
        _tracker = AIActivityTracker()
    return _tracker


def reset_tracker():
    """Reset the global tracker."""
    global _tracker
    _tracker = AIActivityTracker()
