"""
News scraper module for fetching cryptocurrency news from CryptoSlate.
Generic implementation that works for any supported coin.
"""
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests

import config
import utils

logger = utils.setup_logging(__name__)


# ============================================================================
# NEWS FETCHING
# ============================================================================

def extract_article_links(html_content: str, base_url: str, max_links: int = config.MAX_ARTICLES) -> List[str]:
    """
    Extract article links from a CryptoSlate news listing page.
    
    Args:
        html_content: HTML content of the page
        base_url: Base URL for resolving relative links
        max_links: Maximum number of links to extract
        
    Returns:
        List of article URLs
    """
    try:
        soup = BeautifulSoup(html_content, "lxml")
        links = []
        
        # Try each selector until we have enough links
        for selector in config.NEWS_SELECTORS:
            for element in soup.select(selector):
                href = element.get("href")
                if href:
                    full_url = urljoin(base_url, href)
                    if full_url not in links:
                        links.append(full_url)
                
                if len(links) >= max_links:
                    logger.debug(f"✓ Extracted {len(links)} article links")
                    return links
        
        if not links:
            logger.warning("⚠ No article links found with available selectors")
        else:
            logger.debug(f"✓ Extracted {len(links)} article links")
        
        return links
    
    except Exception as e:
        logger.error(f"❌ Error extracting article links: {str(e)}")
        return []


def extract_article_content(html_content: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract article title and content from an article page.
    
    Args:
        html_content: HTML content of the article page
        
    Returns:
        Tuple of (title, content) or (None, None) if extraction failed
    """
    try:
        soup = BeautifulSoup(html_content, "lxml")
        
        # Extract title
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""
        
        # Extract content
        content_selectors = [
            "div.post",
            "article",
            "div.article-content",
        ]
        
        content_div = None
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                break
        
        if content_div:
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in content_div.find_all("p")
                if p.get_text(strip=True)
            ]
            content = "\n\n".join(paragraphs)
        else:
            # Fallback: get all paragraphs
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in soup.find_all("p")
                if p.get_text(strip=True)
            ]
            content = "\n\n".join(paragraphs)
        
        if not content:
            logger.warning("⚠ No content extracted from article")
            return title, None
        
        logger.debug(f"✓ Extracted article: {utils.truncate_text(title, 80)}")
        return title, content
    
    except Exception as e:
        logger.error(f"❌ Error extracting article content: {str(e)}")
        return None, None


# ============================================================================
# SCRAPING ORCHESTRATION
# ============================================================================

def scrape_news_for_coin(news_url: str, coin_name: str, max_articles: int = config.MAX_ARTICLES) -> List[Dict[str, Any]]:
    """
    Scrape news articles for a specific coin.
    
    Args:
        news_url: URL of the news listing page
        coin_name: Name of the coin (for logging)
        max_articles: Maximum number of articles to scrape
        
    Returns:
        List of article dictionaries with title, link, source, content, and timestamp
    """
    logger.info(f"Starting news scrape for {coin_name.upper()}")
    logger.debug(f"News URL: {news_url}")
    
    # Fetch listing page
    logger.info("Fetching news listing page...")
    response = utils.safe_get(news_url, timeout=config.REQUEST_TIMEOUT)
    if not response:
        logger.error(f"❌ Failed to fetch news listing page for {coin_name}")
        return []
    
    # Extract article links
    article_links = extract_article_links(response.text, news_url, max_links=max_articles)
    if not article_links:
        logger.warning(f"⚠ No article links found for {coin_name}")
        return []
    
    logger.info(f"Found {len(article_links)} articles for {coin_name}")
    
    # Fetch and parse each article
    articles = []
    for idx, link in enumerate(article_links, start=1):
        logger.info(f"[{idx}/{len(article_links)}] Scraping: {utils.truncate_text(link, 60)}")
        
        # Fetch article page
        article_response = utils.safe_get(link, timeout=config.REQUEST_TIMEOUT)
        if not article_response:
            logger.warning(f"  ⚠ Skipped: Failed to fetch article")
            continue
        
        # Extract content
        title, content = extract_article_content(article_response.text)
        if not content:
            logger.warning(f"  ⚠ Skipped: No content extracted")
            continue
        
        # Compile article data
        article = {
            "title": title or "No title",
            "link": link,
            "source": urlparse(link).netloc,
            "content": content,
            "fetched_at": utils.get_utc_timestamp(),
            "coin": coin_name.lower(),
        }
        articles.append(article)
        logger.debug(f"  ✓ Successfully scraped ({len(content)} chars)")
        
        # Respect rate limits
        time.sleep(config.DELAY_BETWEEN_REQUESTS)
    
    logger.info(f"✓ Scraped {len(articles)} articles for {coin_name}")
    return articles


def scrape_news_for_multiple_coins(coin_configs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scrape news for multiple coins.
    
    Args:
        coin_configs: List of coin configuration dictionaries
        
    Returns:
        Dictionary mapping coin names to lists of articles
    """
    results = {}
    total_coins = len(coin_configs)
    
    for idx, coin_config in enumerate(coin_configs, start=1):
        coin_name = coin_config["name"]
        news_url = coin_config["news_url"]
        
        logger.info(f"=== Processing {coin_name.upper()} ({idx}/{total_coins}) ===")
        articles = scrape_news_for_coin(news_url, coin_name)
        results[coin_name] = articles
    
    total_articles = sum(len(articles) for articles in results.values())
    logger.info(f"✓ Total articles scraped: {total_articles}")
    
    return results
