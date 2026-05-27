import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    # 1. Test scheme detail without trailing slash
    print("GET https://www.sbimf.com/api/PreLoginAPI/SchemeDetail:")
    try:
        r = sess.get("https://www.sbimf.com/api/PreLoginAPI/SchemeDetail", timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Test POST scheme detail
    print("\nPOST https://www.sbimf.com/api/PreLoginAPI/SchemeDetail:")
    try:
        r = sess.post("https://www.sbimf.com/api/PreLoginAPI/SchemeDetail", timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

    # 3. Fetch script bundle and search for api/PreLoginAPI or ajaxcall or CMS
    print("\nFetching bundle to search for URLs:")
    try:
        r = sess.get("https://www.sbimf.com/bundles/scripts?v=xqmnFHbfWg-YXI716jOiCYu4T2ATT3yVc0Y-Pi-ifQs1", timeout=30)
        text = r.text
        # Search for path patterns
        urls = re.findall(r'["\'](/api/[a-zA-Z0-9_/]+)["\']|["\'](/ajaxcall/[a-zA-Z0-9_/]+)["\']', text)
        matched = set()
        for u in urls:
            for item in u:
                if item:
                    matched.add(item)
        print(f"Found {len(matched)} matching URL patterns:")
        for m in sorted(matched):
            if any(kw in m.lower() for kw in ["scheme", "portfolio", "fact", "download", "cms"]):
                print(f"  - {m}")
    except Exception as e:
        print(f"Error: {e}")
