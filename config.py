"""
Configuration file for multi-coin crypto data pipeline.
Centralized settings for coins, URLs, API parameters, and output structure.
"""
import os
from pathlib import Path

# ============================================================================
# COIN CONFIGURATION
# ============================================================================

COINS = [
    {
        "symbol": "BTCUSDT",
        "name": "bitcoin",
        "display_name": "Bitcoin",
        "news_url": "https://cryptoslate.com/news/bitcoin/",
        "coin_url": "https://cryptoslate.com/coins/bitcoin/",
    },
    {
        "symbol": "ETHUSDT",
        "name": "ethereum",
        "display_name": "Ethereum",
        "news_url": "https://cryptoslate.com/news/ethereum/",
        "coin_url": "https://cryptoslate.com/coins/ethereum/",
    },
    {
        "symbol": "SOLUSDT",
        "name": "solana",
        "display_name": "Solana",
        "news_url": "https://cryptoslate.com/news/solana/",
        "coin_url": "https://cryptoslate.com/coins/solana/",
    },
    {
        "symbol": "XRPUSDT",
        "name": "ripple",
        "display_name": "Ripple (XRP)",
        "news_url": "https://cryptoslate.com/news/xrp/",
        "coin_url": "https://cryptoslate.com/coins/xrp/",
    },
]

# ============================================================================
# WEB SCRAPING SETTINGS
# ============================================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

REQUEST_TIMEOUT = 15
DELAY_BETWEEN_REQUESTS = 1.0
MAX_ARTICLES = 25

# CSS Selectors for CryptoSlate news scraping
NEWS_SELECTORS = [
    "article.cs-category-secondary__card a[href]",  # Featured articles
    "a.list-post-grid__link[href]",                 # Grid articles
]

# ============================================================================
# BINANCE API SETTINGS
# ============================================================================

BINANCE_KLINES_INTERVAL = "1h"  # 1-hour candles
BINANCE_KLINES_LIMIT = 100      # Retrieve last 100 candles
BINANCE_TIMEOUT = 10

# ============================================================================
# FOLDER STRUCTURE
# ============================================================================

BASE_DIR = Path(__file__).parent.absolute()

# Data directories
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SIGNALS_DIR = DATA_DIR / "signals"
LOGS_DIR = DATA_DIR / "logs"

# Ensure directories exist
for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, SIGNALS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def get_coin_output_dir(coin_name):
    """Get the output directory for a specific coin."""
    coin_dir = RAW_DATA_DIR / coin_name.lower()
    coin_dir.mkdir(parents=True, exist_ok=True)
    return coin_dir


def get_output_files(coin_name):
    """Get output file paths for a specific coin."""
    coin_dir = get_coin_output_dir(coin_name)
    return {
        "news_json": coin_dir / "news.json",
        "news_csv": coin_dir / "news.csv",
        "chart_png": coin_dir / "chart.png",
        "price_json": coin_dir / "price.json",
        "signals_json": coin_dir / "signals.json",
    }


# ============================================================================
# LOGGING SETTINGS
# ============================================================================

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / "pipeline.log"

# ============================================================================
# CHART GENERATION SETTINGS
# ============================================================================

CHART_FIGURE_SIZE = (12, 6)
CHART_DPI = 100
CHART_STYLE = "default"

# ============================================================================
# OLLAMA AI SETTINGS (Local LLM & Vision Models)
# ============================================================================

# Ollama Server Configuration
OLLAMA_ENABLED = True
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TIMEOUT = 180  # seconds (increased from 120 for better stability)
OLLAMA_VERBOSE = False

# Ollama Models
OLLAMA_TEXT_MODEL = "llama3"      # For text analysis & summarization
OLLAMA_VISION_MODEL = "llava"     # For chart analysis

# Model Parameters
OLLAMA_TEMPERATURE = 0.7
OLLAMA_TOP_P = 0.9

