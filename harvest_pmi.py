"""One-off: harvest archived ISM Report On Business pages (Wayback) + PR Newswire releases as text."""
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
        except Exception as e: pass
        time.sleep(5*(i+1))
    return None
def txt(html):
    s=BeautifulSoup(html,"html.parser")
    for t in s(["script","style","noscript"]): t.decompose()
    for td in s.find_all(["td","th"]): td.append(" | ")
    return re.sub(r"\n\s*\n+","\n",s.get_text("\n"))
fams={"mfg":["ism.ws/ISMReport/MfgROB.cfm","instituteforsupplymanagement.org/ISMReport/MfgROB.cfm","ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/pmi/*"],
      "svc":["ism.ws/ISMReport/NonMfgROB.cfm","instituteforsupplymanagement.org/ISMReport/NonMfgROB.cfm","ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/services/*"]}
log={}
for fam,urls in fams.items():
    snaps=[]
    for u in urls:
        r=get("http://web.archive.org/cdx/search/cdx",params={"url":u,"output":"json","collapse":"timestamp:8","filter":"statuscode:200","fl":"timestamp,original","from":"2006"})
        if r is None: continue
        try: snaps+= [tuple(x) for x in r.json()[1:]]
        except Exception: pass
    # keep up to 3 per (yyyymm, url-tail) to limit volume
    seen={}; pick=[]
    for ts,orig in sorted(snaps):
        key=(ts[:6],orig.rstrip('/').split('/')[-1].lower()) if 'ismworld' in orig else (ts[:6],'old')
        seen[key]=seen.get(key,0)+1
        if seen[key]<=2: pick.append((ts,orig))
    log[fam]=len(pick); print(fam,len(snaps),"->",len(pick),flush=True)
    for ts,orig in pick:
        fn=f"data/pmi/raw/{fam}_{ts}.txt"
        if os.path.exists(fn): continue
        r=get(f"http://web.archive.org/web/{ts}id_/{orig}")
        if r is None: continue
        t=txt(r.text)
        if "PMI" not in t and "NMI" not in t: continue
        open(fn,"w").write(orig+"\n"+t)
        time.sleep(0.7)
# PR Newswire releases
links=set()
for p in range(1,8):
    r=get(f"https://www.prnewswire.com/news/institute-for-supply-management/?page={p}&pagesize=100")
    if r is None: break
    L=set(re.findall(r'href="(/news-releases/[^"]+\.html)"',r.text)); 
    if not L-links: break
    links|=L
for l in sorted(links):
    if not re.search(r'pmi|report-on-business|nmi',l): continue
    fn="data/pmi/raw/prn_"+l.split('/')[-1].replace('.html','.txt')
    if os.path.exists(fn): continue
    r=get("https://www.prnewswire.com"+l)
    if r is None: continue
    open(fn,"w").write(l+"\n"+txt(r.text)); time.sleep(0.5)
log["prn"]=len(links)
json.dump(log,open("data/pmi/harvest_log.json","w"))
