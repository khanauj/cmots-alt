from cmots_alt.core.settings import load_settings
from cmots_alt.fetchers.http import chrome_session

settings = load_settings()

with chrome_session(settings.http) as sess:
    r = sess.get("https://www.sbimf.com/Content/Service/EncryptionService.js", timeout=30)
    print("Status:", r.status_code)
    # Write to a text file
    with open("scratch_encryption_js.txt", "w", encoding="utf-8") as f:
        f.write(r.text)
    print("Downloaded EncryptionService.js, size:", len(r.text))
