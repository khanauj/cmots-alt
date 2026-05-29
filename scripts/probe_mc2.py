"""Confirm MC full stock directory pagination + name-slug matching feasibility."""
import re
import sys
from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")
sess.headers.update({"Accept": "text/html"})

LINK = re.compile(r'/india/stockpricequote/([a-z0-9-]+)/([a-z0-9-]+)/([A-Z0-9]+)"')

# The directory is alphabetical: /india/stockpricequote/ + ?classic=true paging,
# or per-letter pages. Probe a few forms.
forms = [
    ("root", "https://www.moneycontrol.com/india/stockpricequote/"),
    ("letterA", "https://www.moneycontrol.com/india/stockpricequote/?classic=true"),
]
for label, url in forms:
    r = sess.get(url, timeout=30)
    links = LINK.findall(r.text)
    uniq = {(c, s) for s, c, code in [(a, b, d) for a, b, d in links]}
    print(f"[{label}] {r.status_code} links={len(links)} uniqCompanies={len({l[1] for l in links})} sectors={len({l[0] for l in links})}")

# Look for alphabetical pagination controls
r = sess.get("https://www.moneycontrol.com/india/stockpricequote/", timeout=30)
nav = re.findall(r'href="(/india/stockpricequote/[^"]*)"[^>]*>\s*([A-Z])\s*<', r.text)
print("\nalpha-nav candidates:", nav[:30])

# distinct sector slugs sample (granularity check)
links = LINK.findall(r.text)
sects = sorted({l[0] for l in links})
print(f"\ndistinct sector slugs on page1: {len(sects)}")
for s in sects[:40]:
    print("  ", s)
