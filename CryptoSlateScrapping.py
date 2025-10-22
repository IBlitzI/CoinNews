import requests
from bs4 import BeautifulSoup
import time
import json
import csv
from datetime import datetime
from urllib.parse import urljoin, urlparse

START_URL = "https://cryptoslate.com/coins/bitcoin/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; CoinScraper/1.0)"}
REQUEST_TIMEOUT = 15
DELAY_BETWEEN_REQUESTS = 1.0
MAX_ARTICLES = 25

OUT_JSON = "cryptoslate_bitcoin_news.json"
OUT_CSV = "cryptoslate_bitcoin_news.csv"

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
    # 🔹 CryptoSlate yapısı: section.object-details altında <div class="list-post"> içindeki <a>
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

    # Başlık
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # İçerik kısmı (CryptoSlate’te <div class="post">)
    content_div = soup.select_one("div.post")
    if not content_div:
        content_div = soup.find("article")

    paragraphs = [p.get_text(" ", strip=True) for p in content_div.find_all("p")] if content_div else []
    content = "\n\n".join(paragraphs)
    return title, content

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_csv(data, path):
    keys = ["title", "link", "source", "content", "fetched_at"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)

def main():
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
        save_json(results, OUT_JSON)
        save_csv(results, OUT_CSV)
        print(f"Kaydedildi: {OUT_JSON}, {OUT_CSV}")

if __name__ == "__main__":
    main()
