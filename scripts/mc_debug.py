import re, sys
from curl_cffi import requests as cr
sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")
sess.headers.update({"Accept": "text/html"})

r = sess.get("https://www.moneycontrol.com/india/stockpricequote/A", timeout=30)
print("status", r.status_code, "bytes", len(r.text))
html = r.text

# simple link pattern (worked on root)
simple = re.findall(r'/india/stockpricequote/([a-z0-9-]+)/([a-z0-9-]+)/([A-Z0-9]+)', html)
print("simple matches:", len(simple))
print("sample:", simple[:5])

# show context around the first stockpricequote link to design extraction
i = html.find("/india/stockpricequote/")
# find one that is 3-segment
for m in re.finditer(r'/india/stockpricequote/[a-z0-9-]+/[a-z0-9-]+/[A-Z0-9]+', html):
    j = m.start()
    print("\ncontext:")
    print(re.sub(r"\s+", " ", html[j-60:j+160]))
    break

# Is there a table with company names? show a chunk
k = html.find("stockpricequote/", i+10)
print("\n-- raw chunk --")
print(html[i-200:i+400])
