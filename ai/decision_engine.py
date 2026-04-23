"""
Decision Engine: Final AI brain that combines all analysis into trading signals.

This module synthesizes:
- Sentiment analysis
- Chart technical analysis (LLaVA)
- Price trend
- News summary
- Risk assessment

To produce final trading decisions: BUY / SELL / HOLD
"""
import logging
from typing import Dict, Any, Optional
from enum import Enum

import config
from utils import setup_logging

logger = setup_logging(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class TradingAction(str, Enum):
    """Trading action enum."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class RiskLevel(str, Enum):
    """Risk level enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# DECISION ENGINE
# ============================================================================

class DecisionEngine:
    """Synthesizes all AI analysis into trading decisions."""
    
    # Configuration for decision thresholds
    BULLISH_SCORE_BUY = 0.65      # Score >= 0.65 triggers BUY
    BEARISH_SCORE_SELL = -0.60    # Score <= -0.60 triggers SELL
    HOLD_ZONE = (-0.60, 0.65)     # Between these scores = HOLD
    
    # Weights for different signals (sum = 1.0)
    # Reduced chart weight since LLaVA vision is unreliable
    WEIGHTS = {
        "sentiment": 0.45,      # Increased from 0.30
        "chart": 0.15,          # Reduced from 0.35 (LLaVA not reliable)
        "trend": 0.35,          # Increased from 0.20
        "risk": -0.05,          # Reduced penalty from -0.15
    }
    
    @staticmethod
    def _sentiment_score(sentiment: Dict[str, Any]) -> float:
        """
        Convert sentiment to score (-1 to 1).
        
        Args:
            sentiment: Sentiment dictionary
            
        Returns:
            Score from -1 (very negative) to 1 (very positive)
        """
        overall = sentiment.get("overall_sentiment", "neutral").lower()
        confidence = sentiment.get("average_confidence", 0.5)
        
        if overall == "positive":
            return confidence  # 0 to 1
        elif overall == "negative":
            return -confidence  # -1 to 0
        else:
            return 0.0
    
    
    @staticmethod
    def _chart_score(chart_analysis: Dict[str, Any]) -> float:
        """
        Convert chart analysis to score (-1 to 1).
        
        Args:
            chart_analysis: Chart analysis dictionary
            
        Returns:
            Score from -1 (bearish) to 1 (bullish)
        """
        sentiment = chart_analysis.get("chart_sentiment", "neutral").lower()
        confidence = chart_analysis.get("confidence", 0.5)
        
        if sentiment == "bullish":
            return confidence
        elif sentiment == "bearish":
            return -confidence
        else:
            return 0.0
    
    
    @staticmethod
    def _trend_score(trend: str) -> float:
        """
        Convert price trend to score (-1 to 1).
        
        Args:
            trend: "up", "down", or "sideways"
            
        Returns:
            Score from -1 to 1
        """
        trend_lower = trend.lower()
        if trend_lower == "up":
            return 0.5
        elif trend_lower == "down":
            return -0.5
        else:
            return 0.0
    
    
    @staticmethod
    def _risk_score(risk_level: str) -> float:
        """
        Convert risk level to adjustment (-1 to 1).
        Higher risk = lower score (penalty).
        
        Args:
            risk_level: "low", "medium", or "high"
            
        Returns:
            Score adjustment
        """
        risk_lower = risk_level.lower()
        if risk_lower == "high":
            return -0.5  # Major penalty
        elif risk_lower == "medium":
            return -0.2  # Minor penalty
        else:
            return 0.0   # No penalty
    
    
    @staticmethod
    def calculate_composite_score(
        sentiment: Dict[str, Any],
        chart_analysis: Dict[str, Any],
        trend: str,
        risk_level: str,
    ) -> float:
        """
        Calculate composite decision score.
        
        Args:
            sentiment: Sentiment analysis
            chart_analysis: Chart analysis
            trend: Price trend
            risk_level: Risk level
            
        Returns:
            Score from -1 (strong sell) to 1 (strong buy)
        """
        try:
            sentiment_score = DecisionEngine._sentiment_score(sentiment)
            chart_score = DecisionEngine._chart_score(chart_analysis)
            trend_score = DecisionEngine._trend_score(trend)
            risk_adjustment = DecisionEngine._risk_score(risk_level)
            
            # Weighted average
            composite = (
                sentiment_score * DecisionEngine.WEIGHTS["sentiment"] +
                chart_score * DecisionEngine.WEIGHTS["chart"] +
                trend_score * DecisionEngine.WEIGHTS["trend"] +
                risk_adjustment * DecisionEngine.WEIGHTS["risk"]
            )
            
            # Clamp to -1 to 1
            return max(-1.0, min(1.0, composite))
        
        except Exception as e:
            logger.error(f"❌ Error calculating composite score: {str(e)}")
            return 0.0
    
    
    @staticmethod
    def make_decision(
        composite_score: float,
    ) -> Dict[str, Any]:
        """
        Make trading decision based on composite score.
        
        Args:
            composite_score: Composite score from -1 to 1
            
        Returns:
            Decision dictionary with action and metadata
        """
        try:
            # Determine action
            if composite_score >= DecisionEngine.BULLISH_SCORE_BUY:
                action = TradingAction.BUY
                confidence = int(abs(composite_score) * 100)
                reason = "Strong bullish signals detected"
            elif composite_score <= DecisionEngine.BEARISH_SCORE_SELL:
                action = TradingAction.SELL
                confidence = int(abs(composite_score) * 100)
                reason = "Strong bearish signals detected"
            else:
                action = TradingAction.HOLD
                confidence = int((1 - abs(composite_score)) * 100)
                reason = f"Mixed signals (score: {composite_score:.2f})"
            
            # Adjust confidence
            confidence = max(0, min(100, confidence))
            
            return {
                "action": action.value,
                "confidence": confidence,
                "composite_score": round(composite_score, 3),
                "reason": reason,
            }
        
        except Exception as e:
            logger.error(f"❌ Error making decision: {str(e)}")
            return {
                "action": "hold",
                "confidence": 0,
                "composite_score": 0.0,
                "reason": "Error during decision processing",
                "error": str(e),
            }
    
    
    @staticmethod
    def generate_full_decision(
        symbol: str,
        sentiment: Dict[str, Any],
        chart_analysis: Dict[str, Any],
        trend: str,
        risk_level: str,
        news_summary: str = "",
        additional_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete trading decision with full analysis.
        
        Args:
            symbol: Coin symbol (e.g., "BTC", "ETH")
            sentiment: Sentiment analysis
            chart_analysis: Chart analysis
            trend: Price trend
            risk_level: Risk level assessment
            news_summary: News summary text
            additional_context: Extra context data
            
        Returns:
            Complete decision dictionary
        """
        try:
            # Calculate composite score
            composite_score = DecisionEngine.calculate_composite_score(
                sentiment,
                chart_analysis,
                trend,
                risk_level,
            )
            
            # Make decision
            decision = DecisionEngine.make_decision(composite_score)
            
            # Add metadata
            decision.update({
                "symbol": symbol,
                "sentiment_component": DecisionEngine._sentiment_score(sentiment),
                "chart_component": DecisionEngine._chart_score(chart_analysis),
                "trend_component": DecisionEngine._trend_score(trend),
                "risk_adjustment": DecisionEngine._risk_score(risk_level),
                "risk_level": risk_level,
                "sentiment": sentiment.get("overall_sentiment", "neutral"),
                "chart_sentiment": chart_analysis.get("chart_sentiment", "neutral"),
                "price_trend": trend,
                "summary": news_summary[:200] if news_summary else "No summary available",
            })
            
            if additional_context:
                decision["additional_context"] = additional_context
            
            return decision
        
        except Exception as e:
            logger.error(f"❌ Error generating full decision: {str(e)}")
            return {
                "action": "hold",
                "confidence": 0,
                "symbol": symbol,
                "reason": "Error generating decision",
                "error": str(e),
            }


# ============================================================================
# STANDALONE INTERFACE
# ============================================================================

def generate_trading_decision(
    ai_input: Dict[str, Any],
    sentiment: Dict[str, Any],
    chart_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate trading decision from AI inputs.
    
    Args:
        ai_input: Structured AI input
        sentiment: Sentiment analysis
        chart_analysis: Chart analysis
        
    Returns:
        Trading decision dictionary
    """
    return DecisionEngine.generate_full_decision(
        symbol=ai_input.get("symbol", "CRYPTO"),
        sentiment=sentiment,
        chart_analysis=chart_analysis,
        trend=ai_input.get("trend", "sideways"),
        risk_level=ai_input.get("risk_level", "medium"),
        news_summary=ai_input.get("news_summary", ""),
        additional_context={
            "price": ai_input.get("price", 0),
            "price_change_24h": ai_input.get("price_change_24h", 0),
            "article_count": ai_input.get("article_count", 0),
        },
    )


def generate_all_trading_decisions(
    ai_inputs: Dict[str, Dict[str, Any]],
    sentiments: Dict[str, Dict[str, Any]],
    chart_analyses: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Generate trading decisions for multiple coins.
    
    Args:
        ai_inputs: Dictionary of AI inputs by coin
        sentiments: Dictionary of sentiment analyses by coin
        chart_analyses: Dictionary of chart analyses by coin
        
    Returns:
        Dictionary mapping coins to trading decisions
    """
    decisions = {}
    
    for coin_name in ai_inputs.keys():
        try:
            logger.info(f"Generating trading decision for {coin_name.upper()}")
            
            ai_input = ai_inputs[coin_name]
            sentiment = sentiments.get(coin_name, {})
            chart_analysis = chart_analyses.get(coin_name, {})
            
            decision = generate_trading_decision(ai_input, sentiment, chart_analysis)
            decisions[coin_name] = decision
        
        except Exception as e:
            logger.error(f"❌ Error generating decision for {coin_name}: {str(e)}")
    
    logger.info(f"✓ Generated decisions for {len(decisions)} coins")
    return decisions


# ============================================================================
# ANALYSIS HELPERS
# ============================================================================

def explain_decision(decision: Dict[str, Any]) -> str:
    """
    Generate human-readable explanation of decision.
    
    Args:
        decision: Trading decision dictionary
        
    Returns:
        Explanation text
    """
    try:
        symbol = decision.get("symbol", "CRYPTO")
        action = decision.get("action", "hold").upper()
        confidence = decision.get("confidence", 0)
        reason = decision.get("reason", "Unknown")
        
        return (
            f"{symbol} Trading Signal: {action} (Confidence: {confidence}%)\n"
            f"Reason: {reason}\n"
            f"Composite Score: {decision.get('composite_score', 0):.2f}"
        )
    
    except Exception as e:
        logger.error(f"❌ Error explaining decision: {str(e)}")
        return "Error generating explanation"
