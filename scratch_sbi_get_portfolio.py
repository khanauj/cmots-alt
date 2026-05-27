import json
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    url = "https://www.sbimf.com/ajaxcall/CMS/GetSchemePortfolioSheets"
    
    # Let's request the portfolio for FundId 85 (SBI Infrastructure Fund), for 2026 April (or March)
    payload = {
        "FundId": 85,
        "PSYear": "2026",
        "PSMonth": "April",
        "PSFrequency": "Monthly"
    }
    
    print("POSTing to", url)
    print("Payload:", payload)
    
    r = sess.post(url, json=payload, timeout=30)
    print("Status:", r.status_code)
    # Print the first 2000 characters of the response
    print("Response Length:", len(r.text))
    print("Response Snippet:")
    print(r.text[:2000])
    
    # Save the full HTML response to a file so we can view it
    with open("scratch_sbi_portfolio_85.html", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Saved HTML to scratch_sbi_portfolio_85.html")
