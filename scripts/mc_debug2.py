import re, sys
from curl_cffi import requests as cr
sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")
sess.headers.update({"Accept": "text/html"})
html = sess.get("https://www.moneycontrol.com/india/stockpricequote/A", timeout=30).text

# How many stockpricequote links are followed (within 80 chars) by a <span> w/ ISIN?
links = list(re.finditer(r'/india/stockpricequote/[a-z0-9-]+/[a-z0-9-]+/[A-Z0-9]+', html))
print("total spq links:", len(links))
with_span = 0
for m in links:
    tail = html[m.end(): m.end()+120]
    if "<span>" in tail and re.search(r'IN[A-Z0-9]{10}', tail):
        with_span += 1
print("links followed by ISIN span:", with_span)

# Show markup of links #20, #200, #500 to see the bulk-list row format
for idx in [20, 200, 500, 900]:
    if idx < len(links):
        m = links[idx]
        seg = html[m.start()-80: m.end()+140]
        print(f"\n--- link #{idx} ---")
        print(re.sub(r"\s+", " ", seg))
