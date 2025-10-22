import requests
from bs4 import BeautifulSoup
import time
import json
import csv
from datetime import datetime
from urllib.parse import urljoin, urlparse
from binance import Client
import matplotlib.pyplot as plt
import pandas as pd

START_URL = "https://cryptoslate.com/coins/solana/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CoinScraper/1.0)"}
REQUEST_TIMEOUT = 15
DELAY_BETWEEN_REQUESTS = 1.0
MAX_ARTICLES = 25

OUT_JSON = "cryptoslate_solana_news.json"
OUT_CSV = "cryptoslate_solana_news.csv"
CHART_FILE = "solana_chart.png"

BINANCE_SYMBOL = "SOLUSDT" # Binance'te Solana/USDT sembolü
client = Client()

def get_solana_price_from_binance():
    """Binance'ten anlık SOL fiyatını (USDT cinsinden) alır."""
    try:
        ticker = client.get_symbol_ticker(symbol=BINANCE_SYMBOL)
        price = float(ticker["price"])
        print(f"🔹 Binance fiyatı alındı: {price} USDT")
        return price
    except Exception as e:
        print(f"[!] Binance fiyat alınamadı: {e}")
        return None

def generate_chart_from_binance(symbol="SOLUSDT", interval="1h", limit=100, outfile=CHART_FILE):
    """Binance'ten mum verilerini çekip chart (PNG) üretir."""
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(klines, columns=[
            "open_time", "open", "high", "low", "close",
            "volume", "close_time", "qav", "num_trades",
            "taker_base_vol", "taker_quote_vol", "ignore"
        ])
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close"] = df["close"].astype(float)

        plt.figure(figsize=(10, 5))
        plt.plot(df["open_time"], df["close"], linewidth=2)
        plt.title(f"{symbol} Fiyat Grafiği (Son {limit} mum - {interval})")
        plt.xlabel("Zaman")
        plt.ylabel("Fiyat (USDT)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(outfile)
        plt.close()
        print(f"✅ Binance chart oluşturuldu: {outfile}")
        return outfile
    except Exception as e:
        print(f"[!] Chart oluşturulamadı: {e}")
        return None

def safe_get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"[!] Hata: {url} -> {e}")
        return None

def extract_links_from_listing(html, base_url):
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.select("section.object-details div.list-post a[href]"):
        href = a.get("href")
        if href:
            full = urljoin(base_url, href)
            if full not in links:
                links.append(full)
        if len(links) >= MAX_ARTICLES:
            break
    return links

def extract_article_text(html):
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""
    content_div = soup.select_one("div.post") or soup.find("article")
    paragraphs = [p.get_text(" ", strip=True) for p in content_div.find_all("p")] if content_div else []
    content = "\n\n".join(paragraphs)
    return title, content

def save_json(price, data, path):
    combined = {
        "solana_price_usdt": price,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "articles": data
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

def save_csv(price, data, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Solana Price (USDT)", price])
        writer.writerow(["Fetched At", datetime.utcnow().isoformat() + "Z"])
        writer.writerow([])
        writer.writerow(["title", "link", "source", "content", "fetched_at"])
        for item in data:
            writer.writerow([
                item["title"], item["link"], item["source"], item["content"], item["fetched_at"]
            ])

def main():
    sol_price = get_solana_price_from_binance()

    generate_chart_from_binance(BINANCE_SYMBOL, interval="1h", limit=100, outfile=CHART_FILE)

    print("Listing sayfası indiriliyor:", START_URL)
    resp = safe_get(START_URL)
    if not resp:
        return

    links = extract_links_from_listing(resp.text, START_URL)
    print(f"Bulunan haber linkleri: {len(links)}")

    if not links:
        print("⚠️ Hiç link bulunamadı — selector'ı kontrol et.")
        return

    results = []
    for idx, link in enumerate(links, start=1):
        print(f"[{idx}/{len(links)}] {link}")
        r = safe_get(link)
        if not r:
            continue

        title, content = extract_article_text(r.text)
        if not content:
            print("  -> İçerik bulunamadı.")
            continue

        item = {
            "title": title,
            "link": link,
            "source": urlparse(link).netloc,
            "content": content,
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        results.append(item)
        print(f"  -> {len(content)} karakterlik içerik alındı.")
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n✅ Toplam {len(results)} haber çekildi.")
    if results:
        save_json(sol_price, results, OUT_JSON)
        save_csv(sol_price, results, OUT_CSV)
        print(f"Kaydedildi: {OUT_JSON}, {OUT_CSV}")

if __name__ == "__main__":
    main()
