import json
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    # 1. GET
    print("GET https://www.sbimf.com/api/PreLoginAPI/AllFundNames:")
    try:
        r = sess.get("https://www.sbimf.com/api/PreLoginAPI/AllFundNames", timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. POST
    print("\nPOST https://www.sbimf.com/api/PreLoginAPI/AllFundNames:")
    try:
        r = sess.post("https://www.sbimf.com/api/PreLoginAPI/AllFundNames", timeout=15)
        print(f"Status: {r.status_code}")
        print(f"Content: {r.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")
