# Quick Start

## Prerequisites
- Python 3.8+
- Internet connection

## Install & Run

```bash
pip install -r requirements.txt
python main.py
```

## Output

Data saved to `data/raw/{coin_name}/`:
- `news.json` - Articles
- `news.csv` - CSV format
- `chart.png` - Price chart
- `price.json` - Price data

## Examples

**All coins:**
```bash
python main.py
```

**Specific coins:**
```bash
python main.py --coins bitcoin,ethereum
```

**View logs:**
```bash
tail -f data/logs/pipeline.log
```
# Run all coins with verbose logging
python main.py --verbose

# Run only Bitcoin (fastest test)
python main.py --coins bitcoin

# List available coins
python main.py --list-coins

# Get help with CLI options
python main.py --help
```

## Logs

Logs are saved to `data/logs/pipeline.log`:

```bash
# View last 20 lines
tail -20 data/logs/pipeline.log

# Real-time log watching
tail -f data/logs/pipeline.log

# View entire log
cat data/logs/pipeline.log
```

## Troubleshooting

### "Failed to fetch articles"
- Check internet connection
- CryptoSlate website might be down
- Try running again later

### "No module named 'binance'"
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

### "Permission denied" on Linux/macOS
```bash
chmod +x *.py
python main.py
```

### Slow performance
- Network latency (try again)
- Rate limiting (pipeline waits 1 second between requests)
- Normal: takes 1-3 min per coin

## What to Do With the Data

### 1. Analyze News Sentiment
```python
# Load the JSON
import json
with open('data/raw/bitcoin/news.json') as f:
    data = json.load(f)
    
# Analyze articles
for article in data['articles']:
    print(article['title'])
```

### 2. Track Price Changes
```python
# Open price.json to see:
# - Current price
# - 24h change
# - High/low prices
# - Trading volume
```

### 3. View Price Charts
```bash
# Simply open the PNG file
# Shows price movement over last 100 hours
```

### 4. Integrate With Workflows
```python
# Use the JSON/CSV files in:
# - Dashboards
# - Databases
# - Analytics tools
# - Trading bots
```

## Advanced Usage

### Run Daily

**Windows** (Task Scheduler):
1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at desired time
4. Action: Start program: `python`
5. Arguments: `main.py --coins bitcoin,ethereum`

**Linux/macOS** (Cron):
```bash
# Run daily at 8 AM
0 8 * * * cd /path/to/CoinNews && python main.py
```

### Customize Configuration

Edit `config.py` to:
- Change article count: `MAX_ARTICLES = 50`
- Adjust rate limits: `DELAY_BETWEEN_REQUESTS = 0.5`
- Add new coins (see configuration section)
- Format output differently

### Add Your Own Coins

In `config.py`, add to the `COINS` list:
```python
COINS = [
    # ... existing coins ...
    {
        "symbol": "DOGEUSDT",
        "name": "dogecoin",
        "display_name": "Dogecoin",
        "news_url": "https://cryptoslate.com/news/dogecoin/",
        "coin_url": "https://cryptoslate.com/coins/dogecoin/",
    },
]
```

Then run:
```bash
python main.py --coins dogecoin
```

## Next Steps

1. ✅ Run the pipeline: `python main.py --coins solana`
2. ✅ Check output: `ls data/raw/solana/`
3. ✅ View files: Open `.json`, `.csv`, or `.png`
4. 📖 Read full docs: See [README.md](README.md)
5. 🏗️ Learn architecture: See [ARCHITECTURE.md](ARCHITECTURE.md)
6. 🔄 Migration info: See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

## Quick Reference

| Command | Purpose |
|---------|---------|
| `python main.py` | Run for all coins |
| `python main.py --coins BTC,ETH` | Run for specific coins |
| `python main.py --list-coins` | Show available coins |
| `python main.py --verbose` | Enable debug logging |
| `python main.py --help` | Show all CLI options |

## Support Resources

- **Usage Questions**: See [README.md](README.md)
- **System Design**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Migration Info**: See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Configuration**: Edit [config.py](config.py)
- **Logs**: Check `data/logs/pipeline.log`

---

**Ready to go!** Run `python main.py` and enjoy! 🚀
