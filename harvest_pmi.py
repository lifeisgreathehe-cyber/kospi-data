"""One-off #2: fill 2016-2020 gap and the earliest year via Wayback prefix queries + PR Newswire."""
import os, re, time, json, requests
from bs4 import BeautifulSoup
os.makedirs("data/pmi/raw",exist_ok=True)
H={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
S=requests.Session(); S.headers.update(H)
def get(u,**k):
    for i in range(4):
        try:
            r=S.get(u,timeout=60,**k)
            if r.status_code==200: return r
            if r.status_code in (404,403): return None
        except Exception: pass
        time.sleep(5*(i+1))
    return None
def txt(html):
    s=BeautifulSoup(html,"html.parser")
    for t in s(["script","style","noscript"]): t.decompose()
    for td in s.find_all(["td","th"]): td.append(" | ")
    return re.sub(r"\n\s*\n+","\n",s.get_text("\n"))
log={}
def cdx(prefix, frm, to):
    r=get("http://web.archive.org/cdx/search/cdx",params={"url":prefix,"matchType":"prefix","output":"json","from":frm,"to":to,"filter":"statuscode:200","fl":"timestamp,original","collapse":"digest"})
    try: return [tuple(x) for x in r.json()[1:]]
    except Exception: return []
snaps=[]
for pre,frm,to in [("instituteforsupplymanagement.org/ismreport/","2015","2020"),
                   ("instituteforsupplymanagement.org/about/mediaroom/newsreleasedetail.cfm","2014","2020"),
                   ("instituteforsupplymanagement.org/news/newsroom.cfm","2014","2020"),
                   ("ism.ws/ismreport/","2005","2008"),
                   ("ism.ws/about/mediaroom/newsreleasedetail.cfm","2005","2008")]:
    s=cdx(pre,frm,to); log[pre]=len(s); print(pre,len(s),flush=True); snaps+=s
open("data/pmi/cdx2.json","w").write(json.dumps(snaps))
seen=set(); n=0
for ts,orig in sorted(snaps):
    o=orig.lower()
    if not ("rob" in o or "newsreleasedetail" in o): continue
    if re.search(r"\.(pdf|jpg|png|gif|css|js)$",o): continue
    key=(ts[:8],o.split("://")[-1].replace("www.","").replace(":80",""))
    if key in seen: continue
    seen.add(key)
    fn=f"data/pmi/raw/x_{ts}_{abs(hash(o))%10**8}.txt"
    if os.path.exists(fn): continue
    r=get(f"http://web.archive.org/web/{ts}id_/{orig}")
    if r is None: continue
    t=txt(r.text)
    if "AT A GLANCE" not in t.upper(): continue
    open(fn,"w").write(orig+"\n"+t); n+=1
    time.sleep(0.5)
log["x_saved"]=n
# PR Newswire listing debug
for u in ["https://www.prnewswire.com/news/institute-for-supply-management/","https://www.prnewswire.com/news/institute-for-supply-management/?page=2&pagesize=25"]:
    r=get(u); log[u]=None if r is None else [len(r.text), len(re.findall(r'/news-releases/[^"]+\.html',r.text))]
json.dump(log,open("data/pmi/harvest_log2.json","w"))
