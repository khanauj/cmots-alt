from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/Content/Scripts/common.js", timeout=30)
    print("Status:", r.status_code)
    print(r.text[:3000])
