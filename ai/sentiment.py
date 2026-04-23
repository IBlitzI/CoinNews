"""
Sentiment analysis module for cryptocurrency market news and data.

Uses Llama 3 via Ollama for accurate sentiment analysis.
Analyzes text sentiment and returns structured scores for AI decision-making.
"""
import logging
from typing import Dict, Any, List
from pathlib import Path
import json
import re

import config
from utils import setup_logging

logger = setup_logging(__name__)


# ============================================================================
# SENTIMENT ANALYZER
# ============================================================================

class SentimentAnalyzer:
    """Analyzes sentiment of cryptocurrency market data using Llama 3."""
    
    def __init__(self, use_ollama: bool = True):
        """
        Initialize sentiment analyzer.
        Uses Llama 3 via Ollama as primary method.
        
        Args:
            use_ollama: Use Ollama for Llama 3 analysis
        """
        self.use_ollama = use_ollama
        self.ollama_client = None
        
        if use_ollama:
            try:
                from ai.ollama_client import get_ollama_client
                self.ollama_client = get_ollama_client()
                logger.info("✓ Sentiment analyzer using Llama 3 via Ollama")
            except ImportError:
                logger.warning("⚠ Ollama import failed, will use lightweight sentiment analysis")
                self.use_ollama = False
        
        # Backup keywords (only used if Ollama unavailable)
        self.positive_keywords = {
            "bull": 2.0, "bullish": 2.0, "up": 1.5, "surge": 2.0, "spike": 2.0,
            "gain": 1.5, "growth": 1.5, "strong": 1.5, "rise": 1.5, "high": 1.0,
            "breakthrough": 2.0, "boom": 2.0, "positive": 1.5, "green": 1.0,
            "pump": 1.5, "rally": 2.0, "momentum": 1.5, "uptrend": 2.0,
            "profit": 1.5, "success": 1.5, "record": 1.5, "all-time high": 2.0,
            "approval": 2.0, "adoption": 2.0, "partnership": 1.5, "inflow": 1.5,
        }
        
        self.negative_keywords = {
            "bear": -2.0, "bearish": -2.0, "down": -1.5, "crash": -2.0, "plunge": -2.0,
            "loss": -1.5, "weak": -1.5, "fall": -1.5, "low": -1.0, "dump": -1.5,
            "decline": -1.5, "negative": -1.5, "red": -1.0, "selloff": -2.0,
            "fear": -2.0, "panic": -2.0, "disaster": -2.0, "collapse": -2.0,
            "downtrend": -2.0, "liquidation": -2.0, "hack": -2.0, "exploit": -2.0,
            "scandal": -2.0, "fraud": -2.0, "loss": -1.5, "outflow": -1.5,
        }
    
    
    def _lightweight_sentiment(self, text: str) -> tuple[str, float]:
        """
        Lightweight keyword-based sentiment analysis (fallback only).
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (sentiment, confidence)
        """
        try:
            if not text:
                return "neutral", 0.5
            
            text_lower = text.lower()
            
            # Calculate sentiment score
            pos_score = sum(
                weight
                for keyword, weight in self.positive_keywords.items()
                if keyword in text_lower
            )
            
            neg_score = sum(
                weight
                for keyword, weight in self.negative_keywords.items()
                if keyword in text_lower
            )
            
            # Determine sentiment
            total_score = pos_score + neg_score
            
            if total_score > 0.5:
                sentiment = "positive"
                confidence = min(total_score / 10, 0.95)  # Cap at 0.95
            elif total_score < -0.5:
                sentiment = "negative"
                confidence = min(abs(total_score) / 10, 0.95)
            else:
                sentiment = "neutral"
                confidence = 0.5 + abs(total_score) / 20
            
            return sentiment, max(0.1, min(confidence, 1.0))
        
        except Exception as e:
            logger.error(f"❌ Error in lightweight sentiment: {str(e)}")
            return "neutral", 0.5
    
    
    def _llama3_sentiment(self, text: str) -> tuple:
        """
        Llama 3 sentiment analysis via Ollama.
        Primary method for accurate sentiment detection.
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (sentiment, confidence) or None if failed
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            return None
        
        try:
            # Keep text limited to avoid token bloat
            text_preview = text[:1000] if len(text) > 1000 else text
            
            prompt = f"""You are a cryptocurrency market sentiment analyst. Analyze the sentiment of this text about cryptocurrency.

Text to analyze:
{text_preview}

Provide your analysis in this exact format:
SENTIMENT: [positive|negative|neutral]
CONFIDENCE: [0.0-1.0]
REASONING: [brief one-line explanation]