# ============================================================================
# NEWS SUMMARIZATION SETTINGS
# ============================================================================

SUMMARIZER_ENABLED = True
SUMMARIZER_USE_OLLAMA = True
SUMMARIZER_MAX_POINTS = 7
SUMMARIZER_MAX_CHARS = 500

# ============================================================================
# SENTIMENT ANALYSIS SETTINGS
# ============================================================================

SENTIMENT_ANALYSIS_ENABLED = True
# PRIMARY METHOD: Llama 3 via Ollama for accurate market sentiment
# Fallback: Lightweight keyword analysis if Ollama unavailable
SENTIMENT_USE_OLLAMA = True
SENTIMENT_MODEL = "llama3"  # Primary model for sentiment analysis
SENTIMENT_USE_LLAMA3 = True  # Use Llama 3 for sentiment (not keywords)
SENTIMENT_CONFIDENCE_THRESHOLD = 0.5

# Positive keywords (only used if Ollama unavailable)
POSITIVE_KEYWORDS = {
    "bull": 2.0, "bullish": 2.5, "surge": 1.5, "moon": 2.0,
    "pump": 1.0, "breakout": 1.5, "rally": 1.5, "gain": 1.0,
    "growth": 1.5, "up": 1.0, "higher": 1.0, "increase": 1.0,
    "adopt": 1.5, "partnership": 1.5, "approval": 2.0,
}

# Negative keywords (only used if Ollama unavailable)
NEGATIVE_KEYWORDS = {
    "bear": -2.0, "bearish": -2.5, "crash": -2.0, "dump": -1.0,
    "collapse": -2.0, "fear": -1.5, "loss": -1.5, "down": -1.0,
    "lower": -1.0, "decrease": -1.0, "decline": -1.5, "risk": -1.0,
    "hack": -2.0, "fraud": -2.0, "scandal": -2.0, "ban": -1.5,
}

# ============================================================================
# CHART ANALYSIS SETTINGS (LLaVA Vision)
# ============================================================================

CHART_ANALYSIS_ENABLED = True
# NOTE: LLaVA image interpretation is unreliable
# Confidence scores are reduced (capped at 0.35)
# Chart analysis weight reduced in decision engine (0.15 from 0.35)
CHART_ANALYSIS_USE_OLLAMA = True
CHART_ANALYSIS_CONFIDENCE_REDUCTION = 0.4  # Reduce to 40% of original confidence

# ============================================================================
# TRADING SIGNAL GENERATION SETTINGS
# ============================================================================

SIGNAL_GENERATION_ENABLED = True

# Decision Engine Thresholds
SIGNAL_BUY_THRESHOLD = 0.65          # composite_score >= 0.65
SIGNAL_SELL_THRESHOLD = -0.60        # composite_score <= -0.60
SIGNAL_HOLD_ZONE = (-0.60, 0.65)     # Between thresholds

# Signal Weights (must sum to 1.0)
# Adjusted: Llama 3 sentiment increased, LLaVA chart reduced, price trend increased
SIGNAL_WEIGHTS = {
    "sentiment": 0.45,     # Llama 3 sentiment (45%, increased from 30%)
    "chart": 0.15,         # Technical analysis (15%, reduced from 35% - LLaVA unreliable)
    "trend": 0.35,         # Price trend (35%, increased from 20%)
    "risk": -0.05,         # Risk adjustment (-5%, reduced from -15%)
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_coin_config(symbol):
    """Get configuration for a specific coin by symbol."""
    for coin in COINS:
        if coin["symbol"] == symbol:
            return coin
    return None


def get_coin_by_name(name):
    """Get configuration for a specific coin by name."""
    for coin in COINS:
        if coin["name"].lower() == name.lower():
            return coin
    return None


def get_all_coin_names():
    """Get list of all available coin names."""
    return [coin["name"] for coin in COINS]


def get_all_symbols():
    """Get list of all available coin symbols."""
    return [coin["symbol"] for coin in COINS]
