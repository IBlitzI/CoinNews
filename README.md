# Cryptocurrency Multi-Coin Data Pipeline & AI Trading Signal Generator

> **Note:** This project was developed as a proof-of-concept for integrating local LLM models (Ollama) with cryptocurrency data analysis. The AI components are experimental and optional.

Multi-coin crypto data pipeline with news scraping, price analysis, chart generation, and AI trading signals.

**Supported Coins:** Bitcoin, Ethereum, Solana, Ripple

## Features

- Multi-coin support with minimal configuration
- News scraping from CryptoSlate
- Live price data from Binance API
- Chart generation & visualization
- JSON/CSV export
- AI sentiment analysis (optional, Ollama)
- Trading signal generation (BUY/SELL/HOLD)

## Quick Start

**Install:**
```bash
pip install -r requirements.txt
```

**Run all coins:**
```bash
python main.py
```

**Run specific coins:**
```bash
python main.py --coins bitcoin,ethereum,solana
```

**See QUICKSTART.md for more examples.**

## Output

Data saved to `data/raw/{coin_name}/`:
- `news.json` - Structured articles
- `news.csv` - Tabular format  
- `chart.png` - Price chart
- `price.json` - Live prices

## Project Structure

```
├── config.py          # Coin configurations
├── data_fetcher.py    # Binance API
├── news_scraper.py    # Web scraping
├── chart_generator.py # Visualization
├── storage_manager.py # JSON/CSV export
├── ai/                # AI processing (optional)
└── main.py            # Pipeline orchestrator
```

## Adding New Coins

Edit `config.py` and add to `COINS` list:
```python
{
    "symbol": "DOGEUSDT",
    "name": "dogecoin",
    "display_name": "Dogecoin",
    "news_url": "https://cryptoslate.com/news/dogecoin/",
    "coin_url": "https://cryptoslate.com/coins/dogecoin/",
}
```

## Logs

```bash
tail -f data/logs/pipeline.log
```

## License

MIT
5. Test with all supported coins

