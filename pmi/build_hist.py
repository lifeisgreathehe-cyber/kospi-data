"""ISM history: report texts -> compact records (reports.jsonl) -> monthly CSV."""
import os, sys, glob, csv, json
sys.path.insert(0, os.path.dirname(__file__))
from parse import parse, prev_month, family, last12, MFG, SVC
COLS = ["m_" + k for k, _ in MFG] + ["s_" + k for k, _ in SVC]

def record(text, src):
    fam = family(text)
    if not fam: return None
    r = parse(text, fam)
    if not r: return None
    ym, got = r
    return {"src": src, "fam": fam, "ym": "%d-%02d" % ym, "got": got,
            "l12": {"%d-%02d" % k: v for k, v in last12(text).items()}}

def load(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []

def build(recs):
    cur, prv, l12 = {}, {}, {}
    for r in sorted(recs, key=lambda r: (r["ym"], r["src"])):
        p = r["fam"][0] + "_"; y, m = map(int, r["ym"].split("-"))
        for k, (a, b) in r["got"].items():
            if a is not None: cur.setdefault((y, m), {})[p + k] = a
            if b is not None: prv.setdefault(prev_month((y, m)), {})[p + k] = b
        for mm, v in r["l12"].items():
            yy, mo = map(int, mm.split("-"))
            if p == "s_" and mm < "2008-01": continue  # pre-2008 services headline was Business Activity, not the NMI composite
            l12.setdefault((yy, mo), {})[p + "pmi"] = v
    out = {}
    for ym in sorted(set(cur) | set(prv) | set(l12)):
        row = {}
        for c in COLS:
            for src in (cur, prv, l12):
                v = src.get(ym, {}).get(c)
                if v is not None: row[c] = v; break
        if row: out[ym] = row
    return out

def write(d, path, start="2005-01"):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n"); w.writerow(["month"] + COLS)
        for ym in sorted(d):
            k = "%d-%02d" % ym
            if k >= start: w.writerow([k] + [d[ym].get(c, "") for c in COLS])

if __name__ == "__main__":
    # usage: build_hist.py <rawdir> <reports.jsonl>   (adds records from raw texts)
    recs = load(sys.argv[2]); have = {r["src"] for r in recs}
    for f in sorted(glob.glob(sys.argv[1] + "/*.txt")):
        src = os.path.basename(f)[:-4]
        if src in have: continue
        r = record(open(f, errors="ignore").read(), src)
        if r: recs.append(r)
    with open(sys.argv[2], "w") as fh:
        for r in sorted(recs, key=lambda r: (r["ym"], r["src"])): fh.write(json.dumps(r, separators=(",", ":")) + "\n")
    print(len(recs), "records")
