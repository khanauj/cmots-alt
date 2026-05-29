"""Probe BSE endpoints to see what actually responds."""
from curl_cffi import requests as cr
from datetime import date

sess = cr.Session(impersonate="chrome120")

def show(label, url, headers=None):
    try:
        r = sess.get(url, timeout=30, headers=headers)
        body = r.content[:300]
        print(f"[{label}] {r.status_code}  bytes={len(r.content)}  url={url}")
        print("   head:", body[:200])
    except Exception as e:
        print(f"[{label}] ERROR {e}  url={url}")
    print()

# warm cookies
try:
    sess.get("https://www.bseindia.com/", timeout=20)
except Exception as e:
    print("warmup err", e)

show("api-bare", "https://api.bseindia.com/BseIndiaAPI/api/ListofScripCode/w",
     headers={"Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/corporates/List_Scrips.html", "Accept": "application/json, text/plain, */*"})

show("api-params", "https://api.bseindia.com/BseIndiaAPI/api/ListofScripCode/w?segment=Equity&status=Active&group=&industry=&scripcode=",
     headers={"Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/", "Accept": "application/json, text/plain, */*"})

# new-format bhavcopy
ymd = date.today().strftime("%Y%m%d")
show("bhav-new", f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{ymd}_F_0000.CSV")

# old-format bhavcopy
dmy = date.today().strftime("%d%m%y")
show("bhav-old", f"https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{dmy}.zip")
