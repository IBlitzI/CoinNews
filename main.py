"""
Main orchestrator for the multi-coin cryptocurrency data pipeline.

This module coordinates:
1. News scraping for all configured coins
2. Price data fetching from Binance
3. Chart generation
4. Data persistence to multiple formats

Usage:
    python main.py                    # Run pipeline for all coins
    python main.py --coins BTC,SOL   # Run for specific coins
    python main.py --help            # Show help
"""
import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

import config
import utils
import data_fetcher
import news_scraper
import chart_generator
import storage_manager

logger = utils.setup_logging(__name__)

# AI layer imports (optional - graceful degradation if not available)
try:
    from ai.input_builder import AIInputBuilder
    from ai.sentiment import SentimentAnalyzer
    from ai.summarizer import NewsSummarizer
    from ai.llava_agent import LLaVAChartAnalyzer
    from ai.decision_engine import DecisionEngine, generate_trading_decision
    AI_LAYER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ AI layer not available: {str(e)}")
    AI_LAYER_AVAILABLE = False


# ============================================================================
# PIPELINE ORCHESTRATION
# ============================================================================

class CryptoPipeline:
    """Main pipeline orchestrator for multi-coin data collection."""
    
    def __init__(self, coin_names: Optional[List[str]] = None):
        """
        Initialize pipeline with optional coin filter.
        
        Args:
            coin_names: List of coin names to process (None = all coins)
        """
        self.results = {}
        self.errors = []
        
        if coin_names:
            # Filter coins by name
            self.coins = [c for c in config.COINS if c["name"].lower() in [n.lower() for n in coin_names]]
            if not self.coins:
                logger.error(f"❌ Invalid coin names: {coin_names}")
                self.coins = config.COINS
        else:
            self.coins = config.COINS
        
        logger.info(f"Pipeline initialized for {len(self.coins)} coins: {[c['name'].upper() for c in self.coins]}")
    
    
    def run_complete_pipeline(self) -> Dict[str, Dict[str, Any]]:
        """
        Execute the complete pipeline for all configured coins.
        
        Returns:
            Dictionary with results for each coin
        """
        utils.print_section_header(f"CRYPTOCURRENCY DATA PIPELINE")
        logger.info(f"Starting pipeline at {utils.get_readable_timestamp()}")
        
        for idx, coin_config in enumerate(self.coins, start=1):
            coin_name = coin_config["name"]
            symbol = coin_config["symbol"]
            
            utils.print_section_header(f"Processing {coin_name.upper()} ({idx}/{len(self.coins)})")
            logger.info(f"Symbol: {symbol}")
            
            coin_result = self.process_single_coin(coin_config)
            self.results[coin_name] = coin_result
        
        # Run AI analysis if available
        if AI_LAYER_AVAILABLE:
            self.run_ai_analysis()
        
        # Generate reports
        self._generate_reports()
        
        logger.info(f"✓ Pipeline completed at {utils.get_readable_timestamp()}")
        return self.results
    
    
    def process_single_coin(self, coin_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single coin through the complete pipeline.
        
        Args:
            coin_config: Coin configuration dictionary
            
        Returns:
            Dictionary with processing results
        """
        coin_name = coin_config["name"]
        symbol = coin_config["symbol"]
        news_url = coin_config["news_url"]
        
        result = {
            "coin": coin_name,
            "symbol": symbol,
            "status": "pending",
            "price": None,
            "articles": [],
            "files": {},
            "error": None,
        }
        
        try:
            # Step 1: Fetch price data
            logger.info(f"\n[1/4] Fetching price data for {symbol}...")
            price = data_fetcher.get_current_price(symbol)
            price_data = data_fetcher.get_price_summary(symbol)
            result["price"] = price
            result["price_data"] = price_data
            
            # Step 2: Scrape news
            logger.info(f"\n[2/4] Scraping news for {coin_name}...")
            articles = news_scraper.scrape_news_for_coin(news_url, coin_name)
            result["articles"] = articles
            
            # Step 3: Generate chart
            logger.info(f"\n[3/4] Generating chart for {symbol}...")
            output_files = config.get_output_files(coin_name)
            chart_path = chart_generator.generate_price_chart(
                symbol,
                output_files["chart_png"],
                interval="1h",
                limit=100,
            )
            if chart_path:
                result["files"]["chart"] = chart_path
            
            # Step 4: Save data
            logger.info(f"\n[4/4] Saving data for {coin_name}...")
            saved_files = storage_manager.save_all_data(
                coin_name,
                articles,
                price,
                price_data,
            )
            result["files"].update(saved_files)
            
            result["status"] = "success"
            logger.info(f"✅ Successfully processed {coin_name.upper()}")
        
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"❌ Error processing {coin_name}: {str(e)}", exc_info=True)
            self.errors.append((coin_name, str(e)))
        
        return result
    
    
    def run_ai_analysis(self):
        """
        Run AI analysis on collected data to generate trading signals.
        Orchestrates: summarization, sentiment, chart analysis, and decision making.
        """
        try:
            utils.print_section_header("AI ANALYSIS LAYER: Generating Trading Signals")
            logger.info("Starting AI analysis...")
            
            # Initialize AI components
            summarizer = NewsSummarizer(use_ollama=True)
            chart_analyzer = LLaVAChartAnalyzer()
            
            ai_inputs = {}
            sentiments = {}
            chart_analyses = {}
            trading_decisions = {}
            
            # Process each coin
            for coin_name in self.results.keys():
                if self.results[coin_name]["status"] != "success":
                    logger.warning(f"⚠ Skipping AI analysis for {coin_name} (data collection failed)")
                    continue
                
                try:
                    logger.info(f"\n[AI] Processing {coin_name.upper()}...")
                    
                    # Build AI input (this already includes sentiment analysis)
                    logger.info(f"  → Building AI input...")
                    ai_input = AIInputBuilder.build_ai_inputs_from_files(coin_name)
                    if not ai_input:
                        logger.warning(f"⚠ Failed to build AI input for {coin_name}")
                        continue
                    
                    ai_inputs[coin_name] = ai_input
                    
                    # Extract sentiment from AI input
                    sentiment = {
                        "overall_sentiment": ai_input.get("sentiment", "neutral"),
                        "average_confidence": ai_input.get("sentiment_confidence", 0.5),
                        "positive_count": ai_input.get("sentiment_positive_count", 0),
                        "negative_count": ai_input.get("sentiment_negative_count", 0),
                    }
                    sentiments[coin_name] = sentiment
                    
                    # Analyze chart
                    logger.info(f"  → Analyzing chart...")
                    chart_analysis = chart_analyzer.analyze_chart(
                        config.get_output_files(coin_name)["chart_png"],
                        ai_input
                    )
                    chart_analyses[coin_name] = chart_analysis
                    
                    # Generate trading decision
                    logger.info(f"  → Generating trading decision...")
                    decision = generate_trading_decision(ai_input, sentiment, chart_analysis)
                    trading_decisions[coin_name] = decision
                    
                    # Log decision
                    action = decision.get("action", "hold").upper()
                    confidence = decision.get("confidence", 0)
                    logger.info(f"  ✓ Decision: {action} (Confidence: {confidence}%)")
                    
                    # Store in results
                    self.results[coin_name]["ai_decision"] = decision
                    self.results[coin_name]["ai_input"] = ai_input
                    self.results[coin_name]["ai_sentiment"] = sentiment
                    self.results[coin_name]["ai_chart_analysis"] = chart_analysis
                    
                    # Save processed analysis to storage
                    storage_manager.save_processed_analysis(
                        coin_name,
                        ai_input,
                        sentiment,
                        chart_analysis,
                    )
                    
                    # Save trading signal
                    storage_manager.save_trading_signal(coin_name, decision)
                
                except Exception as e:
                    logger.error(f"❌ AI analysis error for {coin_name}: {str(e)}", exc_info=False)
                    self.results[coin_name]["ai_error"] = str(e)
            
            # Save trading signals
            if trading_decisions:
                logger.info("\nSaving trading signals...")
                self._save_trading_signals(trading_decisions)
                logger.info(f"✓ Generated trading signals for {len(trading_decisions)} coins")
            
            logger.info(f"✓ AI analysis completed at {utils.get_readable_timestamp()}")
        
        except Exception as e:
            logger.error(f"❌ Critical error in AI analysis: {str(e)}", exc_info=True)
    
    
    def _save_trading_signals(self, decisions: Dict[str, Dict[str, Any]]):
        """
        Save trading decisions to JSON files.
        
        Args:
            decisions: Dictionary mapping coin names to trading decisions
        """
        import json
        
        for coin_name, decision in decisions.items():
            try:
                output_files = config.get_output_files(coin_name)
                signals_path = output_files.get("signals_json")
                
                if signals_path:
                    signals_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(signals_path, "w") as f:
                        json.dump({
                            "timestamp": utils.get_utc_timestamp(),
                            "coin": coin_name,
                            "decision": decision,
                        }, f, indent=2, default=str)
                    
                    logger.info(f"  → Saved signal for {coin_name}: {signals_path}")
            
            except Exception as e:
                logger.error(f"❌ Error saving signal for {coin_name}: {str(e)}")
    
    
    def _generate_reports(self):
        """Generate summary reports after pipeline execution."""
        logger.info("\n" + "=" * 80)
        logger.info("GENERATING REPORTS")
        logger.info("=" * 80)
        
        # Execution summary
        storage_manager.generate_summary_report(self.results)
        
        # Storage statistics
        storage_manager.generate_storage_report()
        
        # Error summary
        if self.errors:
            logger.warning(f"\n⚠ {len(self.errors)} error(s) occurred during pipeline execution:")
            for coin_name, error in self.errors:
                logger.warning(f"  - {coin_name}: {error}")


# ============================================================================
# CLI INTERFACE
# ============================================================================

def create_argument_parser():
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Multi-coin cryptocurrency data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run for all coins
  python main.py --coins BTC,ETH,SOL     # Run for specific coins
  python main.py --coins bitcoin ethereum # Run by name (case-insensitive)
        """
    )
    
    parser.add_argument(
        "--coins",
        type=str,
        default=None,
        help="Comma-separated list of coin names or symbols (e.g., 'BTC,ETH,SOL' or 'bitcoin,ethereum,solana')",
    )
    
    parser.add_argument(
        "--list-coins",
        action="store_true",
        help="List all available coins and exit",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    
    return parser


def list_available_coins():
    """Display available coins and their symbols."""
    print("\n" + "=" * 60)
    print("AVAILABLE COINS")
    print("=" * 60)
    print(f"{'Name':<20} {'Symbol':<12} {'News URL'}")
    print("-" * 60)
    
    for coin in config.COINS:
        print(f"{coin['name']:<20} {coin['symbol']:<12} {coin['news_url']}")
    
    print("=" * 60 + "\n")


def parse_coin_argument(coin_arg: str) -> List[str]:
    """
    Parse coin argument from CLI.
    Supports both names and symbols, comma-separated.
    
    Args:
        coin_arg: Coin names or symbols (comma-separated)
        
    Returns:
        List of valid coin names
    """
    coin_list = [c.strip().upper() for c in coin_arg.split(",")]
    valid_coins = []
    
    for coin_input in coin_list:
        # Try as symbol first
        config_obj = config.get_coin_config(coin_input)
        if config_obj:
            valid_coins.append(config_obj["name"])
            continue
        
        # Try as name
        config_obj = config.get_coin_by_name(coin_input)
        if config_obj:
            valid_coins.append(config_obj["name"])
            continue
        
        logger.warning(f"⚠ Unknown coin: {coin_input}")
    
    return valid_coins


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the pipeline."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle --list-coins
    if args.list_coins:
        list_available_coins()
        return
    
    # Adjust logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse coin argument
    coin_names = None
    if args.coins:
        coin_names = parse_coin_argument(args.coins)
        if not coin_names:
            logger.error("❌ No valid coins specified")
            return
    
    # Run pipeline
    try:
        pipeline = CryptoPipeline(coin_names=coin_names)
        results = pipeline.run_complete_pipeline()
        
        # Print final summary
        successful = sum(1 for r in results.values() if r["status"] == "success")
        total = len(results)
        print(f"\n[OK] Pipeline completed: {successful}/{total} coins processed successfully\n")
        return 0
    
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"[ERR] Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = main()
    sys.exit(exit_code)
