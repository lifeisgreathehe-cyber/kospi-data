import os, json, requests, re
os.makedirs("data/pmi",exist_ok=True)
H={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
out={}
def g(u,**k):
    try:
        r=requests.get(u,timeout=90,headers=H,**k); return r
    except Exception as e: return str(e)
# ALFRED vintage of discontinued NAPM series
for sid in ["NAPM","NAPMNOI","NMFCI"]:
    r=g(f"https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={sid}&vintage_date=2016-06-01")
    out["alfred_"+sid]=r if isinstance(r,str) else [r.status_code,r.text[:200],r.text[-200:]]
for u in ["instituteforsupplymanagement.org/ISMReport/MfgROB.cfm","instituteforsupplymanagement.org/ISMReport/NonMfgROB.cfm","ism.ws/ISMReport/MfgROB.cfm","ism.ws/ISMReport/NonMfgROB.cfm","ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/pmi/*","ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/services/*"]:
    r=g("http://web.archive.org/cdx/search/cdx",params={"url":u,"output":"json","collapse":"timestamp:6","filter":"statuscode:200","fl":"timestamp,original"})
    if isinstance(r,str): out["cdx "+u]=r; continue
    try:
        rows=r.json()[1:]; out["cdx "+u]=[len(rows),rows[:2],rows[-2:]]
    except Exception as e: out["cdx "+u]=[r.status_code,r.text[:200]]
for p in [1,20,60]:
    r=g(f"https://www.prnewswire.com/news/institute-for-supply-management/?page={p}&pagesize=100")
    if isinstance(r,str): out[f"prn{p}"]=r; continue
    links=re.findall(r'href="(/news-releases/[^"]+\.html)"',r.text)
    dates=re.findall(r'(\w{3} \d{1,2}, \d{4})',r.text)
    out[f"prn{p}"]=[r.status_code,len(links),links[:2],dates[:1],dates[-1:]]
r=g("https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/pmi/october/")
out["ism_oct"]=r if isinstance(r,str) else [r.status_code,len(r.text)]
if not isinstance(r,str): open("data/pmi/ism_oct.html","w").write(r.text)
json.dump(out,open("data/pmi/probe.json","w"),ensure_ascii=False,indent=1)
print(json.dumps(out,ensure_ascii=False)[:4000])
