from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    url = "https://www.sbimf.com/ajaxcall/CMS/GetRecentPortfolios"
    print("POSTing to", url)
    r = sess.post(url, timeout=30)
    print("Status:", r.status_code)
    print("Length:", len(r.text))
    print("Snippet:")
    print(r.text[:2000])
    
    with open("scratch_sbi_recent.html", "w", encoding="utf-8") as f:
        f.write(r.text)
