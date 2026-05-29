from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()
url = "https://www.sbimf.com/bundles/scripts?v=xqmnFHbfWg-YXI716jOiCYu4T2ATT3yVc0Y-Pi-ifQs1"

with chrome_session(settings.http) as sess:
    resp = sess.get(url, timeout=30)
    text = resp.text
    
    idx = text.find("SCHEME_PORTFOLIO_SHEETS")
    if idx != -1:
        print("SCHEME_PORTFOLIO_SHEETS:")
        print(text[idx-50:idx+200])
