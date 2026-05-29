"""Probe candidate full-universe sector sources. Empirical — no guessing."""
import json
import sys

from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")


def warm(url):
    try:
        sess.get(url, timeout=20)
    except Exception as e:
        print("warm err", e)


def show(label, url, headers=None, want="json"):
    try:
        r = sess.get(url, timeout=30, headers=headers)
        ct = r.headers.get("content-type", "")
        body = r.content
        is_json = body.lstrip()[:1] in (b"[", b"{")
        print(f"[{label}] {r.status_code} bytes={len(body)} ct={ct[:40]} json={is_json}")
        if is_json:
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    print("   keys:", list(data.keys())[:20])
                    print("   head:", json.dumps(data)[:400])
                elif isinstance(data, list) and data:
                    print("   list len:", len(data), "first keys:", list(data[0].keys()))
            except Exception as e:
                print("   json parse err", e)
        else:
            print("   head:", body[:160])
    except Exception as e:
        print(f"[{label}] ERR {e}")
    print()


# ── BSE ──────────────────────────────────────────────────────────────────────
warm("https://www.bseindia.com/")
show(
    "BSE getScripHeaderData",
    "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w?Debtflag=&scripcode=500325&seriesid=",
    headers={"Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/"},
)
show(
    "BSE CompanyData",
    "https://api.bseindia.com/BseIndiaAPI/api/ComHeaderData/w?quotetype=EQ&scripcode=500325&seriesid=",
    headers={"Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/"},
)
# BSE industry dropdown (list of industries)
show(
    "BSE IndustryDDL",
    "https://api.bseindia.com/BseIndiaAPI/api/DDLIndustryType/w?Type=Industry",
    headers={"Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/"},
)
# BSE ListofScripData filtered by one industry — does it then populate INDUSTRY?
show(
    "BSE ScripData byIndustry",
    "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=Banks&segment=Equity&status=Active",
    headers={"Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/corporates/List_Scrips.html"},
)

# ── NSE ──────────────────────────────────────────────────────────────────────
warm("https://www.nseindia.com/")
for label, url in [
    ("NSE ind csv", "https://nsearchives.nseindia.com/content/equities/Industry_classification.csv"),
    ("NSE ind xlsx", "https://nsearchives.nseindia.com/content/equities/Industry_classification.xlsx"),
    ("NSE ind www1", "https://www1.nseindia.com/content/equities/Industry_classification.csv"),
    ("NSE seclist", "https://nsearchives.nseindia.com/content/equities/sec_list.csv"),
]:
    show(label, url, want="csv")

# NSE quote-equity industryInfo (per symbol)
show(
    "NSE quote RELIANCE",
    "https://www.nseindia.com/api/quote-equity?symbol=RELIANCE",
    headers={"Referer": "https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE", "Accept": "application/json"},
)
