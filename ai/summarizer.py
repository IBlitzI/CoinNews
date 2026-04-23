"""
News summarizer module for condensing raw articles into concise, market-relevant summaries.

Reduces 20k+ token articles into 5-7 key bullet points optimized for AI trading analysis.
"""
import logging
import json
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

import config
from utils import setup_logging

logger = setup_logging(__name__)


# ============================================================================
# SUMMARIZER ENGINE
# ============================================================================

class NewsSummarizer:
    """Summarizes news articles for market analysis."""
    
    def __init__(self, use_ollama: bool = True):
        """
        Initialize summarizer.
        
        Args:
            use_ollama: Whether to use Ollama for advanced summarization
        """
        self.use_ollama = use_ollama
        self.ollama_client = None
        
        if use_ollama:
            try:
                from ai.ollama_client import get_ollama_client
                self.ollama_client = get_ollama_client()
            except ImportError:
                logger.warning("⚠ Ollama import failed, using lightweight summarization")
                self.use_ollama = False
    
    
    def _lightweight_summary(
        self,
        articles: List[Dict[str, Any]],
        max_points: int = 7,
    ) -> Dict[str, Any]:
        """
        Lightweight summarization without LLM.
        Extracts key phrases and important sentences.
        
        Args:
            articles: List of article dictionaries
            max_points: Maximum bullet points to generate
            
        Returns:
            Summary dictionary
        """
        if not articles:
            return {
                "summary": "No articles available",
                "key_points": [],
                "sentiment_hint": "neutral",
                "article_count": 0,
            }
        
        try:
            # Combine all titles for quick context
            titles = [a.get("title", "") for a in articles if a.get("title")]
            all_content = " ".join(titles)
            
            # Extract first 500 chars of content from first few articles
            for article in articles[:3]:
                content = article.get("content", "")
                if content:
                    all_content += " " + content[:300]
            
            # Simple sentiment detection from content
            positive_words = ["up", "gain", "surge", "bull", "strong", "growth", "rise"]
            negative_words = ["down", "fall", "crash", "bear", "weak", "decline", "loss"]
            
            text_lower = all_content.lower()
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)
            
            if pos_count > neg_count:
                sentiment = "positive"
            elif neg_count > pos_count:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            # Extract key sentences
            key_points = []
            for article in articles[:5]:  # Top 5 articles
                title = article.get("title", "").strip()
                if title and len(title) > 10:
                    # Truncate long titles
                    if len(title) > 100:
                        title = title[:97] + "..."
                    key_points.append(title)
            
            key_points = key_points[:max_points]
            
            summary = (
                f"Summary of {len(articles)} articles. "
                f"Primary sentiment: {sentiment}. "
                f"Key stories: {', '.join(key_points[:3]) if key_points else 'Mixed market news'}."
            )
            
            return {
                "summary": summary,
                "key_points": key_points,
                "sentiment_hint": sentiment,
                "article_count": len(articles),
            }
        
        except Exception as e:
            logger.error(f"❌ Error in lightweight summary: {str(e)}")
            return {
                "summary": f"{len(articles)} articles analyzed",
                "key_points": [],
                "sentiment_hint": "neutral",
                "article_count": len(articles),
            }
    
    
    def _ollama_summary(
        self,
        articles: List[Dict[str, Any]],
        max_points: int = 7,
    ) -> Optional[Dict[str, Any]]:
        """
        Ollama-powered summarization using LLM.
        
        Args:
            articles: List of articles
            max_points: Maximum bullet points
            
        Returns:
            Summary dictionary or None if failed
        """
        if not self.ollama_client or not self.ollama_client.is_available():
            logger.debug("⚠ Ollama not available, falling back to lightweight")
            return None
        
        try:
            # Combine article titles (keep token count low)
            titles = [a.get("title", "") for a in articles if a.get("title")][:10]
            combined_titles = "\n".join(titles)
            
            prompt = f"""Analyze these cryptocurrency news headlines and provide:
1. A brief 1-2 sentence summary
2. Exactly {max_points} key bullet points (max 10 words each)
3. Overall sentiment: positive, negative, or neutral

Headlines:
{combined_titles}

Format your response as JSON:
{{
    "summary": "...",
    "key_points": ["point1", "point2"],
    "sentiment_hint": "positive|negative|neutral"
}}"""
            
            response = self.ollama_client.generate_text(
                prompt,
                model="llama3",
                temperature=0.5,
            )
            
            if not response:
                return None
            
            # Parse JSON from response
            try:
                # Extract JSON from response
                json_match = re.search(r'\{[^{}]*"summary"[^{}]*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    result["article_count"] = len(articles)
                    return result
            except (json.JSONDecodeError, AttributeError):
                logger.debug("⚠ Failed to parse LLM response as JSON")
            
            return None
        
        except Exception as e:
            logger.error(f"❌ Error in Ollama summary: {str(e)}")
            return None
    
    
    def summarize(
        self,
        articles: List[Dict[str, Any]],
        max_points: int = 7,
        use_ollama_if_available: bool = True,
    ) -> Dict[str, Any]:
        """
        Summarize articles using optimal method.
        
        Args:
            articles: List of article dictionaries
            max_points: Maximum bullet points to generate
            use_ollama_if_available: Try Ollama first, fallback to lightweight
            
        Returns:
            Summary dictionary
        """
        try:
            # Try Ollama first if available and requested
            if use_ollama_if_available and self.use_ollama:
                ollama_result = self._ollama_summary(articles, max_points)
                if ollama_result:
                    logger.info(f"✓ Ollama summarization complete ({len(articles)} articles)")
                    return ollama_result
            
            # Fallback to lightweight
            result = self._lightweight_summary(articles, max_points)
            logger.info(f"✓ Lightweight summarization complete ({len(articles)} articles)")
            return result
        
        except Exception as e:
            logger.error(f"❌ Error summarizing articles: {str(e)}")
            return {
                "summary": "Error during summarization",
                "key_points": [],
                "sentiment_hint": "neutral",
                "article_count": len(articles),
            }


# ============================================================================
# FILE-BASED INTERFACE
# ============================================================================

def summarize_news_file(
    news_json_path: str,
    use_ollama: bool = True,
    max_points: int = 7,
) -> Dict[str, Any]:
    """
    Summarize news from a JSON file.
    
    Args:
        news_json_path: Path to news.json file
        use_ollama: Use Ollama for summarization
        max_points: Maximum bullet points
        
    Returns:
        Summary dictionary
    """
    try:
        news_path = Path(news_json_path)
        if not news_path.exists():
            logger.error(f"❌ News file not found: {news_json_path}")
            return {"error": "File not found", "key_points": [], "sentiment_hint": "neutral"}
        
        with open(news_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        articles = data.get("articles", [])
        
        summarizer = NewsSummarizer(use_ollama=use_ollama)
        summary = summarizer.summarize(articles, max_points=max_points)
        
        return summary
    
    except json.JSONDecodeError:
        logger.error(f"❌ Invalid JSON in {news_json_path}")
        return {"error": "Invalid JSON", "key_points": [], "sentiment_hint": "neutral"}
    except Exception as e:
        logger.error(f"❌ Error reading news file: {str(e)}")
        return {"error": str(e), "key_points": [], "sentiment_hint": "neutral"}


# ============================================================================
# BATCH INTERFACE
# ============================================================================

def summarize_all_coins(
    use_ollama: bool = True,
    max_points: int = 7,
) -> Dict[str, Dict[str, Any]]:
    """
    Summarize news for all configured coins.
    
    Args:
        use_ollama: Use Ollama for summarization
        max_points: Maximum bullet points per coin
        
    Returns:
        Dictionary mapping coin names to summaries
    """
    results = {}
    
    for coin_name in config.get_all_coin_names():
        output_files = config.get_output_files(coin_name)
        news_file = output_files["news_json"]
        
        if news_file.exists():
            logger.info(f"Summarizing news for {coin_name.upper()}")
            summary = summarize_news_file(
                str(news_file),
                use_ollama=use_ollama,
                max_points=max_points,
            )
            results[coin_name] = summary
    
    logger.info(f"✓ Summarized news for {len(results)} coins")
    return results
