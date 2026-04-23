"""
Utility functions for the crypto data pipeline.
Includes logging setup, HTTP requests, and common helpers.
"""
import logging
import requests
from datetime import datetime
from typing import Optional
import config


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(logger_name: str) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        logger_name: Name of the logger
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(config.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# ============================================================================
# HTTP REQUESTS
# ============================================================================

def safe_get(url: str, timeout: int = config.REQUEST_TIMEOUT) -> Optional[requests.Response]:
    """
    Make a safe HTTP GET request with error handling.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Response object or None if request failed
    """
    logger = logging.getLogger(__name__)
    
    try:
        response = requests.get(url, headers=config.HEADERS, timeout=timeout)
        response.raise_for_status()
        logger.debug(f"✓ Successfully fetched: {url}")
        return response
    except requests.exceptions.Timeout:
        logger.error(f"[TIMEOUT] Request timed out: {url}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"[CONNECTION ERROR] Failed to connect: {url}")
        return None
    except requests.exceptions.HTTPError as e:
        logger.error(f"[HTTP ERROR] {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.error(f"[ERROR] Failed to fetch {url}: {str(e)}")
        return None


# ============================================================================
# DATETIME UTILITIES
# ============================================================================

def get_utc_timestamp():
    """Get current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"


def get_readable_timestamp():
    """Get current timestamp in readable format."""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


# ============================================================================
# DATA VALIDATION
# ============================================================================

def validate_coin_symbol(symbol: str) -> bool:
    """Check if coin symbol is valid."""
    return symbol in config.get_all_symbols()


def validate_coin_name(name: str) -> bool:
    """Check if coin name is valid."""
    return name.lower() in [c.lower() for c in config.get_all_coin_names()]


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_price(price: float, decimal_places: int = 2) -> str:
    """Format price with specified decimal places."""
    if price is None:
        return "N/A"
    return f"${price:,.{decimal_places}f}"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text


# ============================================================================
# PROGRESS REPORTING
# ============================================================================

def print_progress(current: int, total: int, prefix: str = "Progress", suffix: str = ""):
    """
    Print a progress bar.
    
    Args:
        current: Current item number
        total: Total items
        prefix: Prefix text
        suffix: Suffix text
    """
    percentage = current / total
    filled = int(50 * percentage)
    bar = "█" * filled + "░" * (50 - filled)
    print(f"\r{prefix} |{bar}| {percentage:.0%} {suffix}", end="", flush=True)
    if current == total:
        print()  # Newline when complete


def print_section_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)
