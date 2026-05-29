import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/portfolios", timeout=30)
    html = r.text
    print(f"HTML size: {len(html)} chars")
    
    # Let's find form elements, selects, inputs
    selects = re.findall(r'<select[^>]*>.*?</select>', html, re.DOTALL | re.IGNORECASE)
    print(f"Found {len(selects)} select tags:")
    for s in selects[:10]:
        # Print select element signature and a few characters of content
        lines = s.split("\n")
        print(f"  {lines[0][:150]} ... ({len(s)} chars)")
        # Print options if short
        options = re.findall(r'<option[^>]*>.*?</option>', s, re.DOTALL | re.IGNORECASE)
        print(f"    Options count: {len(options)}")
        for opt in options[:5]:
            print(f"      {opt.strip()}")
            
    # Search for script contents with interesting keywords
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    print(f"\nFound {len(scripts)} inline script tags")
    for idx, sc in enumerate(scripts):
        if any(kw in sc for kw in ["GetSchemePortfolioSheets", "FundId", "PSYear", "PSMonth", "portfolio"]):
            print(f"  Script #{idx} matches keywords (len={len(sc)}):")
            print(sc[:1000])
