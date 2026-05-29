"""Verify NSE quote API (warmup) and Screener/MC per-name sector extraction."""
import json
import re
import sys
from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")

# ── NSE quote-equity with proper warmup ──────────────────────────────────────
nse = cr.Session(impersonate="chrome120")
nse.headers.update({"Accept": "application/json"})
try:
    nse.get("https://www.nseindia.com/", timeout=20)
    nse.get("https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE", timeout=20)
except Exception as e:
    print("nse warm err", e)
try:
    r = nse.get("https://www.nseindia.com/api/quote-equity?symbol=RELIANCE", timeout=30,
                headers={"Referer": "https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE"})
    print("[NSE quote] status", r.status_code, "bytes", len(r.content))
    if r.content.lstrip()[:1] == b"{":
        d = json.loads(r.content)
        info = d.get("industryInfo", {})
        print("   industryInfo:", json.dumps(info))
        print("   metadata.industry:", d.get("metadata", {}).get("industry"))
except Exception as e:
    print("[NSE quote] ERR", e)

# ── NSE broad index file coverage (bulk) ─────────────────────────────────────
for label, url in [
    ("Nifty500", "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"),
    ("NiftyMicro250", "https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv"),
    ("NiftyTotalMkt", "https://nsearchives.nseindia.com/content/indices/ind_niftytotalmarket_list.csv"),
]:
    try:
        rr = nse.get(url, timeout=30)
        n = rr.content.count(b"\n")
        print(f"[{label}] {rr.status_code} rows~{n} hdr={rr.content.splitlines()[0][:80] if rr.status_code==200 else ''}")
    except Exception as e:
        print(f"[{label}] ERR {e}")

# ── Screener per-company (works by BSE code OR NSE symbol) ────────────────────
sc = cr.Session(impersonate="chrome120")
for label, code in [("Screener RELIANCE", "RELIANCE"), ("Screener byBSE 500325", "500325")]:
    try:
        r = sc.get(f"https://www.screener.in/company/{code}/", timeout=30)
        html = r.text
        # Screener shows sector/industry in a peers line and breadcrumb
        m = re.findall(r'(?:Sector|Industry)\s*[:<].*?</', html)
        # the peer-comparison links carry industry classification id
        links = re.findall(r'href="/company/compare/[^"]*"[^>]*>([^<]+)<', html)
        print(f"[{label}] {r.status_code} bytes={len(html)}")
        # Look for the classification block
        m2 = re.search(r'Industry[^<]*</[^>]*>\s*<[^>]*>([^<]+)<', html)
        # crude: find 'sector' anchor text
        sect = re.findall(r'/company/compare/[^"]+/"[^>]*>\s*([^<]+?)\s*<', html)
        print("   peers links sample:", links[:4])
    except Exception as e:
        print(f"[{label}] ERR {e}")
