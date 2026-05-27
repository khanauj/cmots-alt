import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/bundles/scripts?v=xqmnFHbfWg-YXI716jOiCYu4T2ATT3yVc0Y-Pi-ifQs1", timeout=30)
    text = r.text
    
    matches = list(re.finditer("CREATE_TOKEN", text))
    print(f"Matches for CREATE_TOKEN: {len(matches)}")
    for m in matches:
        idx = m.start()
        print(text[max(0, idx - 150):min(len(text), idx + 800)])
        print("-"*40)
        
    matches_tok = list(re.finditer("GenerateToken", text))
    print(f"Matches for GenerateToken: {len(matches_tok)}")
    for m in matches_tok:
        idx = m.start()
        print(text[max(0, idx - 150):min(len(text), idx + 800)])
        print("-"*40)
