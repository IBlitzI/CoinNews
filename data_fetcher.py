"""
Data fetcher module for retrieving cryptocurrency data from Binance.
Handles price data, historical candles, and market information.
"""
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import pandas as pd
from binance import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

import config
import utils

logger = utils.setup_logging(__name__)


# ============================================================================
# BINANCE CLIENT INITIALIZATION
# ============================================================================

def get_binance_client() -> Client:
    """
    Initialize and return Binance API client.
    Uses default API keys (public market data access).
    
    Returns:
        Binance Client instance
    """
    try:
        client = Client()
        logger.info("✓ Binance client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to initialize Binance client: {str(e)}")
        raise


# ============================================================================
# PRICE DATA FETCHING
# ============================================================================

def get_current_price(symbol: str) -> Optional[float]:
    """
    Fetch current price for a cryptocurrency from Binance.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        
    Returns:
        Current price or None if failed
    """
    try:
        client = get_binance_client()
        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker["price"])
        logger.info(f"✓ {symbol} current price: {utils.format_price(price)}")
        return price
    except BinanceAPIException as e:
        logger.error(f"❌ Binance API error for {symbol}: {e.status_code} {e.message}")
        return None
    except BinanceRequestException as e:
        logger.error(f"❌ Binance request error for {symbol}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching price for {symbol}: {str(e)}")
        return None


def get_24h_stats(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch 24-hour statistics for a cryptocurrency.
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        Dictionary with 24h stats or None if failed
    """
    try:
        client = get_binance_client()
        stats = client.get_ticker(symbol=symbol)
        return {
            "symbol": stats.get("symbol"),
            "price_change": float(stats.get("priceChange", 0)),
            "price_change_percent": float(stats.get("priceChangePercent", 0)),
            "high": float(stats.get("highPrice", 0)),
            "low": float(stats.get("lowPrice", 0)),
            "volume": float(stats.get("volume", 0)),
            "quote_volume": float(stats.get("quoteAssetVolume", 0)),
        }
    except Exception as e:
        logger.error(f"❌ Failed to fetch 24h stats for {symbol}: {str(e)}")
        return None


# ============================================================================
# HISTORICAL DATA FETCHING
# ============================================================================

def get_klines_dataframe(
    symbol: str,
    interval: str = config.BINANCE_KLINES_INTERVAL,
    limit: int = config.BINANCE_KLINES_LIMIT,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV (candlestick) data from Binance and return as DataFrame.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        interval: Kline interval (e.g., '1m', '5m', '1h', '1d')
        limit: Number of candles to retrieve
        
    Returns:
        DataFrame with OHLCV data or None if failed
    """
    try:
        client = get_binance_client()
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        
        if not klines:
            logger.warning(f"⚠ No kline data returned for {symbol}")
            return None
        
        # Create DataFrame
        df = pd.DataFrame(
            klines,
            columns=[
                "open_time", "open", "high", "low", "close",
                "volume", "close_time", "quote_asset_volume",
                "number_of_trades", "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume", "ignore"
            ]
        )
        
        # Convert timestamp to datetime
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
        
        # Convert price and volume columns to float
        for col in ["open", "high", "low", "close", "volume", "quote_asset_volume"]:
            df[col] = df[col].astype(float)
        
        logger.info(f"✓ Fetched {len(df)} {interval} candles for {symbol}")
        return df
    
    except BinanceAPIException as e:
        logger.error(f"❌ Binance API error for {symbol}: {e.message}")
        return None
    except BinanceRequestException as e:
        logger.error(f"❌ Binance request error for {symbol}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching klines for {symbol}: {str(e)}")
        return None


def get_price_summary(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive price summary for a coin.
    Combines current price, 24h stats, and historical data.
    
    Args:
        symbol: Trading pair symbol
        
    Returns:
        Dictionary with comprehensive price data or None if failed
    """
    try:
        current_price = get_current_price(symbol)
        if current_price is None:
            return None
        
        stats_24h = get_24h_stats(symbol)
        df = get_klines_dataframe(symbol, interval="1h", limit=24)
        
        summary = {
            "symbol": symbol,
            "fetched_at": utils.get_utc_timestamp(),
            "current_price": current_price,
            "price_change_24h": stats_24h.get("price_change") if stats_24h else None,
            "price_change_percent_24h": stats_24h.get("price_change_percent") if stats_24h else None,
            "high_24h": stats_24h.get("high") if stats_24h else None,
            "low_24h": stats_24h.get("low") if stats_24h else None,
            "volume_24h": stats_24h.get("volume") if stats_24h else None,
        }
        
        # Add additional stats from historical data
        if df is not None and not df.empty:
            summary.update({
                "open_price_24h": df.iloc[0]["open"],
                "high_price_24h": df["high"].max(),
                "low_price_24h": df["low"].min(),
            })
        
        logger.debug(f"✓ Price summary compiled for {symbol}")
        return summary
    
    except Exception as e:
        logger.error(f"❌ Failed to compile price summary for {symbol}: {str(e)}")
        return None


# ============================================================================
# MULTI-COIN DATA FETCHING
# ============================================================================

def fetch_data_for_coins(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch data for multiple coins.
    
    Args:
        symbols: List of trading pair symbols
        
    Returns:
        Dictionary mapping symbols to their data
    """
    results = {}
    total = len(symbols)
    
    for idx, symbol in enumerate(symbols, start=1):
        logger.info(f"Fetching Binance data for {symbol} ({idx}/{total})")
        data = get_price_summary(symbol)
        if data:
            results[symbol] = data
    
    logger.info(f"✓ Successfully fetched data for {len(results)}/{total} coins")
    return results
