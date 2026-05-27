import json
import uuid
import random
import re
import time
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

def generate_session_id():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    return "".join(random.choice(chars) for _ in range(30))

with chrome_session(settings.http) as sess:
    # 1. Generate Token
    req_uuid = str(uuid.uuid4())
    session_id = generate_session_id()
    print("Generating token with UUID:", req_uuid, "Session:", session_id)
    
    token_url = "https://www.sbimf.com/api/GenerateToken/Post/"
    token_payload = {"Requestid": req_uuid, "SessionId": session_id}
    
    r = sess.post(token_url, json=token_payload, timeout=30)
    print("Token Status:", r.status_code)
    data_match = re.search(r'<Data[^>]*>(.*?)</Data>', r.text, re.DOTALL)
    if not data_match:
        print("No token data found in:", r.text)
        token = None
    else:
        data_json = json.loads(data_match.group(1))
        token = data_json["CreateTokenResult"]["Data"]
        print("Token obtained! length:", len(token))
    
    if token:
        # 2. Get schemes list
        schemes_url = "https://www.sbimf.com/api/SchemeListingAPI/GetSchemeDataByFundId/"
        schemes_payload = {
            "Requestid": str(uuid.uuid4()),
            "SessionId": generate_session_id(),
            "Data": json.dumps({"FundId": None, "SchemeCodes": []})
        }
        
        headers = {
            "Token": token,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/plain, */*"
        }
        r2 = sess.post(schemes_url, json=schemes_payload, headers=headers, timeout=30)
        print("Schemes response status:", r2.status_code)
        print("Schemes response body snippet:", r2.text[:1000])
        
        s_data_match = re.search(r'<Data[^>]*>(.*?)</Data>', r2.text, re.DOTALL)
        if s_data_match:
            try:
                schemes_list = json.loads(s_data_match.group(1))
            except Exception as e:
                print("Failed to parse schemes from <Data>:", e)
                schemes_list = []
        else:
            try:
                schemes_list = r2.json()
            except Exception as e:
                print("Failed to parse as JSON:", e)
                schemes_list = []
        
        # Get unique funds
        seen_funds = set()
        funds = []
        for item in schemes_list:
            fid = item.get("FundId")
            fname = item.get("FundName")
            fcat = item.get("FundCategoryName")
            if fid and fid not in seen_funds:
                seen_funds.add(fid)
                funds.append((fid, fname, fcat))
                
        print(f"Total unique funds: {len(funds)}")
        
        # Let's try to query GetSchemePortfolioSheets for the first 10 funds to see how many have links
        sheets_url = "https://www.sbimf.com/ajaxcall/CMS/GetSchemePortfolioSheets"
        
        links_found = []
        for fid, fname, fcat in funds[:15]:
            payload = {
                "FundId": fid,
                "PSYear": "2026",
                "PSMonth": "April",
                "PSFrequency": "Monthly"
            }
            try:
                r_sheet = sess.post(sheets_url, json=payload, timeout=15)
                # Search for xlsx links
                xlsx_links = re.findall(r'href="([^"]+\.xlsx[^"]*)"', r_sheet.text, re.I)
                if xlsx_links:
                    print(f"FundId {fid} ({fname}): found {len(xlsx_links)} links: {xlsx_links[0]}")
                    links_found.append((fid, fname, xlsx_links[0]))
                else:
                    print(f"FundId {fid} ({fname}): no link found")
                time.sleep(0.5)
            except Exception as e:
                print(f"FundId {fid} ({fname}): error: {e}")
                
        print(f"\nSummary: found links for {len(links_found)} out of 15 funds.")
