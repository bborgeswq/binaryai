"""
LLM Market Analyzer
Uses Claude or GPT to analyze market conditions and provide insights
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from loguru import logger

# Try importing LLM clients
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class MarketAnalysis:
    """LLM market analysis result"""
    symbol: str
    timestamp: datetime
    summary: str
    sentiment: Literal["bullish", "bearish", "neutral"]
    confidence: float
    key_factors: List[str]
    risks: List[str]
    opportunities: List[str]
    recommended_action: Literal["buy", "sell", "hold", "wait"]
    reasoning: str
    price_prediction: Optional[Dict[str, float]] = None  # short/medium/long term

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": str(self.timestamp),
            "summary": self.summary,
            "sentiment": self.sentiment,
            "confidence": self.confidence,
            "key_factors": self.key_factors,
            "risks": self.risks,
            "opportunities": self.opportunities,
            "recommended_action": self.recommended_action,
            "reasoning": self.reasoning,
            "price_prediction": self.price_prediction
        }


class LLMAnalyzer:
    """
    Uses LLMs for advanced market analysis.
    Provides context-aware reasoning that traditional indicators can't capture.
    """

    SYSTEM_PROMPT = """You are an expert cryptocurrency and stock market analyst with deep expertise in technical analysis, market psychology, and quantitative trading.

Your role is to analyze market data and provide actionable trading insights. You must:
1. Be objective and data-driven
2. Consider both bullish and bearish scenarios
3. Identify key risks and opportunities
4. Provide clear, actionable recommendations
5. Explain your reasoning

IMPORTANT: You are advising an automated trading system. Your analysis will be used to make real trading decisions. Be conservative with confidence levels and always highlight risks.

When analyzing data:
- Look for convergence/divergence of indicators
- Consider the broader market context
- Identify support and resistance levels
- Watch for pattern formations
- Evaluate volume and momentum
- Consider market sentiment

Always structure your response as valid JSON."""

    def __init__(
            self,
            api_key: str,
            provider: Literal["anthropic", "openai"] = "anthropic",
            model: Optional[str] = None,
            temperature: float = 0.3
    ):
        """
        Initialize LLM analyzer.

        Args:
            api_key: API key for the LLM provider
            provider: LLM provider (anthropic or openai)
            model: Model to use (default based on provider)
            temperature: Response temperature (lower = more consistent)
        """
        self.provider = provider
        self.temperature = temperature

        if provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed")
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model or "claude-sonnet-4-20250514"
        elif provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed")
            self.client = openai.OpenAI(api_key=api_key)
            self.model = model or "gpt-4-turbo-preview"
        else:
            raise ValueError(f"Unknown provider: {provider}")

        logger.info(f"LLM Analyzer initialized with {provider}/{self.model}")

    async def analyze_market(
            self,
            symbol: str,
            technical_data: Dict[str, Any],
            patterns: List[Dict[str, Any]],
            signal: Dict[str, Any],
            additional_context: Optional[str] = None
    ) -> MarketAnalysis:
        """
        Perform comprehensive market analysis using LLM.

        Args:
            symbol: Trading symbol
            technical_data: Technical analysis results
            patterns: Detected patterns
            signal: Current signal
            additional_context: Any additional context

        Returns:
            MarketAnalysis with LLM insights
        """
        prompt = self._build_analysis_prompt(
            symbol, technical_data, patterns, signal, additional_context
        )

        try:
            response = await self._call_llm(prompt)
            analysis = self._parse_response(response, symbol)
            return analysis
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._fallback_analysis(symbol, signal)

    async def get_market_commentary(
            self,
            symbols: List[str],
            portfolio_state: Dict[str, Any]
    ) -> str:
        """
        Get overall market commentary.

        Args:
            symbols: Symbols being tracked
            portfolio_state: Current portfolio state

        Returns:
            Market commentary string
        """
        prompt = f"""Provide a brief market commentary for a trading session.

Tracked Symbols: {', '.join(symbols)}

Current Portfolio:
{json.dumps(portfolio_state, indent=2)}

Provide:
1. Overall market sentiment (1-2 sentences)
2. Key things to watch today
3. Any concerning patterns or opportunities
4. Suggested focus areas

Keep it concise and actionable."""

        try:
            response = await self._call_llm(prompt)
            return response
        except Exception as e:
            logger.error(f"Failed to get market commentary: {e}")
            return "Market commentary unavailable."

    async def evaluate_trade(
            self,
            symbol: str,
            side: Literal["buy", "sell"],
            entry_price: float,
            stop_loss: float,
            take_profit: float,
            position_size: float,
            reasoning: str
    ) -> Dict[str, Any]:
        """
        Evaluate a proposed trade before execution.

        Args:
            symbol: Trading symbol
            side: Buy or sell
            entry_price: Proposed entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            position_size: Position size
            reasoning: Why this trade is being considered

        Returns:
            Evaluation with approval/rejection and reasoning
        """
        risk_pct = abs(entry_price - stop_loss) / entry_price * 100
        reward_pct = abs(take_profit - entry_price) / entry_price * 100
        rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0

        prompt = f"""Evaluate this proposed trade:

