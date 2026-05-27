import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/bundles/scripts?v=xqmnFHbfWg-YXI716jOiCYu4T2ATT3yVc0Y-Pi-ifQs1", timeout=30)
    text = r.text
    
    # Let's search for functions that call GetSchemePortfolioSheets
    for m in re.finditer(r"GetSchemePortfolioSheets", text):
        start = max(0, m.start() - 500)
        end = min(len(text), m.end() + 1500)
        print(f"--- Match at {m.start()} ---")
        print(text[start:end])
        print("\n" + "="*80 + "\n")
