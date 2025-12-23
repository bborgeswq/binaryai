"""
AI Decision Engine
Combines all analysis methods to make final trading decisions
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from decimal import Decimal
from loguru import logger

from src.analysis.signals import Signal, SignalType, SignalGenerator
from src.analysis.technical import TechnicalAnalyzer, TechnicalAnalysisResult
from src.analysis.patterns import PatternRecognizer, Pattern
from .llm_analyzer import LLMAnalyzer, MarketAnalysis


class DecisionAction(Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    HOLD = "hold"
    WAIT = "wait"


@dataclass
class TradingDecision:
    """Final trading decision with all supporting data"""
    symbol: str
    action: DecisionAction
    confidence: float
    timestamp: datetime

    # Trade parameters (if action is buy/sell)
    quantity: Optional[Decimal] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    # Analysis data
    technical_signal: Optional[str] = None
    patterns_detected: List[str] = field(default_factory=list)
    llm_sentiment: Optional[str] = None

    # Reasoning
    primary_reasons: List[str] = field(default_factory=list)
    supporting_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)

    # Scores
    technical_score: float = 0.0
    pattern_score: float = 0.0
    llm_score: float = 0.0
    final_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "confidence": self.confidence,
            "timestamp": str(self.timestamp),
            "quantity": float(self.quantity) if self.quantity else None,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "technical_signal": self.technical_signal,
            "patterns_detected": self.patterns_detected,
            "llm_sentiment": self.llm_sentiment,
            "primary_reasons": self.primary_reasons,
            "supporting_factors": self.supporting_factors,
            "risk_factors": self.risk_factors,
            "scores": {
                "technical": self.technical_score,
                "pattern": self.pattern_score,
                "llm": self.llm_score,
                "final": self.final_score
            }
        }

    @property
    def is_actionable(self) -> bool:
        """Check if decision should result in a trade."""
        return self.action in [DecisionAction.BUY, DecisionAction.SELL]

    @property
    def is_exit(self) -> bool:
        """Check if decision is to exit a position."""
        return self.action in [DecisionAction.CLOSE_LONG, DecisionAction.CLOSE_SHORT]


class DecisionEngine:
    """
    Main decision engine that combines all analysis methods.
    Makes final trading decisions based on multiple signals.
    """

    def __init__(
            self,
            technical_analyzer: Optional[TechnicalAnalyzer] = None,
            pattern_recognizer: Optional[PatternRecognizer] = None,
            signal_generator: Optional[SignalGenerator] = None,
            llm_analyzer: Optional[LLMAnalyzer] = None,
            min_confidence: float = 0.65,
            use_llm: bool = True,
            weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize decision engine.

        Args:
            technical_analyzer: Technical analysis engine
            pattern_recognizer: Pattern recognition engine
            signal_generator: Signal generator
            llm_analyzer: LLM analyzer for AI insights
            min_confidence: Minimum confidence to make a decision
            use_llm: Whether to use LLM analysis
            weights: Custom weights for different analysis methods
        """
        self.ta = technical_analyzer or TechnicalAnalyzer()
        self.pr = pattern_recognizer or PatternRecognizer()
        self.sg = signal_generator or SignalGenerator(self.ta, self.pr)
        self.llm = llm_analyzer
        self.min_confidence = min_confidence
        self.use_llm = use_llm and llm_analyzer is not None

        # Weights for combining signals
        self.weights = weights or {
            "technical": 0.4,
            "patterns": 0.25,
            "llm": 0.35
        }

        logger.info(f"Decision Engine initialized (LLM: {self.use_llm})")

    async def make_decision(
            self,
            df,  # pd.DataFrame
            symbol: str,
            timeframe: str = "1h",
            current_position: Optional[Dict[str, Any]] = None,
            portfolio_value: Optional[Decimal] = None,
            max_position_pct: float = 0.1
    ) -> TradingDecision:
        """
        Make a trading decision for a symbol.

        Args:
            df: OHLCV DataFrame
            symbol: Trading symbol
            timeframe: Data timeframe
            current_position: Current position info if any
            portfolio_value: Total portfolio value
            max_position_pct: Max position size as % of portfolio

        Returns:
            TradingDecision with action and reasoning
        """
        timestamp = datetime.now()
        current_price = float(df["close"].iloc[-1]) if not df.empty else 0

        # Step 1: Technical Analysis
        ta_result = self.ta.analyze(df, symbol, timeframe)
        technical_score = self._score_technical(ta_result)

        # Step 2: Pattern Recognition
        patterns = self.pr.find_all_patterns(df)
        pattern_score = self._score_patterns(patterns)

        # Step 3: Generate Signal
        signal = self.sg.generate_signal(df, symbol, timeframe)

        # Step 4: LLM Analysis (optional)
        llm_analysis = None
        llm_score = 0.5  # Neutral default
        if self.use_llm and self.llm:
            try:
                llm_analysis = await self.llm.analyze_market(
                    symbol=symbol,
                    technical_data=ta_result.to_dict(),
                    patterns=[p.to_dict() for p in patterns],
                    signal=signal.to_dict()
                )
                llm_score = self._score_llm(llm_analysis)
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}")

        # Step 5: Combine Scores
        final_score = self._combine_scores(technical_score, pattern_score, llm_score)

        # Step 6: Determine Action
        action, confidence = self._determine_action(
            final_score, signal, ta_result, patterns, llm_analysis, current_position
        )

        # Step 7: Calculate Trade Parameters
        quantity = None
        entry_price = None
        stop_loss = None
        take_profit = None

        if action in [DecisionAction.BUY, DecisionAction.SELL]:
            entry_price = current_price
            stop_loss = signal.suggested_stop_loss
            take_profit = signal.suggested_take_profit

            if portfolio_value:
                # Calculate position size based on risk
                risk_per_trade = portfolio_value * Decimal("0.02")  # 2% risk
                if stop_loss:
                    price_risk = abs(Decimal(str(current_price)) - Decimal(str(stop_loss)))
                    if price_risk > 0:
                        quantity = min(
                            risk_per_trade / price_risk,
                            portfolio_value * Decimal(str(max_position_pct)) / Decimal(str(current_price))
                        )

        # Step 8: Compile Reasoning
        primary_reasons = self._get_primary_reasons(signal, ta_result, patterns, llm_analysis)
        supporting_factors = self._get_supporting_factors(ta_result, patterns)
        risk_factors = self._get_risk_factors(signal, ta_result, llm_analysis)

        return TradingDecision(
            symbol=symbol,
            action=action,
            confidence=confidence,
            timestamp=timestamp,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            technical_signal=ta_result.overall_signal,
            patterns_detected=[p.pattern_type.value for p in patterns],
            llm_sentiment=llm_analysis.sentiment if llm_analysis else None,
            primary_reasons=primary_reasons,
            supporting_factors=supporting_factors,
            risk_factors=risk_factors,
            technical_score=technical_score,
            pattern_score=pattern_score,
            llm_score=llm_score,
            final_score=final_score
        )

    def _score_technical(self, ta_result: TechnicalAnalysisResult) -> float:
        """Score technical analysis result (0-1, 0.5 = neutral)."""
        signal_scores = {
            "strong_buy": 0.9,
            "buy": 0.7,
            "neutral": 0.5,
            "sell": 0.3,
            "strong_sell": 0.1
        }
        base_score = signal_scores.get(ta_result.overall_signal, 0.5)

        # Adjust for confidence
        adjusted = 0.5 + (base_score - 0.5) * ta_result.confidence

        return adjusted

    def _score_patterns(self, patterns: List[Pattern]) -> float:
        """Score patterns (0-1, 0.5 = neutral)."""
        if not patterns:
            return 0.5

        bullish_strength = sum(p.strength for p in patterns if p.signal == "bullish")
        bearish_strength = sum(p.strength for p in patterns if p.signal == "bearish")

        net_strength = bullish_strength - bearish_strength
        max_possible = len(patterns)  # Max 1.0 per pattern

        # Normalize to 0-1 range with 0.5 as neutral
        if max_possible > 0:
            normalized = net_strength / max_possible
            return 0.5 + (normalized * 0.4)  # Scale to 0.1-0.9 range

        return 0.5

    def _score_llm(self, analysis: MarketAnalysis) -> float:
        """Score LLM analysis (0-1, 0.5 = neutral)."""
        sentiment_scores = {
            "bullish": 0.75,
            "bearish": 0.25,
            "neutral": 0.5
        }
        action_scores = {
            "buy": 0.8,
            "sell": 0.2,
            "hold": 0.5,
            "wait": 0.5
        }

        sentiment_score = sentiment_scores.get(analysis.sentiment, 0.5)
        action_score = action_scores.get(analysis.recommended_action, 0.5)

        # Combine sentiment and action, weighted by confidence
        combined = (sentiment_score + action_score) / 2
        adjusted = 0.5 + (combined - 0.5) * analysis.confidence

        return adjusted

    def _combine_scores(
            self,
            technical: float,
            patterns: float,
            llm: float
    ) -> float:
        """Combine all scores using weights."""
        if self.use_llm:
            return (
                    technical * self.weights["technical"] +
                    patterns * self.weights["patterns"] +
                    llm * self.weights["llm"]
            )
        else:
            # Redistribute LLM weight to technical if LLM not used
            tech_weight = self.weights["technical"] + self.weights["llm"] * 0.6
            pattern_weight = self.weights["patterns"] + self.weights["llm"] * 0.4
            return technical * tech_weight + patterns * pattern_weight

    def _determine_action(
            self,
            final_score: float,
            signal: Signal,
            ta_result: TechnicalAnalysisResult,
            patterns: List[Pattern],
            llm_analysis: Optional[MarketAnalysis],
            current_position: Optional[Dict[str, Any]]
    ) -> tuple:
        """Determine action based on scores and current position."""
        # Check for exit conditions if we have a position
        if current_position:
            position_side = current_position.get("side", "none")

            # Exit long position on bearish signals
            if position_side == "long" and final_score < 0.35:
                return DecisionAction.CLOSE_LONG, abs(0.5 - final_score) * 2

            # Exit short position on bullish signals
            if position_side == "short" and final_score > 0.65:
                return DecisionAction.CLOSE_SHORT, abs(final_score - 0.5) * 2

        # Entry decisions
        if final_score >= 0.7:
            # Strong buy signal
            confidence = (final_score - 0.5) * 2
            if confidence >= self.min_confidence:
                return DecisionAction.BUY, confidence
            return DecisionAction.WAIT, confidence

        elif final_score <= 0.3:
            # Strong sell signal
            confidence = (0.5 - final_score) * 2
            if confidence >= self.min_confidence:
                return DecisionAction.SELL, confidence
            return DecisionAction.WAIT, confidence

        elif 0.55 <= final_score < 0.7:
            # Mild bullish - wait for confirmation
            return DecisionAction.WAIT, (final_score - 0.5) * 2

        elif 0.3 < final_score <= 0.45:
            # Mild bearish - wait for confirmation
            return DecisionAction.WAIT, (0.5 - final_score) * 2

        else:
            # Neutral zone
            return DecisionAction.HOLD, abs(0.5 - final_score) * 2

    def _get_primary_reasons(
            self,
            signal: Signal,
            ta_result: TechnicalAnalysisResult,
            patterns: List[Pattern],
            llm_analysis: Optional[MarketAnalysis]
    ) -> List[str]:
        """Get primary reasons for the decision."""
        reasons = []

        # From signal
        reasons.extend(signal.reasons[:3])

        # From patterns
        for pattern in patterns[:2]:
            reasons.append(f"{pattern.pattern_type.value}: {pattern.description}")

        # From LLM
        if llm_analysis:
            reasons.extend(llm_analysis.key_factors[:2])

        return reasons[:5]

    def _get_supporting_factors(
            self,
            ta_result: TechnicalAnalysisResult,
            patterns: List[Pattern]
    ) -> List[str]:
        """Get supporting factors."""
        factors = []

        factors.append(f"Trend: {ta_result.trend.value}")
        factors.append(f"Momentum: {ta_result.momentum.value}")
        factors.append(f"Volatility: {ta_result.volatility:.1f}%")

        if ta_result.support_levels:
            factors.append(f"Support: {ta_result.support_levels[0]:.2f}")
        if ta_result.resistance_levels:
            factors.append(f"Resistance: {ta_result.resistance_levels[0]:.2f}")

        return factors

    def _get_risk_factors(
            self,
            signal: Signal,
            ta_result: TechnicalAnalysisResult,
            llm_analysis: Optional[MarketAnalysis]
    ) -> List[str]:
        """Get risk factors."""
        risks = list(signal.warnings)

        if llm_analysis:
            risks.extend(llm_analysis.risks[:2])

        if ta_result.volatility > 50:
            risks.append(f"High volatility ({ta_result.volatility:.1f}%)")

        return risks[:5]

    async def analyze_multiple(
            self,
            data: Dict[str, Any],  # symbol -> DataFrame
            timeframe: str = "1h",
            portfolio_value: Optional[Decimal] = None
    ) -> Dict[str, TradingDecision]:
        """
        Analyze multiple symbols and make decisions.

        Args:
            data: Dict mapping symbol to OHLCV DataFrame
            timeframe: Data timeframe
            portfolio_value: Total portfolio value

        Returns:
            Dict mapping symbol to TradingDecision
        """
        decisions = {}

        for symbol, df in data.items():
            try:
                decision = await self.make_decision(
                    df=df,
                    symbol=symbol,
                    timeframe=timeframe,
                    portfolio_value=portfolio_value
                )
                decisions[symbol] = decision
            except Exception as e:
                logger.error(f"Decision failed for {symbol}: {e}")
                decisions[symbol] = TradingDecision(
                    symbol=symbol,
                    action=DecisionAction.WAIT,
                    confidence=0.0,
                    timestamp=datetime.now(),
                    risk_factors=[f"Analysis error: {str(e)}"]
                )

        return decisions

    def get_best_opportunities(
            self,
            decisions: Dict[str, TradingDecision],
            top_n: int = 3
    ) -> List[TradingDecision]:
        """Get best trading opportunities from decisions."""
        actionable = [
            d for d in decisions.values()
            if d.is_actionable and d.confidence >= self.min_confidence
        ]

        actionable.sort(key=lambda x: x.confidence, reverse=True)
        return actionable[:top_n]
