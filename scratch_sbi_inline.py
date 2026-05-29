import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/portfolios", timeout=30)
    html = r.text
    
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    print(f"Total inline scripts: {len(scripts)}")
    for idx, sc in enumerate(scripts):
        print(f"\n--- Inline Script #{idx} (len={len(sc)}) ---")
        # Print first 200 chars and last 200 chars if long, else print whole
        if len(sc) > 800:
            print(sc[:400])
            print("...\n[TRUNCATED]\n...")
            print(sc[-400:])
        else:
            print(sc)
        print("="*80)
