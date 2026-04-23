"""
Storage manager module for handling data persistence.
Manages saving articles, prices, and metadata to JSON and CSV formats.
"""
import logging
import json
import csv
from typing import Dict, List, Any, Optional
from pathlib import Path

import config
import utils

logger = utils.setup_logging(__name__)


# ============================================================================
# NEWS STORAGE
# ============================================================================

def save_articles_to_json(
    coin_name: str,
    articles: List[Dict[str, Any]],
    price: Optional[float] = None,
) -> Optional[Path]:
    """
    Save articles to a JSON file.
    
    Args:
        coin_name: Name of the coin
        articles: List of article dictionaries
        price: Current price to include in metadata
        
    Returns:
        Path to the saved file or None if failed
    """
    try:
        output_files = config.get_output_files(coin_name)
        output_file = output_files["news_json"]
        
        data = {
            "coin": coin_name.upper(),
            "price_usdt": price,
            "fetched_at": utils.get_utc_timestamp(),
            "article_count": len(articles),
            "articles": articles,
        }
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Saved {len(articles)} articles to JSON: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"❌ Error saving articles to JSON for {coin_name}: {str(e)}")
        return None


def save_articles_to_csv(
    coin_name: str,
    articles: List[Dict[str, Any]],
    price: Optional[float] = None,
) -> Optional[Path]:
    """
    Save articles to a CSV file.
    
    Args:
        coin_name: Name of the coin
        articles: List of article dictionaries
        price: Current price to include in header
        
    Returns:
        Path to the saved file or None if failed
    """
    try:
        output_files = config.get_output_files(coin_name)
        output_file = output_files["news_csv"]
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            
            # Header with metadata
            writer.writerow([f"{coin_name.upper()} News Data"])
            writer.writerow([])
            writer.writerow([f"Price (USDT)", price or "N/A"])
            writer.writerow([f"Fetched At", utils.get_utc_timestamp()])
            writer.writerow([f"Total Articles", len(articles)])
            writer.writerow([])
            
            # Column headers
            writer.writerow(["title", "link", "source", "content", "fetched_at"])
            
            # Articles
            for article in articles:
                writer.writerow([
                    article.get("title", ""),
                    article.get("link", ""),
                    article.get("source", ""),
                    article.get("content", ""),
                    article.get("fetched_at", ""),
                ])
        
        logger.info(f"✓ Saved {len(articles)} articles to CSV: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"❌ Error saving articles to CSV for {coin_name}: {str(e)}")
        return None


# ============================================================================
# PRICE DATA STORAGE
# ============================================================================

def save_price_data(
    coin_name: str,
    price_data: Dict[str, Any],
) -> Optional[Path]:
    """
    Save price data to a JSON file.
    
    Args:
        coin_name: Name of the coin
        price_data: Dictionary with price information
        
    Returns:
        Path to the saved file or None if failed
    """
    try:
        output_files = config.get_output_files(coin_name)
        output_file = output_files["price_json"]
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(price_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Saved price data to: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"❌ Error saving price data for {coin_name}: {str(e)}")
        return None


# ============================================================================
# BATCH STORAGE
# ============================================================================

def save_all_data(
    coin_name: str,
    articles: List[Dict[str, Any]],
    price: Optional[float] = None,
    price_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[Path]]:
    """
    Save all data (articles and price) for a coin.
    
    Args:
        coin_name: Name of the coin
        articles: List of articles
        price: Current price
        price_data: Price data dictionary
        
    Returns:
        Dictionary with saved file paths
    """
    logger.info(f"Saving all data for {coin_name.upper()}")
    
    results = {
        "news_json": save_articles_to_json(coin_name, articles, price),
        "news_csv": save_articles_to_csv(coin_name, articles, price),
        "price_json": None,
    }
    
    if price_data:
        results["price_json"] = save_price_data(coin_name, price_data)
    
    return results


def generate_summary_report(
    pipeline_results: Dict[str, Dict[str, Any]],
    output_file: Optional[Path] = None,
) -> str:
    """
    Generate a summary report of the pipeline execution.
    
    Args:
        pipeline_results: Dictionary with results for each coin
        output_file: Optional file path to save report
        
    Returns:
        Report as string
    """
    try:
        lines = []
        lines.append("=" * 80)
        lines.append("CRYPTOCURRENCY DATA PIPELINE EXECUTION REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {utils.get_readable_timestamp()}")
        lines.append("")
        
        for coin_name, result in pipeline_results.items():
            lines.append(f"\n{coin_name.upper()}")
            lines.append("-" * 40)
            
            if "price" in result and result["price"]:
                lines.append(f"  Price:        {utils.format_price(result['price'])}")
            else:
                lines.append(f"  Price:        Failed to fetch")
            
            if "articles" in result:
                lines.append(f"  Articles:     {len(result['articles'])} scraped")
            else:
                lines.append(f"  Articles:     Failed to scrape")
            
            if "files" in result:
                lines.append(f"  Files saved:  {sum(1 for f in result['files'].values() if f)}")
            
            if "error" in result:
                lines.append(f"  Error:        {result['error']}")
        
        lines.append("\n" + "=" * 80)
        
        report = "\n".join(lines)
        
        # Print to console
        logger.info(report)
        
        # Save to file if requested
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"✓ Report saved to: {output_file}")
        
        return report
    
    except Exception as e:
        logger.error(f"❌ Error generating summary report: {str(e)}")
        return ""


