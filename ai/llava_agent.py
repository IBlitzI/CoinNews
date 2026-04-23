"""
LLaVA Vision Agent for technical chart analysis.

Uses Ollama's LLaVA model to analyze cryptocurrency price charts
and identify technical patterns, trends, and support/resistance levels.
"""
import logging
import json
import re
from typing import Dict, Any, Optional
from pathlib import Path

import config
from utils import setup_logging

logger = setup_logging(__name__)


# ============================================================================
# LLAVA CHART ANALYZER
# ============================================================================

class LLaVAChartAnalyzer:
    """Analyzes cryptocurrency price charts using LLaVA vision model."""
    
    def __init__(self):
        """Initialize chart analyzer."""
        try:
            from ai.ollama_client import get_ollama_client
            self.ollama_client = get_ollama_client()
            self.available = True
        except ImportError:
            logger.warning("⚠ Ollama client not available")
            self.ollama_client = None
            self.available = False
    
    
    def _fallback_analysis(self, ai_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback analysis when LLaVA is not available.
        Uses price trend from structured data.
        
        Args:
            ai_input: Structured AI input
            
        Returns:
            Chart analysis dictionary
        """
        try:
            trend = ai_input.get("trend", "sideways")
            price_change = ai_input.get("price_change_24h", 0)
            
            # Determine chart sentiment from trend and price change
            if trend == "up" or price_change > 2:
                chart_sentiment = "bullish"
                confidence = 0.65
                notes = f"Uptrend detected. 24h change: {price_change:.2f}%"
            elif trend == "down" or price_change < -2:
                chart_sentiment = "bearish"
                confidence = 0.65
                notes = f"Downtrend detected. 24h change: {price_change:.2f}%"
            else:
                chart_sentiment = "neutral"
                confidence = 0.55
                notes = "Sideways movement, no clear directional bias"
            
            return {
                "chart_sentiment": chart_sentiment,
                "confidence": confidence,
                "notes": notes,
                "method": "fallback_structural",
            }
        
        except Exception as e:
            logger.error(f"❌ Error in fallback analysis: {str(e)}")
            return {
                "chart_sentiment": "neutral",
                "confidence": 0.5,
                "notes": "Analysis unavailable",
                "error": str(e),
            }
    
    
    def analyze_chart(
        self,
        chart_path: str,
        ai_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Analyze a cryptocurrency price chart using LLaVA.
        
        Args:
            chart_path: Path to chart PNG file
            ai_input: Structured AI input with price context
            
        Returns:
            Chart analysis dictionary
        """
        try:
            # Check if chart exists
            chart_file = Path(chart_path)
            if not chart_file.exists():
                logger.warning(f"⚠ Chart not found: {chart_path}")
                return self._fallback_analysis(ai_input)
            
            # Try LLaVA analysis if available
            if self.available and self.ollama_client and self.ollama_client.is_available():
                return self._llava_analysis(chart_path, ai_input)
            
            # Fallback
            logger.debug("Using fallback chart analysis (Ollama not available)")
            return self._fallback_analysis(ai_input)
        
        except Exception as e:
            logger.error(f"❌ Error analyzing chart: {str(e)}")
            return self._fallback_analysis(ai_input)
    
    
    def _llava_analysis(
        self,
        chart_path: str,
        ai_input: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLaVA to analyze chart.
        Intentionally reduces confidence to make analysis less impactful.
        
        Args:
            chart_path: Path to chart image
            ai_input: AI input with context
            
        Returns:
            Analysis result or None
        """
        try:
            symbol = ai_input.get("symbol", "CRYPTO")
            price = ai_input.get("price", 0)
            
            prompt = f"""Analyze this {symbol} price chart and provide:
1. Overall trend: bullish, bearish, or neutral
2. Confidence level (0.0-1.0)
3. Brief technical analysis (1-2 sentences)

Context: Current price ${price}, 24h trend: {ai_input.get('trend')}

Respond in JSON format:
{{
    "chart_sentiment": "bullish|bearish|neutral",
    "confidence": 0.0-1.0,
    "notes": "technical analysis here"
}}"""
            
            response = self.ollama_client.analyze_image(
                chart_path,
                prompt,
                model="llava",
                temperature=0.5,
            )
            
            if not response:
                return None
            
            # Parse JSON from response
            try:
                json_match = re.search(r'\{[^{}]*"chart_sentiment"[^{}]*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    # Reduce confidence for LLaVA analysis (image interpretation unreliable)
                    original_confidence = result.get("confidence", 0.5)
                    # Cap at 0.35 and reduce further
                    result["confidence"] = min(original_confidence * 0.4, 0.35)
                    result["method"] = "llava_reduced"
                    return result
            except (json.JSONDecodeError, AttributeError):
                logger.debug("⚠ Failed to parse LLM response as JSON")
            
            return None
        
        except Exception as e:
            logger.error(f"❌ Error in LLaVA analysis: {str(e)}")
            return None


# ============================================================================
# STANDALONE INTERFACE
# ============================================================================

def analyze_chart(
    chart_path: str,
    ai_input: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Analyze a cryptocurrency chart.
    
    Args:
        chart_path: Path to chart image
        ai_input: Structured AI input
        
    Returns:
        Chart analysis dictionary
    """
    analyzer = LLaVAChartAnalyzer()
    return analyzer.analyze_chart(chart_path, ai_input)


def analyze_all_charts(
    ai_inputs: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Analyze charts for multiple coins.
    
    Args:
        ai_inputs: Dictionary mapping coin names to AI inputs
        
    Returns:
        Dictionary mapping coin names to chart analyses
    """
    results = {}
    analyzer = LLaVAChartAnalyzer()
    
    total = len(ai_inputs)
    for idx, (coin_name, ai_input) in enumerate(ai_inputs.items(), start=1):
        try:
            logger.info(f"[{idx}/{total}] Analyzing chart for {coin_name.upper()}")
            
            chart_path = ai_input.get("chart_path")
            if not chart_path:
                logger.warning(f"⚠ No chart path for {coin_name}")
                continue
            
            analysis = analyzer.analyze_chart(chart_path, ai_input)
            results[coin_name] = analysis
        
        except Exception as e:
            logger.error(f"❌ Error analyzing chart for {coin_name}: {str(e)}")
    
    logger.info(f"✓ Chart analysis complete for {len(results)} coins")
    return results


# ============================================================================
# UTILITIES
# ============================================================================

def get_chart_sentiment_score(analysis: Dict[str, Any]) -> float:
    """
    Convert chart sentiment to numerical score (-1 to 1).
    
    Args:
        analysis: Chart analysis dictionary
        
    Returns:
        Score from -1 (bearish) to 1 (bullish)
    """
    sentiment = analysis.get("chart_sentiment", "neutral").lower()
    
    if sentiment == "bullish":
        return 1.0
    elif sentiment == "bearish":
        return -1.0
    else:
        return 0.0


def interpret_chart_analysis(analysis: Dict[str, Any]) -> str:
    """
    Create human-readable interpretation of chart analysis.
    
    Args:
        analysis: Chart analysis dictionary
        
    Returns:
        Interpretation text
    """
    sentiment = analysis.get("chart_sentiment", "neutral")
    confidence = analysis.get("confidence", 0.5)
    notes = analysis.get("notes", "No technical notes available")
    
    confidence_pct = int(confidence * 100)
    
    return (
        f"{sentiment.capitalize()} pattern detected (confidence: {confidence_pct}%). "
        f"Technical analysis: {notes}"
    )
