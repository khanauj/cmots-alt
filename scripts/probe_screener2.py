"""Find Screener's company id + clean industry via peers, and the warehouse id."""
import re
import sys
from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")

r = sess.get("https://www.screener.in/company/TCS/", timeout=30)
html = r.text

# company id often in: data-company-id / /api/company/<id>/ / warehouse
for pat in [r'company[_-]id["\s:=]+(\d+)', r'/api/company/(\d+)/', r'data-warehouse-id="(\d+)"', r'"id":\s*(\d+)']:
    m = re.search(pat, html)
    print(pat, "->", m.group(1) if m else None)

# The "Peer comparison" section header carries the industry name.
m = re.search(r'Compare with peers?.*?<.*?>([^<]{3,60})</', html, re.S)
# Industry is in the section "#peers" with text "Industry: X" or a subheading
idx = html.find("peers")
print("\n-- around first 'peers' --")
print(re.sub(r"\s+", " ", html[idx-300:idx+300]))

# Screener also embeds: "Industry: <a ...>NAME</a>" sometimes in the ratios/about
for m in re.finditer(r'([A-Z][a-z]+ ?(?:&|and)? ?[A-Za-z]*)\s*</a>\s*</li>', html):
    pass

# Look for the explicit BSE/NSE industry classification block
for kw in ["sector_id", "industry_id", "Industry Classification", "warehouse"]:
    i = html.find(kw)
    if i != -1:
        print(f"\n-- around '{kw}' --")
        print(re.sub(r"\s+", " ", html[i-120:i+180]))