# ============================================================================
# CLEANUP AND UTILITIES
# ============================================================================

def get_storage_statistics() -> Dict[str, Any]:
    """
    Get statistics about stored data.
    
    Returns:
        Dictionary with storage statistics
    """
    try:
        stats = {
            "raw_data_dir": str(config.RAW_DATA_DIR),
            "coins": {},
        }
        
        for coin_name in config.get_all_coin_names():
            output_files = config.get_output_files(coin_name)
            files_info = {}
            
            for file_type, file_path in output_files.items():
                if file_path.exists():
                    size_kb = file_path.stat().st_size / 1024
                    files_info[file_type] = {
                        "path": str(file_path),
                        "size_kb": round(size_kb, 2),
                    }
            
            if files_info:
                stats["coins"][coin_name] = files_info
        
        return stats
    
    except Exception as e:
        logger.error(f"❌ Error getting storage statistics: {str(e)}")
        return {}


# ============================================================================
# PROCESSED DATA STORAGE (AI Analysis, Sentiment, Processed Results)
# ============================================================================

def save_processed_analysis(
    coin_name: str,
    ai_input: Dict[str, Any],
    sentiment: Dict[str, Any],
    chart_analysis: Dict[str, Any],
) -> Optional[Path]:
    """
    Save processed AI analysis to the processed directory.
    
    Args:
        coin_name: Name of the coin
        ai_input: AI input builder data
        sentiment: Sentiment analysis
        chart_analysis: Chart analysis from LLaVA
        
    Returns:
        Path to the saved file or None if failed
    """
    try:
        processed_dir = config.PROCESSED_DATA_DIR / coin_name.lower()
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        analysis_file = processed_dir / "analysis.json"
        
        data = {
            "timestamp": utils.get_utc_timestamp(),
            "coin": coin_name.upper(),
            "ai_input": ai_input,
            "sentiment": sentiment,
            "chart_analysis": chart_analysis,
        }
        
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"✓ Saved processed analysis for {coin_name} to: {analysis_file}")
        return analysis_file
    
    except Exception as e:
        logger.error(f"❌ Error saving processed analysis for {coin_name}: {str(e)}")
        return None


def save_trading_signal(
    coin_name: str,
    decision: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Path]:
    """
    Save trading signal/decision to the signals directory.
    
    Args:
        coin_name: Name of the coin
        decision: Trading decision from decision engine
        metadata: Optional additional metadata
        
    Returns:
        Path to the saved file or None if failed
    """
    try:
        signals_dir = config.SIGNALS_DIR / coin_name.lower()
        signals_dir.mkdir(parents=True, exist_ok=True)
        
        signal_file = signals_dir / "signal.json"
        
        data = {
            "timestamp": utils.get_utc_timestamp(),
            "coin": coin_name.upper(),
            "decision": decision,
        }
        
        if metadata:
            data["metadata"] = metadata
        
        with open(signal_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"✓ Saved trading signal for {coin_name} to: {signal_file}")
        return signal_file
    
    except Exception as e:
        logger.error(f"❌ Error saving trading signal for {coin_name}: {str(e)}")
        return None


def generate_storage_report() -> str:
    """
    Generate a report of stored data.
    
    Returns:
        Report as string
    """
    try:
        stats = get_storage_statistics()
        lines = []
        
        lines.append("\n" + "=" * 80)
        lines.append("STORAGE STATISTICS")
        lines.append("=" * 80)
        
        for coin, data in stats.get("coins", {}).items():
            lines.append(f"\n{coin.upper()}:")
            total_size = 0
            for file_type, file_info in data.items():
                size = file_info["size_kb"]
                total_size += size
                lines.append(f"  {file_type:15} {size:8.2f} KB")
            lines.append(f"  {'Total':15} {total_size:8.2f} KB")
        
        lines.append("\n" + "=" * 80)
        
        report = "\n".join(lines)
        logger.info(report)
        return report
    
    except Exception as e:
        logger.error(f"❌ Error generating storage report: {str(e)}")
        return ""
