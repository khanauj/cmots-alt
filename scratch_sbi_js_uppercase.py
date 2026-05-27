import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/bundles/scripts?v=xqmnFHbfWg-YXI716jOiCYu4T2ATT3yVc0Y-Pi-ifQs1", timeout=30)
    text = r.text
    
    for kw in ["SCHEME_PORTFOLIO_SHEETS", "GET_LATEST_RECORD_BYFUNDID"]:
        matches = list(re.finditer(kw, text))
        print(f"\nMatches for {kw}: {len(matches)}")
        for m in matches:
            idx = m.start()
            print(f"Match at {idx}:")
            print(text[max(0, idx - 150):min(len(text), idx + 200)])
            print("-"*40)
