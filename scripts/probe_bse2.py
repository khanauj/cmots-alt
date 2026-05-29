"""Probe candidate BSE endpoints to find a live one."""
from curl_cffi import requests as cr
from datetime import date, timedelta

sess = cr.Session(impersonate="chrome120")
H = {
    "Origin": "https://www.bseindia.com",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
}
try:
    sess.get("https://www.bseindia.com/", timeout=20)
    sess.get("https://www.bseindia.com/corporates/List_Scrips.html", timeout=20)
except Exception as e:
    print("warmup", e)

def show(label, url, headers=H):
    try:
        r = sess.get(url, timeout=30, headers=headers)
        head = r.content[:120]
        is_json = r.content.lstrip()[:1] in (b"[", b"{")
        is_zip = r.content[:2] == b"PK"
        print(f"[{label}] {r.status_code} bytes={len(r.content)} json={is_json} zip={is_zip}")
        print("   ", head)
    except Exception as e:
        print(f"[{label}] ERR {e}")
    print()

# API candidates
show("ListofScripData", "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active")
show("ListofScripCSV", "https://api.bseindia.com/BseIndiaAPI/api/LitsofScripData/w?segment=Equity&status=Active")
show("getScripData", "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w?Debtflag=&scripcode=500325&seriesid=")
show("Equitydata", "https://api.bseindia.com/BseIndiaAPI/api/Equitydata/w")

# bhavcopy for recent trading days, with Referer
for back in range(0, 6):
    d = date.today() - timedelta(days=back)
    ymd = d.strftime("%Y%m%d")
    show(f"bhav-{ymd}", f"https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{ymd}_F_0000.CSV",
         headers={"Referer": "https://www.bseindia.com/markets/MarketInfo/BhavCopy.aspx"})