Symbol: {symbol}
Side: {side.upper()}
Entry Price: ${entry_price:,.2f}
Stop Loss: ${stop_loss:,.2f} ({risk_pct:.1f}% risk)
Take Profit: ${take_profit:,.2f} ({reward_pct:.1f}% reward)
Risk/Reward Ratio: {rr_ratio:.2f}
Position Size: ${position_size:,.2f}

Reasoning for trade:
{reasoning}

Evaluate this trade and respond with JSON:
{{
    "approved": true/false,
    "confidence": 0.0-1.0,
    "concerns": ["list of concerns"],
    "suggestions": ["list of suggestions"],
    "reasoning": "your reasoning"
}}

Be conservative. Only approve trades with solid reasoning and acceptable risk."""

        try:
            response = await self._call_llm(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Trade evaluation failed: {e}")
            return {
                "approved": False,
                "confidence": 0.0,
                "concerns": ["LLM evaluation failed"],
                "suggestions": [],
                "reasoning": str(e)
            }

    def _build_analysis_prompt(
            self,
            symbol: str,
            technical_data: Dict[str, Any],
            patterns: List[Dict[str, Any]],
            signal: Dict[str, Any],
            additional_context: Optional[str]
    ) -> str:
        """Build the analysis prompt."""
        prompt = f"""Analyze the following market data for {symbol}:

## Technical Analysis
{json.dumps(technical_data, indent=2)}

## Detected Patterns
{json.dumps(patterns, indent=2) if patterns else "No patterns detected"}

## Current Signal
{json.dumps(signal, indent=2)}

{f"## Additional Context{chr(10)}{additional_context}" if additional_context else ""}

Provide your analysis as JSON with this structure:
{{
    "summary": "Brief 1-2 sentence summary",
    "sentiment": "bullish" | "bearish" | "neutral",
    "confidence": 0.0-1.0,
    "key_factors": ["list of key factors"],
    "risks": ["list of risks"],
    "opportunities": ["list of opportunities"],
    "recommended_action": "buy" | "sell" | "hold" | "wait",
    "reasoning": "detailed reasoning",
    "price_prediction": {{
        "short_term": price or null,
        "medium_term": price or null,
        "direction": "up" | "down" | "sideways"
    }}
}}"""
        return prompt

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM API."""
        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=self.temperature,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        else:  # openai
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content

    def _parse_response(self, response: str, symbol: str) -> MarketAnalysis:
        """Parse LLM response into MarketAnalysis."""
        # Try to extract JSON from response
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

            return MarketAnalysis(
                symbol=symbol,
                timestamp=datetime.now(),
                summary=data.get("summary", "Analysis unavailable"),
                sentiment=data.get("sentiment", "neutral"),
                confidence=float(data.get("confidence", 0.5)),
                key_factors=data.get("key_factors", []),
                risks=data.get("risks", []),
                opportunities=data.get("opportunities", []),
                recommended_action=data.get("recommended_action", "wait"),
                reasoning=data.get("reasoning", ""),
                price_prediction=data.get("price_prediction")
            )
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return self._fallback_analysis(symbol, {"confidence": 0.5})

    def _fallback_analysis(self, symbol: str, signal: Dict[str, Any]) -> MarketAnalysis:
        """Return fallback analysis when LLM fails."""
        return MarketAnalysis(
            symbol=symbol,
            timestamp=datetime.now(),
            summary="LLM analysis unavailable - using signal-based assessment",
            sentiment="neutral",
            confidence=signal.get("confidence", 0.5) * 0.5,  # Lower confidence
            key_factors=signal.get("reasons", []),
            risks=["LLM analysis failed - proceed with caution"],
            opportunities=[],
            recommended_action="wait",
            reasoning="Fallback to technical signals only"
        )


class SentimentAnalyzer:
    """
    Analyzes market sentiment from various sources.
    Can be extended to analyze news, social media, etc.
    """

    def __init__(self, llm_analyzer: Optional[LLMAnalyzer] = None):
        self.llm = llm_analyzer

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment from text."""
        if not self.llm:
            return {"sentiment": "neutral", "confidence": 0.5}

        prompt = f"""Analyze the sentiment of this market-related text:

"{text}"

Respond with JSON:
{{
    "sentiment": "bullish" | "bearish" | "neutral",
    "confidence": 0.0-1.0,
    "key_points": ["list of key points"],
    "market_impact": "high" | "medium" | "low" | "none"
}}"""

        try:
            response = await self.llm._call_llm(prompt)
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")

        return {"sentiment": "neutral", "confidence": 0.5}

    async def get_market_mood(self, headlines: List[str]) -> Dict[str, Any]:
        """Get overall market mood from headlines."""
        if not headlines:
            return {"mood": "neutral", "confidence": 0.5}

        text = "\n".join(f"- {h}" for h in headlines[:10])

        prompt = f"""Analyze the overall market mood from these headlines:

{text}

Respond with JSON:
{{
    "mood": "bullish" | "bearish" | "neutral" | "fearful" | "greedy",
    "confidence": 0.0-1.0,
    "summary": "brief summary",
    "key_themes": ["list of themes"]
}}"""

        try:
            if self.llm:
                response = await self.llm._call_llm(prompt)
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end > start:
                    return json.loads(response[start:end])
        except Exception as e:
            logger.error(f"Market mood analysis failed: {e}")

        return {"mood": "neutral", "confidence": 0.5}
