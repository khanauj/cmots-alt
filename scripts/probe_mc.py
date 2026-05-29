"""Probe Moneycontrol for a BULK sector->companies listing (few requests)."""
import re
import sys
from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")
sess.headers.update({"Accept": "text/html,application/xhtml+xml"})

cands = [
    ("sector-classification", "https://www.moneycontrol.com/stocks/marketstats/sectorclassification.php"),
    ("bse-sectors", "https://www.moneycontrol.com/markets/indian-indices/"),
    ("glossary-sector", "https://www.moneycontrol.com/india/stockpricequote/"),
    ("nse-gainers", "https://www.moneycontrol.com/stocks/marketstats/nsegainer/index.php"),
]
for label, url in cands:
    try:
        r = sess.get(url, timeout=30)
        html = r.text
        # count links to stock price quote pages (each is a company)
        quotes = re.findall(r'/india/stockpricequote/([a-z0-9-]+)/([a-z0-9-]+)/([A-Z0-9]+)', html)
        print(f"[{label}] {r.status_code} bytes={len(html)} quoteLinks={len(quotes)}")
        if quotes:
            print("   sample:", quotes[:3])
    except Exception as e:
        print(f"[{label}] ERR {e}")

# MC stockpricequote URL embeds the sector slug as the first path segment.
# Fetch one company page and confirm sector is in the URL/breadcrumb.
r = sess.get("https://www.moneycontrol.com/india/stockpricequote/refineries/relianceindustries/RI", timeout=30)
print("\n[RIL page]", r.status_code, "bytes", len(r.text))
m = re.search(r'stockpricequote/([a-z0-9-]+)/', r.url if hasattr(r, "url") else "")
bc = re.findall(r'class="bcrumb[^"]*"[^>]*>(.*?)</', r.text, re.S)
# breadcrumb / sector indicators
for kw in ["sector", "Sector", "industry", "Industry"]:
    i = r.text.find(kw)
    if i != -1:
        print(f"  '{kw}':", re.sub(r"\s+", " ", r.text[i-60:i+120])[:160])
        break
