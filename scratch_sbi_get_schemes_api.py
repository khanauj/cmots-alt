import json
import uuid
import random
import re
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
    token_payload = {
        "Requestid": req_uuid,
        "SessionId": session_id
    }
    
    r = sess.post(token_url, json=token_payload, timeout=30)
    print("Token Status:", r.status_code)
    
    # Extract JSON inside <Data>...</Data>
    data_match = re.search(r'<Data[^>]*>(.*?)</Data>', r.text, re.DOTALL)
    if not data_match:
        print("Could not find <Data> in response:", r.text)
        token = None
    else:
        try:
            data_json = json.loads(data_match.group(1))
            token = data_json["CreateTokenResult"]["Data"]
            print("Token obtained! length:", len(token))
        except Exception as e:
            print("Failed to parse token JSON:", e)
            print("XML Data content:", data_match.group(1))
            token = None
        
    if token:
        # 2. Call GetSchemeDataByFundId
        schemes_url = "https://www.sbimf.com/api/SchemeListingAPI/GetSchemeDataByFundId/"
        schemes_payload = {
            "Requestid": str(uuid.uuid4()),
            "SessionId": generate_session_id(),
            "Data": json.dumps({
                "FundId": None,
                "SchemeCodes": []
            })
        }
        
        headers = {
            "Token": token,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/plain, */*"
        }
        
        r2 = sess.post(schemes_url, json=schemes_payload, headers=headers, timeout=30)
        print("\nSchemes Status:", r2.status_code)
        
        # Check if response is XML or JSON
        if "<ResponseModel" in r2.text or "<Data" in r2.text:
            s_data_match = re.search(r'<Data[^>]*>(.*?)</Data>', r2.text, re.DOTALL)
            if s_data_match:
                try:
                    s_json = json.loads(s_data_match.group(1))
                    print("Parsed schemes list from XML Data.")
                    schemes_list = s_json
                except Exception as e:
                    print("Failed to parse schemes from XML <Data>:", e)
                    print("Content in <Data>:", s_data_match.group(1)[:500])
                    schemes_list = []
            else:
                print("Response contains XML but no <Data>:")
                print(r2.text[:1000])
                schemes_list = []
        else:
            try:
                schemes_list = r2.json()
            except Exception as e:
                print("Failed to parse schemes as direct JSON:", e)
                print("Text response:", r2.text[:1000])
                schemes_list = []
                
        if schemes_list:
            print("Schemes count:", len(schemes_list))
            # Save to a JSON file
            with open("scratch_sbi_schemes_list.json", "w", encoding="utf-8") as f:
                json.dump(schemes_list, f, indent=2)
            print("Saved list to scratch_sbi_schemes_list.json")
            
            # Print unique category names
            cats = set(item.get("FundCategoryName") for item in schemes_list if item.get("FundCategoryName"))
            print("Categories:", sorted(cats))
            
            for item in schemes_list[:10]:
                print(f"FundId: {item.get('FundId')}, FundName: {item.get('FundName')}, Category: {item.get('FundCategoryName')}")
