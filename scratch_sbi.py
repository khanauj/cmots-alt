import json
import httpx
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    # Let's try to query the landing page
    print("GET landing page:")
    try:
        r = sess.get("https://www.sbimf.com/portfolios", timeout=30)
        print(f"Status: {r.status_code}")
        print(f"Title: {r.text[:1000]}")
    except Exception as e:
        print(f"Error: {e}")

    # Let's try to fetch scheme detail list metadata
    print("\nGET pre-login API scheme details:")
    try:
        r2 = sess.get("https://www.sbimf.com/api/PreLoginAPI/SchemeDetail/", timeout=30)
        print(f"Status: {r2.status_code}")
        data = r2.json()
        print(f"Found {len(data)} schemes")
        # Print a couple of schemes
        for item in data[:5]:
            print(item)
    except Exception as e:
        print(f"Error: {e}")
