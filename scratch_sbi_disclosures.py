from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    url = "https://www.sbimf.com/en-us/downloads/portfolio-disclosures"
    print("GET", url)
    r = sess.get(url, timeout=30)
    print("Status:", r.status_code)
    print("Final URL:", r.url)
    print("Length:", len(r.text))
