import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/portfolios", timeout=30)
    html = r.text
    
    # Let's search for xlsx/xls/pdf links
    links = re.findall(r'href="([^"]+\.(?:xlsx|xls|pdf)[^"]*)"', html, re.I)
    print(f"Found {len(links)} links in page HTML:")
    for l in links[:20]:
        print(f"  - {l}")
