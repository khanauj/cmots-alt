"""Dump BSE getScripHeaderData fully + try other BSE industry endpoints."""
import json
import sys
from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")
H = {"Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/"}
try:
    sess.get("https://www.bseindia.com/", timeout=20)
except Exception:
    pass

# Full dump of getScripHeaderData
r = sess.get("https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w?Debtflag=&scripcode=500325&seriesid=", timeout=30, headers=H)
data = json.loads(r.content)
print("=== getScripHeaderData FULL ===")
print(json.dumps(data, indent=1)[:2000])

# Check INDUSTRY values in the bulk list — are ANY populated?
r2 = sess.get("https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active", timeout=40,
              headers={"Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/corporates/List_Scrips.html"})
lst = json.loads(r2.content)
nonnull_ind = [x for x in lst if (x.get("INDUSTRY") or "").strip()]
print(f"\n=== bulk INDUSTRY populated: {len(nonnull_ind)} / {len(lst)} ===")

# Try scrip-level company-profile / industry endpoints
for label, url in [
    ("CompanyProfile", "https://api.bseindia.com/BseIndiaAPI/api/StockReachGraph/w?scripcode=500325&flag=0&fromdate=&todate=&seriesid="),
    ("ScripIndustry", "https://api.bseindia.com/BseIndiaAPI/api/Scripindustrydata/w?scripcd=500325"),
    ("CompanyMaster", "https://api.bseindia.com/BseIndiaAPI/api/getScripMaster/w?Group=&scripcode=500325"),
    ("HeaderwithIndustry", "https://api.bseindia.com/BseIndiaAPI/api/ScripHeaderData/w?Debtflag=&scripcode=500325&seriesid="),
]:
    try:
        rr = sess.get(url, timeout=20, headers=H)
        body = rr.content
        is_json = body.lstrip()[:1] in (b"[", b"{")
        print(f"\n[{label}] {rr.status_code} json={is_json} bytes={len(body)}")
        if is_json:
            d = json.loads(body)
            s = json.dumps(d)
            print("   ", s[:300])
            if "ndustr" in s:
                print("   >>> CONTAINS 'industr'")
    except Exception as e:
        print(f"[{label}] ERR {e}")
