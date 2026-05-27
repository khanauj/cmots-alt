import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/portfolios", timeout=30)
    html = r.text
    
    script_tags = re.findall(r'<script[^>]*>', html, re.IGNORECASE)
    print(f"Total script tags: {len(script_tags)}")
    for t in script_tags:
        print(f"  {t}")
