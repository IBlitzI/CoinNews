"""
AI Input Builder: Combines raw data into structured, AI-ready format.

This is the CORE module that prepares data for all AI models (LLM, LLaVA, etc).
Output must be clean, structured, and minimal to optimize AI analysis.
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional

import config
from utils import setup_logging

logger = setup_logging(__name__)


# ============================================================================
# INPUT BUILDER
# ============================================================================

class AIInputBuilder:
    """Builds structured AI inputs from raw crypto data."""
    
    @staticmethod
    def _determine_trend(price_data: Dict[str, Any]) -> str:
        """
        Determine price trend from price data.
        
        Args:
            price_data: Price data dictionary
            
        Returns:
            "up", "down", or "sideways"
        """
        try:
            current = price_data.get("current_price", 0)
            open_price = price_data.get("open_price_24h", current)
            
            if open_price == 0:
                return "sideways"
            
            change_pct = ((current - open_price) / open_price) * 100
            
            if change_pct > 1.5:
                return "up"
            elif change_pct < -1.5:
                return "down"
            else:
                return "sideways"
        
        except Exception as e:
            logger.warning(f"⚠ Error determining trend: {str(e)}")
            return "sideways"
    
    
    @staticmethod
    def _determine_risk_level(
        price_data: Dict[str, Any],
        sentiment: Dict[str, Any],
    ) -> str:
        """
        Determine risk level based on price volatility and sentiment.
        
        Args:
            price_data: Price data
            sentiment: Sentiment analysis
            
        Returns:
            "low", "medium", or "high"
        """
        try:
            high = price_data.get("high_24h") or 0
            low = price_data.get("low_24h") or 0
            current = price_data.get("current_price") or 0
            
            # Ensure all values are numeric and non-zero for comparison
            high = float(high) if high else 0
            low = float(low) if low else 0
            current = float(current) if current else 0
            
            if current == 0 or high == 0 or low == 0:
                return "medium"
            
            # Calculate volatility
            volatility = ((high - low) / current) * 100 if current > 0 else 0
            
            # Calculate risk based on volatility and sentiment confidence
            sentiment_confidence = sentiment.get("average_confidence", 0.5)
            
            if volatility > 10:
                base_risk = "high"
            elif volatility > 5:
                base_risk = "medium"
            else:
                base_risk = "low"
            
            # Adjust if low sentiment confidence (high uncertainty)
            if sentiment_confidence < 0.4:
                if base_risk == "low":
                    base_risk = "medium"
                elif base_risk == "medium":
                    base_risk = "high"
            
            return base_risk
        
        except Exception as e:
            logger.warning(f"⚠ Error determining risk level: {str(e)}")
            return "medium"
    
    
    @staticmethod
    def build(
        coin_name: str,
        price_data: Dict[str, Any],
        sentiment: Dict[str, Any],
        summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build AI input from components.
        
        Args:
            coin_name: Coin name (e.g., "bitcoin")
            price_data: Price dictionary from data_fetcher
            sentiment: Sentiment analysis from sentiment module
            summary: Summary from summarizer module
            
        Returns:
            Structured AI input dictionary
        """
        try:
            symbol = config.get_coin_by_name(coin_name)
            symbol_str = symbol["symbol"] if symbol else f"{coin_name.upper()}USDT"
            
            trend = AIInputBuilder._determine_trend(price_data)
            risk_level = AIInputBuilder._determine_risk_level(price_data, sentiment)
            
            # Build clean AI input
            ai_input = {
                # Identifiers
                "symbol": symbol_str.replace("USDT", ""),
                "coin_name": coin_name.lower(),
                
                # Price Information
                "price": round(float(price_data.get("current_price") or 0), 2),
                "price_change_24h": round(float(price_data.get("price_change_percent_24h") or 0), 2),
                "high_24h": round(float(price_data.get("high_24h") or 0), 2),
                "low_24h": round(float(price_data.get("low_24h") or 0), 2),
                
                # Technical Trend
                "trend": trend,
                
                # Sentiment
                "sentiment": sentiment.get("overall_sentiment", "neutral"),
                "sentiment_confidence": round(float(sentiment.get("average_confidence") or 0.5), 2),
                "sentiment_positive_count": sentiment.get("positive_count", 0),
                "sentiment_negative_count": sentiment.get("negative_count", 0),
                
                # News Summary (CONDENSED!)
                "news_summary": summary.get("summary", "No summary available")[:500],
                "key_points": summary.get("key_points", [])[:5],
                
                # Chart Path for LLaVA
                "chart_path": str(config.get_output_files(coin_name)["chart_png"]),
                
                # Risk Assessment
                "risk_level": risk_level,
                
                # Metadata
                "article_count": summary.get("article_count", 0),
                "data_timestamp": price_data.get("fetched_at", ""),
            }
            
            logger.debug(f"✓ Built AI input for {coin_name.upper()}")
            return ai_input
        
        except Exception as e:
            logger.error(f"❌ Error building AI input: {str(e)}")
            return {}
    
    
    @staticmethod
    def build_ai_inputs_from_files(coin_name: str) -> Optional[Dict[str, Any]]:
        """
        Build AI inputs by reading data files for a coin.
        
        Args:
            coin_name: Coin name
            
        Returns:
            AI input dictionary or None if failed
        """
        try:
            output_files = config.get_output_files(coin_name)
            
            # Load price data
            price_file = output_files["price_json"]
            if not price_file.exists():
                logger.error(f"❌ Price file not found: {price_file}")
                return None
            
            with open(price_file, "r", encoding="utf-8") as f:
                price_data = json.load(f)
            
            # Load news data for sentiment
            news_file = output_files["news_json"]
            if not news_file.exists():
                logger.error(f"❌ News file not found: {news_file}")
                return None
            
            with open(news_file, "r", encoding="utf-8") as f:
                news_data = json.load(f)
            
            # Analyze sentiment from loaded news
            from ai.sentiment import SentimentAnalyzer
            analyzer = SentimentAnalyzer(use_ollama=config.SENTIMENT_USE_OLLAMA)
            sentiment = analyzer.analyze_articles(news_data.get("articles", []))
            
            # Summarize news
            from ai.summarizer import NewsSummarizer
            summarizer = NewsSummarizer(use_ollama=config.SUMMARIZER_USE_OLLAMA)
            summary = summarizer.summarize(
                news_data.get("articles", []),
                max_points=config.SUMMARIZER_MAX_POINTS,
                use_ollama_if_available=config.SUMMARIZER_USE_OLLAMA,
            )
            
            # Build AI input
            ai_input = AIInputBuilder.build(
                coin_name,
                price_data,
                sentiment,
                summary,
            )
            
            return ai_input
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Error building AI input from files: {str(e)}")
            return None
    
    
    @staticmethod
    def build_all_ai_inputs() -> Dict[str, Dict[str, Any]]:
        """
        Build AI inputs for all configured coins.
        
        Returns:
            Dictionary mapping coin names to AI inputs
        """
        results = {}
        
        for coin_name in config.get_all_coin_names():
            logger.info(f"Building AI input for {coin_name.upper()}")
            ai_input = AIInputBuilder.build_ai_inputs_from_files(coin_name)
            if ai_input:
                results[coin_name] = ai_input
        
        logger.info(f"✓ Built AI inputs for {len(results)} coins")
        return results
    
    
    @staticmethod
    def validate_ai_input(ai_input: Dict[str, Any]) -> bool:
        """
        Validate AI input structure.
        
        Args:
            ai_input: AI input dictionary
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            "symbol",
            "price",
            "trend",
            "sentiment",
            "chart_path",
        ]
        
        for field in required_fields:
            if field not in ai_input:
                logger.warning(f"⚠ Missing required field: {field}")
                return False
        
        return True
