import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/bundles/scripts?v=xqmnFHbfWg-YXI716jOiCYu4T2ATT3yVc0Y-Pi-ifQs1", timeout=30)
    text = r.text
    
    matches = list(re.finditer("Get_DisclosureDetailsonMonthandYear", text))
    print(f"Matches: {len(matches)}")
    for m in matches:
        idx = m.start()
        print(text[max(0, idx - 300):min(len(text), idx + 1000)])
        print("-"*40)
