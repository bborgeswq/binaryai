"""
Self-Learning Database System
Stores trades, AI decisions, and learns from past performance
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from loguru import logger


@dataclass
class Trade:
    """Represents a completed trade."""
    id: Optional[int] = None
    symbol: str = ""
    side: str = ""  # BUY or SELL
    entry_price: float = 0.0
    exit_price: float = 0.0
    quantity: float = 0.0
    entry_time: str = ""
    exit_time: str = ""
    pnl: float = 0.0
    pnl_percent: float = 0.0
    fees: float = 0.0
    status: str = "open"  # open, closed, cancelled
    strategy: str = ""
    timeframe: str = ""
    indicators_at_entry: str = ""  # JSON string
    indicators_at_exit: str = ""   # JSON string
    notes: str = ""


@dataclass
class AIDecision:
    """Represents an AI trading decision."""
    id: Optional[int] = None
    timestamp: str = ""
    symbol: str = ""
    action: str = ""  # BUY, SELL, HOLD
    confidence: float = 0.0
    reasoning: str = ""
    indicators: str = ""  # JSON string
    patterns_detected: str = ""  # JSON string
    market_context: str = ""
    outcome: str = ""  # win, loss, pending
    outcome_pnl: float = 0.0
    was_executed: bool = False
    trade_id: Optional[int] = None


@dataclass
class LearningInsight:
    """Insights learned from past trades."""
    id: Optional[int] = None
    created_at: str = ""
    insight_type: str = ""  # pattern, indicator, timing, risk
    description: str = ""
    confidence: float = 0.0
    supporting_trades: str = ""  # JSON list of trade IDs
    parameters: str = ""  # JSON string


class TradingDatabase:
    """SQLite database for storing and learning from trades."""

    def __init__(self, db_path: str = "data/trading_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"Trading database initialized at {self.db_path}")

    def _init_database(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                quantity REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                pnl REAL DEFAULT 0,
                pnl_percent REAL DEFAULT 0,
                fees REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                strategy TEXT,
                timeframe TEXT,
                indicators_at_entry TEXT,
                indicators_at_exit TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # AI Decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT,
                indicators TEXT,
                patterns_detected TEXT,
                market_context TEXT,
                outcome TEXT DEFAULT 'pending',
                outcome_pnl REAL DEFAULT 0,
                was_executed INTEGER DEFAULT 0,
                trade_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trade_id) REFERENCES trades(id)
            )
        """)

        # Learning Insights table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                insight_type TEXT NOT NULL,
                description TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                supporting_trades TEXT,
                parameters TEXT
            )
        """)

        # Performance metrics table (daily summaries)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_win REAL DEFAULT 0,
                avg_loss REAL DEFAULT 0,
                best_trade REAL DEFAULT 0,
                worst_trade REAL DEFAULT 0,
                symbols_traded TEXT
            )
        """)

        conn.commit()
        conn.close()

    # ==================== TRADE OPERATIONS ====================

    def add_trade(self, trade: Trade) -> int:
        """Add a new trade to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (
                symbol, side, entry_price, exit_price, quantity,
                entry_time, exit_time, pnl, pnl_percent, fees,
                status, strategy, timeframe, indicators_at_entry,
                indicators_at_exit, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.symbol, trade.side, trade.entry_price, trade.exit_price,
            trade.quantity, trade.entry_time, trade.exit_time, trade.pnl,
            trade.pnl_percent, trade.fees, trade.status, trade.strategy,
            trade.timeframe, trade.indicators_at_entry, trade.indicators_at_exit,
            trade.notes
        ))

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Added trade #{trade_id}: {trade.side} {trade.quantity} {trade.symbol}")
        return trade_id

    def close_trade(self, trade_id: int, exit_price: float, exit_time: str = None,
                    indicators_at_exit: dict = None) -> Trade:
        """Close an open trade and calculate P&L."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get the trade
        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise ValueError(f"Trade {trade_id} not found")

        entry_price = row[3]
        quantity = row[5]
        side = row[2]

        # Calculate P&L
        if side == "BUY":
            pnl = (exit_price - entry_price) * quantity
        else:  # SELL (short)
            pnl = (entry_price - exit_price) * quantity

        pnl_percent = (pnl / (entry_price * quantity)) * 100

        exit_time = exit_time or datetime.now().isoformat()
        indicators_json = json.dumps(indicators_at_exit) if indicators_at_exit else ""

        cursor.execute("""
            UPDATE trades SET
                exit_price = ?,
                exit_time = ?,
                pnl = ?,
                pnl_percent = ?,
                status = 'closed',
                indicators_at_exit = ?
            WHERE id = ?
        """, (exit_price, exit_time, pnl, pnl_percent, indicators_json, trade_id))

        conn.commit()
        conn.close()

        logger.info(f"Closed trade #{trade_id}: P&L = ${pnl:.2f} ({pnl_percent:.2f}%)")

        # Update daily performance
        self._update_daily_performance()

        return self.get_trade(trade_id)

    def get_trade(self, trade_id: int) -> Optional[Trade]:
        """Get a trade by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Trade(
                id=row[0], symbol=row[1], side=row[2], entry_price=row[3],
                exit_price=row[4], quantity=row[5], entry_time=row[6],
                exit_time=row[7], pnl=row[8], pnl_percent=row[9],
                fees=row[10], status=row[11], strategy=row[12],
                timeframe=row[13], indicators_at_entry=row[14],
                indicators_at_exit=row[15], notes=row[16]
            )
        return None

    def get_open_trades(self) -> List[Trade]:
        """Get all open trades."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM trades WHERE status = 'open'")
        rows = cursor.fetchall()
        conn.close()

        return [Trade(
            id=row[0], symbol=row[1], side=row[2], entry_price=row[3],
            exit_price=row[4], quantity=row[5], entry_time=row[6],
            exit_time=row[7], pnl=row[8], pnl_percent=row[9],
            fees=row[10], status=row[11], strategy=row[12],
            timeframe=row[13], indicators_at_entry=row[14],
            indicators_at_exit=row[15], notes=row[16]
        ) for row in rows]

    def get_recent_trades(self, limit: int = 50) -> List[Trade]:
        """Get recent trades."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM trades
            ORDER BY entry_time DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [Trade(
            id=row[0], symbol=row[1], side=row[2], entry_price=row[3],
            exit_price=row[4], quantity=row[5], entry_time=row[6],
            exit_time=row[7], pnl=row[8], pnl_percent=row[9],
            fees=row[10], status=row[11], strategy=row[12],
            timeframe=row[13], indicators_at_entry=row[14],
            indicators_at_exit=row[15], notes=row[16]
        ) for row in rows]

    # ==================== AI DECISION OPERATIONS ====================

    def add_decision(self, decision: AIDecision) -> int:
        """Record an AI decision."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ai_decisions (
                timestamp, symbol, action, confidence, reasoning,
                indicators, patterns_detected, market_context,
                outcome, outcome_pnl, was_executed, trade_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision.timestamp or datetime.now().isoformat(),
            decision.symbol, decision.action, decision.confidence,
            decision.reasoning, decision.indicators, decision.patterns_detected,
            decision.market_context, decision.outcome, decision.outcome_pnl,
            1 if decision.was_executed else 0, decision.trade_id
        ))

        decision_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Recorded AI decision #{decision_id}: {decision.action} {decision.symbol} (confidence: {decision.confidence:.0%})")
        return decision_id

    def update_decision_outcome(self, decision_id: int, outcome: str,
                                 outcome_pnl: float, trade_id: int = None):
        """Update the outcome of a decision after trade closes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE ai_decisions SET
                outcome = ?,
                outcome_pnl = ?,
                trade_id = ?
            WHERE id = ?
        """, (outcome, outcome_pnl, trade_id, decision_id))

        conn.commit()
        conn.close()

        logger.info(f"Updated decision #{decision_id} outcome: {outcome} (${outcome_pnl:.2f})")

    def get_recent_decisions(self, limit: int = 50) -> List[AIDecision]:
        """Get recent AI decisions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM ai_decisions
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [AIDecision(
            id=row[0], timestamp=row[1], symbol=row[2], action=row[3],
            confidence=row[4], reasoning=row[5], indicators=row[6],
            patterns_detected=row[7], market_context=row[8], outcome=row[9],
            outcome_pnl=row[10], was_executed=bool(row[11]), trade_id=row[12]
        ) for row in rows]

    # ==================== LEARNING & ANALYTICS ====================

    def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get performance statistics for the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(pnl) as total_pnl,
                AVG(CASE WHEN pnl > 0 THEN pnl ELSE NULL END) as avg_win,
                AVG(CASE WHEN pnl < 0 THEN pnl ELSE NULL END) as avg_loss,
                MAX(pnl) as best_trade,
                MIN(pnl) as worst_trade
            FROM trades
            WHERE status = 'closed' AND entry_time >= ?
        """, (cutoff_date,))

        row = cursor.fetchone()
        conn.close()

        total = row[0] or 0
        wins = row[1] or 0

        return {
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": row[2] or 0,
            "win_rate": (wins / total * 100) if total > 0 else 0,
            "total_pnl": row[3] or 0,
            "avg_win": row[4] or 0,
            "avg_loss": row[5] or 0,
            "best_trade": row[6] or 0,
            "worst_trade": row[7] or 0,
            "profit_factor": abs(row[4] / row[5]) if row[5] and row[5] != 0 else 0
        }

    def get_symbol_performance(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """Get performance for a specific symbol."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(pnl) as total_pnl,
                AVG(pnl_percent) as avg_pnl_percent
            FROM trades
            WHERE symbol = ? AND status = 'closed' AND entry_time >= ?
        """, (symbol, cutoff_date))

        row = cursor.fetchone()
        conn.close()

        total = row[0] or 0
        wins = row[1] or 0

        return {
            "symbol": symbol,
            "total_trades": total,
            "win_rate": (wins / total * 100) if total > 0 else 0,
            "total_pnl": row[2] or 0,
            "avg_pnl_percent": row[3] or 0
        }

    def get_strategy_performance(self, strategy: str = None) -> List[Dict[str, Any]]:
        """Get performance by strategy."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if strategy:
            cursor.execute("""
                SELECT
                    strategy,
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl) as total_pnl
                FROM trades
                WHERE strategy = ? AND status = 'closed'
                GROUP BY strategy
            """, (strategy,))
        else:
            cursor.execute("""
                SELECT
                    strategy,
                    COUNT(*) as total,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(pnl) as total_pnl
                FROM trades
                WHERE status = 'closed'
                GROUP BY strategy
            """)

        rows = cursor.fetchall()
        conn.close()

        return [{
            "strategy": row[0] or "Unknown",
            "total_trades": row[1],
            "win_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
            "total_pnl": row[3] or 0
        } for row in rows]

    def get_decision_accuracy(self, days: int = 30) -> Dict[str, Any]:
        """Analyze AI decision accuracy."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                action,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                AVG(confidence) as avg_confidence,
                AVG(outcome_pnl) as avg_pnl
            FROM ai_decisions
            WHERE was_executed = 1 AND timestamp >= ? AND outcome != 'pending'
            GROUP BY action
        """, (cutoff_date,))

        rows = cursor.fetchall()
        conn.close()

        results = {}
        for row in rows:
            action = row[0]
            total = row[1]
            wins = row[2]
            results[action] = {
                "total_decisions": total,
                "successful": wins,
                "accuracy": (wins / total * 100) if total > 0 else 0,
                "avg_confidence": row[3] or 0,
                "avg_pnl": row[4] or 0
            }

        return results

    def learn_from_history(self) -> List[LearningInsight]:
        """Analyze trade history and generate learning insights."""
        insights = []

        # Get performance stats
        stats = self.get_performance_stats(days=30)

        # Insight: Overall performance
        if stats["total_trades"] >= 10:
            if stats["win_rate"] < 40:
                insights.append(LearningInsight(
                    insight_type="performance",
                    description=f"Low win rate ({stats['win_rate']:.1f}%). Consider being more selective with entries.",
                    confidence=0.8,
                    parameters=json.dumps({"win_rate": stats["win_rate"]})
                ))
            elif stats["win_rate"] > 60:
                insights.append(LearningInsight(
                    insight_type="performance",
                    description=f"Good win rate ({stats['win_rate']:.1f}%). Current strategy is working well.",
                    confidence=0.8,
                    parameters=json.dumps({"win_rate": stats["win_rate"]})
                ))

        # Analyze by symbol
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT symbol,
                   COUNT(*) as trades,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   SUM(pnl) as total_pnl
            FROM trades
            WHERE status = 'closed'
            GROUP BY symbol
            HAVING trades >= 5
        """)

        for row in cursor.fetchall():
            symbol, trades, wins, total_pnl = row
            win_rate = (wins / trades * 100) if trades > 0 else 0

            if win_rate < 35:
                insights.append(LearningInsight(
                    insight_type="symbol",
                    description=f"Poor performance on {symbol} ({win_rate:.1f}% win rate). Consider avoiding or adjusting strategy.",
                    confidence=0.7,
                    parameters=json.dumps({"symbol": symbol, "win_rate": win_rate, "pnl": total_pnl})
                ))
            elif win_rate > 65:
                insights.append(LearningInsight(
                    insight_type="symbol",
                    description=f"Strong performance on {symbol} ({win_rate:.1f}% win rate). Consider increasing position size.",
                    confidence=0.7,
                    parameters=json.dumps({"symbol": symbol, "win_rate": win_rate, "pnl": total_pnl})
                ))

        conn.close()

        # Save insights to database
        for insight in insights:
            self.add_insight(insight)

        logger.info(f"Generated {len(insights)} learning insights")
        return insights

    def add_insight(self, insight: LearningInsight) -> int:
        """Save a learning insight."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO learning_insights (
                insight_type, description, confidence,
                supporting_trades, parameters
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            insight.insight_type, insight.description, insight.confidence,
            insight.supporting_trades, insight.parameters
        ))

        insight_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return insight_id

    def get_insights(self, limit: int = 20) -> List[LearningInsight]:
        """Get recent learning insights."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM learning_insights
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [LearningInsight(
            id=row[0], created_at=row[1], insight_type=row[2],
            description=row[3], confidence=row[4],
            supporting_trades=row[5], parameters=row[6]
        ) for row in rows]

    def _update_daily_performance(self):
        """Update daily performance summary."""
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl,
                AVG(CASE WHEN pnl > 0 THEN pnl ELSE NULL END) as avg_win,
                AVG(CASE WHEN pnl < 0 THEN pnl ELSE NULL END) as avg_loss,
                MAX(pnl) as best,
                MIN(pnl) as worst,
                GROUP_CONCAT(DISTINCT symbol) as symbols
            FROM trades
            WHERE DATE(exit_time) = ? AND status = 'closed'
        """, (today,))

        row = cursor.fetchone()

        if row and row[0] > 0:
            total = row[0]
            wins = row[1] or 0
            win_rate = (wins / total * 100) if total > 0 else 0

            cursor.execute("""
                INSERT OR REPLACE INTO daily_performance (
                    date, total_trades, winning_trades, losing_trades,
                    total_pnl, win_rate, avg_win, avg_loss,
                    best_trade, worst_trade, symbols_traded
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                today, total, wins, row[2] or 0, row[3] or 0,
                win_rate, row[4] or 0, row[5] or 0,
                row[6] or 0, row[7] or 0, row[8] or ""
            ))

            conn.commit()

        conn.close()

    def get_context_for_ai(self, symbol: str) -> str:
        """Generate context string for AI decision making."""
        stats = self.get_performance_stats(days=7)
        symbol_stats = self.get_symbol_performance(symbol, days=7)
        insights = self.get_insights(limit=5)

        context = f"""
TRADING PERFORMANCE CONTEXT (Last 7 days):
- Total trades: {stats['total_trades']}
- Win rate: {stats['win_rate']:.1f}%
- Total P&L: ${stats['total_pnl']:.2f}
- Average win: ${stats['avg_win']:.2f}
- Average loss: ${stats['avg_loss']:.2f}

{symbol.upper()} SPECIFIC:
- Trades on {symbol}: {symbol_stats['total_trades']}
- Win rate: {symbol_stats['win_rate']:.1f}%
- Total P&L: ${symbol_stats['total_pnl']:.2f}

RECENT INSIGHTS:
"""
        for insight in insights[:3]:
            context += f"- {insight.description}\n"

        return context
