import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/Content/Scripts/common.js", timeout=30)
    text = r.text
    
    # Search for DataBindUrls and APIURLS
    for kw in ["DataBindUrls", "APIURLS"]:
        matches = list(re.finditer(kw, text))
        print(f"\nMatches for {kw}: {len(matches)}")
        for m in matches:
            idx = m.start()
            print(text[max(0, idx - 50):min(len(text), idx + 800)])
            print("-"*40)
