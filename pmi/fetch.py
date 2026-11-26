"""Monthly ISM PMI update: read the latest ISM Report On Business releases (PR Newswire,
ismworld.org as fallback), add them to data/pmi/reports.jsonl, rebuild data/pmi/ism_monthly.csv."""
import os, re, sys, time, requests
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(__file__))
from build_hist import record, load, build, write
import json

REC = "data/pmi/reports.jsonl"; OUT = "data/pmi/ism_monthly.csv"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
     "Accept-Language": "en-US,en;q=0.9"}
S = requests.Session(); S.headers.update(H)

def get(u):
    for i in range(3):
        try:
            r = S.get(u, timeout=60)
            if r.status_code == 200:
                r.encoding = "utf-8"
                return r.text
            print(u, r.status_code)
            if r.status_code in (403, 404): return None
        except Exception as e:
            print(u, e)
        time.sleep(5 * (i + 1))
    return None

def txt(html):
    s = BeautifulSoup(html, "html.parser")
    for t in s(["script", "style", "noscript"]): t.decompose()
    for td in s.find_all(["td", "th"]): td.append(" | ")
    return re.sub(r"\n\s*\n+", "\n", s.get_text("\n"))

recs = load(REC); have = {r["src"] for r in recs}; added = 0; dbg = 0
deep = "--deep" in sys.argv
links = []
for p in range(1, (6 if deep else 2)):
    h = get(f"https://www.prnewswire.com/news/institute-for-supply-management/?page={p}&pagesize=100")
    if not h: break
    L = [l for l in re.findall(r'href="(/news-releases/[^"]+-(\d+)\.html)"', h)]
    new = [l for l in L if l not in links]
    if not new: break
    links += new
print("prn links", len(links))
for path, rid in dict.fromkeys(links):
    if not re.search(r"pmi|report-on-business|nmi", path): continue
    src = "prn_" + rid
    if src in have: continue
    h = get("https://www.prnewswire.com" + path)
    if not h: continue
    t = txt(h); r = record(t, src)
    if "--debug" in sys.argv and (not r or "pmi" not in r["got"]) and dbg < 6:
        i = t.upper().find("AT A GLANCE"); os.makedirs("data/pmi/debug", exist_ok=True)
        open(f"data/pmi/debug/{src}.txt", "w").write(path + "\n" + (t[max(0, i - 300):i + 3000] if i >= 0 else t[:6000])); dbg += 1
    if r:
        recs.append(r); have.add(src); added += 1; print("added", src, r["fam"], r["ym"], r["got"].get("pmi"))
    time.sleep(1)
# Fallback: ISM's own pages for the current report
MN = ["january","february","march","april","may","june","july","august","september","october","november","december"]
import datetime as dt
t = dt.date.today()
for back in (1, 2):
    m = (t.month - 1 - back) % 12
    for sect in ("pmi", "services"):
        src = f"ism_{sect}_{t.year if t.month - back > 0 else t.year - 1}_{m + 1:02d}"
        if src in have: continue
        h = get(f"https://www.ismworld.org/supply-management-news-and-reports/reports/ism-report-on-business/{sect}/{MN[m]}/")
        if not h: continue
        r = record(txt(h), src)
        if r and r["ym"] == src[-7:].replace("_", "-"):
            recs.append(r); have.add(src); added += 1; print("added", src, r["got"].get("pmi"))
with open(REC, "w") as fh:
    for r in sorted(recs, key=lambda r: (r["ym"], r["src"])): fh.write(json.dumps(r, separators=(",", ":")) + "\n")
write(build(recs), OUT)
print("records", len(recs), "added", added)
