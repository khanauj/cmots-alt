import httpx
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/Content/Service/Portfolios.js", timeout=30)
    with open("scratch_portfolios_js.txt", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Downloaded Portfolios.js, size:", len(r.text))
