"""Find where sector/industry lives in a Screener company page."""
import re
import sys
from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")

for code in ["RELIANCE", "500325", "TCS"]:
    r = sess.get(f"https://www.screener.in/company/{code}/", timeout=30)
    html = r.text
    print(f"\n===== {code} status={r.status_code} bytes={len(html)} =====")

    # 1. Breadcrumb / classification anchors to /company/compare/
    comp = re.findall(r'/company/compare/([^/"]+)/?"', html)
    print("compare-slugs:", comp[:6])

    # 2. Look for explicit 'Industry' / 'Sector' labels with following text
    for label in ["Industry", "Sector"]:
        for m in re.finditer(label + r'\s*[:<]', html):
            seg = html[m.start(): m.start() + 220]
            seg = re.sub(r"\s+", " ", seg)
            print(f"{label} ctx:", seg[:200])
            break

    # 3. The classic Screener pattern: peer-comparison heading
    m = re.search(r'href="/company/compare/[^"]+/"[^>]*>([^<]+)</a>', html)
    if m:
        print("compare-anchor text:", m.group(1).strip())

    # 4. og:description / meta sometimes carries sector
    m = re.search(r'<meta name="description" content="([^"]+)"', html)
    if m:
        print("meta desc:", m.group(1)[:160])
