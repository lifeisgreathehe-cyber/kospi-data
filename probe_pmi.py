import json, requests
H={"User-Agent":"Mozilla/5.0"}
out={}
r=requests.get("https://api.db.nomics.world/v22/datasets/ISM",params={"limit":100},timeout=60,headers=H)
out["datasets_status"]=r.status_code
ds=r.json().get("datasets",{}).get("docs",[]) if r.ok else []
out["datasets"]=[]
for d in ds:
    code=d["code"]
    s=requests.get(f"https://api.db.nomics.world/v22/series/ISM/{code}",params={"observations":1,"limit":50},timeout=60,headers=H)
    docs=s.json().get("series",{}).get("docs",[]) if s.ok else []
    out["datasets"].append({"code":code,"name":d.get("name"),"series":[{"code":x["series_code"],"name":x.get("series_name"),"first":(x.get("period") or [None])[0],"last":(x.get("period") or [None])[-1],"n":len(x.get("period") or [])} for x in docs]})
for u in ["https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/pmi/","https://www.prnewswire.com/news/institute-for-supply-management/","https://fred.stlouisfed.org/graph/fredgraph.csv?id=NAPM","https://tradingeconomics.com/united-states/business-confidence"]:
    try:
        q=requests.get(u,timeout=30,headers=H); out[u]=[q.status_code,len(q.text)]
    except Exception as e: out[u]=str(e)
json.dump(out,open("data/pmi/probe.json","w"),ensure_ascii=False,indent=1)
print(json.dumps(out,ensure_ascii=False)[:3000])