Focus on market impact and trading relevance."""
            
            response = self.ollama_client.generate_text(
                prompt,
                model="llama3",
                temperature=0.3,
                top_p=0.9,
            )
            
            if not response:
                return None
            
            # Parse response
            lines = response.strip().split("\n")
            sentiment_line = None
            confidence_line = None
            
            for line in lines:
                if "SENTIMENT:" in line:
                    sentiment_line = line
                elif "CONFIDENCE:" in line:
                    confidence_line = line
            
            if sentiment_line and confidence_line:
                sentiment = sentiment_line.split("SENTIMENT:")[-1].strip().lower()
                confidence_str = confidence_line.split("CONFIDENCE:")[-1].strip()
                
                # Extract confidence number
                try:
                    confidence = float(re.search(r'[\d.]+', confidence_str).group())
                except (ValueError, AttributeError):
                    confidence = 0.5
                
                if sentiment in ["positive", "negative", "neutral"]:
                    confidence = max(0.0, min(confidence, 1.0))
                    return sentiment, confidence
            
            logger.debug(f"⚠ Failed to parse Llama 3 response: {response[:100]}")
            return None
        
        except Exception as e:
            logger.error(f"❌ Error in Llama 3 sentiment: {str(e)}")
            return None
    
    
    def analyze(
        self,
        text: str,
        use_llama3: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze text sentiment using Llama 3 primarily.
        
        Args:
            text: Text to analyze
            use_llama3: Use Llama 3 for analysis (primary)
            
        Returns:
            Dictionary with sentiment and confidence
        """
        try:
            # Try Llama 3 first (primary method)
            if use_llama3 and self.use_ollama:
                result = self._llama3_sentiment(text)
                if result:
                    sentiment, confidence = result
                    return {
                        "sentiment": sentiment,
                        "confidence": confidence,
                        "method": "llama3",
                    }
            
            # Fallback to lightweight keywords
            logger.debug("Falling back to lightweight sentiment (Llama 3 unavailable)")
            sentiment, confidence = self._lightweight_sentiment(text)
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "method": "lightweight_fallback",
            }
        
        except Exception as e:
            logger.error(f"❌ Error analyzing sentiment: {str(e)}")
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "error": str(e),
                "method": "error",
            }
    
    
    def analyze_articles(
        self,
        articles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze sentiment across multiple articles using Llama 3.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Aggregated sentiment analysis
        """
        if not articles:
            return {
                "overall_sentiment": "neutral",
                "average_confidence": 0.5,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }
    
    
    def analyze_articles(
        self,
        articles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Analyze sentiment across multiple articles using Llama 3.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Aggregated sentiment analysis
        """
        if not articles:
            return {
                "overall_sentiment": "neutral",
                "average_confidence": 0.5,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
            }
        
        try:
            sentiments = []
            confidences = []
            
            # Analyze each article with Llama 3
            for article in articles:
                content = article.get("content", "") or article.get("title", "")
                if content:
                    result = self.analyze(content, use_llama3=True)
                    sentiments.append(result["sentiment"])
                    confidences.append(result["confidence"])
            
            if not sentiments:
                return {
                    "overall_sentiment": "neutral",
                    "average_confidence": 0.5,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                }
            
            pos_count = sentiments.count("positive")
            neg_count = sentiments.count("negative")
            neu_count = sentiments.count("neutral")
            
            # Determine overall sentiment
            if pos_count > neg_count:
                overall = "positive"
            elif neg_count > pos_count:
                overall = "negative"
            else:
                overall = "neutral"
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            
            return {
                "overall_sentiment": overall,
                "average_confidence": avg_confidence,
                "positive_count": pos_count,
                "negative_count": neg_count,
                "neutral_count": neu_count,
                "total_articles": len(articles),
                "method": "llama3",
            }
        
        except Exception as e:
            logger.error(f"❌ Error analyzing articles: {str(e)}")
            return {
                "overall_sentiment": "neutral",
                "average_confidence": 0.0,
                "error": str(e),
            }


# ============================================================================
# FILE-BASED INTERFACE
# ============================================================================

def analyze_news_file(
    news_json_path: str,
    use_ollama: bool = True,
) -> Dict[str, Any]:
    """
    Analyze sentiment from a news JSON file.
    
    Args:
        news_json_path: Path to news.json file
        use_ollama: Use Ollama for analysis
        
    Returns:
        Sentiment analysis dictionary
    """
    try:
        news_path = Path(news_json_path)
        if not news_path.exists():
            logger.error(f"❌ News file not found: {news_json_path}")
            return {"error": "File not found"}
        
        with open(news_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        articles = data.get("articles", [])
        
        analyzer = SentimentAnalyzer(use_ollama=use_ollama)
        result = analyzer.analyze_articles(articles)
        
        return result
    
    except json.JSONDecodeError:
        logger.error(f"❌ Invalid JSON in {news_json_path}")
        return {"error": "Invalid JSON"}
    except Exception as e:
        logger.error(f"❌ Error analyzing news file: {str(e)}")
        return {"error": str(e)}


# ============================================================================
# BATCH INTERFACE
# ============================================================================

def analyze_all_coins(use_ollama: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Analyze sentiment for all configured coins.
    
    Args:
        use_ollama: Use Ollama for analysis
        
    Returns:
        Dictionary mapping coin names to sentiment analysis
    """
    results = {}
    
    for coin_name in config.get_all_coin_names():
        output_files = config.get_output_files(coin_name)
        news_file = output_files["news_json"]
        
        if news_file.exists():
            logger.info(f"Analyzing sentiment for {coin_name.upper()}")
            sentiment = analyze_news_file(str(news_file), use_ollama=use_ollama)
            results[coin_name] = sentiment
    
    logger.info(f"✓ Sentiment analysis complete for {len(results)} coins")
    return results
