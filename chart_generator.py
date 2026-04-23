"""
Chart generator module for visualizing cryptocurrency price data.
Generates price charts from Binance candlestick data.
"""
import logging
from typing import Optional
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import config
import data_fetcher
import utils

logger = utils.setup_logging(__name__)


# ============================================================================
# CHART GENERATION
# ============================================================================

def generate_price_chart(
    symbol: str,
    output_file: Path,
    interval: str = config.BINANCE_KLINES_INTERVAL,
    limit: int = config.BINANCE_KLINES_LIMIT,
    title_suffix: str = "",
) -> Optional[Path]:
    """
    Generate a price chart from Binance candlestick data.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        output_file: Path to save the chart PNG
        interval: Kline interval (e.g., '1h', '1d')
        limit: Number of candles to retrieve
        title_suffix: Additional text to append to chart title
        
    Returns:
        Path to the generated chart or None if failed
    """
    try:
        logger.info(f"Generating price chart for {symbol}")
        
        # Fetch kline data
        df = data_fetcher.get_klines_dataframe(symbol, interval, limit)
        if df is None or df.empty:
            logger.error(f"❌ Failed to fetch kline data for {symbol}")
            return None
        
        # Create figure and plot
        plt.figure(figsize=config.CHART_FIGURE_SIZE, dpi=config.CHART_DPI)
        
        # Plot close price
        plt.plot(
            df["open_time"],
            df["close"],
            linewidth=2,
            label="Close Price",
            color="#1f77b4"
        )
        
        # Add high/low range as shaded area
        plt.fill_between(
            df["open_time"],
            df["low"],
            df["high"],
            alpha=0.2,
            color="#1f77b4",
            label="Daily Range"
        )
        
        # Formatting
        title = f"{symbol} Price Chart ({interval.upper()})"
        if title_suffix:
            title += f" - {title_suffix}"
        
        plt.title(title, fontsize=14, fontweight="bold")
        plt.xlabel("Time", fontsize=11)
        plt.ylabel("Price (USDT)", fontsize=11)
        plt.grid(True, alpha=0.3, linestyle="--")
        plt.legend(loc="upper left", fontsize=10)
        
        # Format x-axis dates
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45, ha="right")
        
        # Add price statistics as text
        current_price = df["close"].iloc[-1]
        min_price = df["low"].min()
        max_price = df["high"].max()
        change = df["close"].iloc[-1] - df["close"].iloc[0]
        change_pct = (change / df["close"].iloc[0] * 100) if df["close"].iloc[0] != 0 else 0
        
        stats_text = f"Current: ${current_price:.2f} | Min: ${min_price:.2f} | Max: ${max_price:.2f} | Change: {change_pct:+.2f}%"
        plt.figtext(0.5, 0.02, stats_text, ha="center", fontsize=9, style="italic", alpha=0.7)
        
        plt.tight_layout()
        
        # Save chart
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=config.CHART_DPI, bbox_inches="tight")
        plt.close()
        
        logger.info(f"✓ Chart saved: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"❌ Error generating chart for {symbol}: {str(e)}")
        plt.close()
        return None


def generate_comparison_chart(
    symbols: list[str],
    output_file: Path,
    interval: str = config.BINANCE_KLINES_INTERVAL,
    limit: int = config.BINANCE_KLINES_LIMIT,
) -> Optional[Path]:
    """
    Generate a comparison chart for multiple coins (normalized close prices).
    
    Args:
        symbols: List of trading pair symbols
        output_file: Path to save the chart PNG
        interval: Kline interval
        limit: Number of candles to retrieve
        
    Returns:
        Path to the generated chart or None if failed
    """
    try:
        logger.info(f"Generating comparison chart for {len(symbols)} symbols")
        
        # Fetch data for all symbols
        all_dfs = {}
        for symbol in symbols:
            df = data_fetcher.get_klines_dataframe(symbol, interval, limit)
            if df is not None and not df.empty:
                all_dfs[symbol] = df
        
        if not all_dfs:
            logger.error("❌ Failed to fetch data for any symbol")
            return None
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), dpi=config.CHART_DPI)
        
        # Plot 1: Absolute prices
        ax1.set_title("Price Comparison (Absolute)", fontsize=12, fontweight="bold")
        for symbol, df in all_dfs.items():
            ax1.plot(df["open_time"], df["close"], linewidth=2, label=symbol, marker="o", markersize=3)
        ax1.set_ylabel("Price (USDT)")
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Plot 2: Normalized prices (% change)
        ax2.set_title("Price Comparison (Normalized % Change)", fontsize=12, fontweight="bold")
        for symbol, df in all_dfs.items():
            first_price = df["close"].iloc[0]
            pct_change = ((df["close"] - first_price) / first_price * 100)
            ax2.plot(df["open_time"], pct_change, linewidth=2, label=symbol, marker="o", markersize=3)
        ax2.set_xlabel("Time")
        ax2.set_ylabel("Change (%)")
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.axhline(y=0, color="black", linestyle="--", alpha=0.5)
        
        # Format x-axis
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate(rotation=45, ha="right")
        
        plt.tight_layout()
        
        # Save chart
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=config.CHART_DPI, bbox_inches="tight")
        plt.close()
        
        logger.info(f"✓ Comparison chart saved: {output_file}")
        return output_file
    
    except Exception as e:
        logger.error(f"❌ Error generating comparison chart: {str(e)}")
        plt.close()
        return None


# ============================================================================
# BATCH CHART GENERATION
# ============================================================================

def generate_charts_for_coins(coin_symbols: list[str]) -> dict[str, Optional[Path]]:
    """
    Generate price charts for multiple coins.
    
    Args:
        coin_symbols: List of coin symbols
        
    Returns:
        Dictionary mapping symbols to chart file paths
    """
    results = {}
    total = len(coin_symbols)
    
    for idx, symbol in enumerate(coin_symbols, start=1):
        logger.info(f"Generating chart for {symbol} ({idx}/{total})")
        output_file = config.get_output_files(symbol.replace("USDT", "").lower())["chart_png"]
        
        chart_path = generate_price_chart(symbol, output_file)
        results[symbol] = chart_path
    
    successful = sum(1 for p in results.values() if p is not None)
    logger.info(f"✓ Generated {successful}/{total} charts")
    
    return results
