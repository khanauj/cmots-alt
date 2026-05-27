import re
from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/bundles/scripts?v=xqmnFHbfWg-YXI716jOiCYu4T2ATT3yVc0Y-Pi-ifQs1", timeout=30)
    text = r.text
    
    # Search for all occurrences of GET_LATEST_RECORD_BYFUNDID or SCHEME_PORTFOLIO_SHEETS
    for pattern in ["GET_LATEST_RECORD_BYFUNDID", "SCHEME_PORTFOLIO_SHEETS", "SCHEME_PORTFOLIO_SHEETS_UPDATED"]:
        for m in re.finditer(pattern, text):
            # Print a block around it if it looks like an ajax request or action
            idx = m.start()
            # Check if this match is just the enum definition we saw earlier
            context = text[max(0, idx - 100):min(len(text), idx + 200)]
            if ":" in context and "/ajaxcall" in context:
                # This is just the endpoint mapping, skip it to find actual calls
                continue
            print(f"--- Actual usage of {pattern} at {idx} ---")
            print(text[max(0, idx - 400):min(len(text), idx + 1000)])
            print("\n" + "="*80 + "\n")
