"""Build monthly ISM history from saved report texts (Wayback / PR Newswire / ismworld)."""
import os, sys, glob, csv
sys.path.insert(0, os.path.dirname(__file__))
from parse import parse, prev_month, family, last12, MFG, SVC
COLS = ["m_" + k for k, _ in MFG] + ["s_" + k for k, _ in SVC]

def build(files):
    cur, prv, l12 = {}, {}, {}
    for f in sorted(files, key=lambda p: os.path.basename(p).split("_")[1] if "_" in os.path.basename(p) else p):
        t = open(f, errors="ignore").read()
        fam = family(t)
        if not fam: continue
        r = parse(t, fam)
        if not r: continue
        ym, got = r
        p = fam[0] + "_"
        for k, (a, b) in got.items():
            if a is not None: cur.setdefault(ym, {})[p + k] = a
            if b is not None: prv.setdefault(prev_month(ym), {})[p + k] = b
        for m, v in last12(t).items():
            l12.setdefault(m, {})[p + "pmi"] = v
    out = {}
    for ym in sorted(set(cur) | set(prv) | set(l12)):
        row = {}
        for c in COLS:
            for src in (cur, prv, l12):
                v = src.get(ym, {}).get(c)
                if v is not None: row[c] = v; break
        if row: out[ym] = row
    return out

def write(d, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n"); w.writerow(["month"] + COLS)
        for ym in sorted(d):
            w.writerow([f"{ym[0]}-{ym[1]:02d}"] + [d[ym].get(c, "") for c in COLS])

if __name__ == "__main__":
    write(build(glob.glob(sys.argv[1] + "/*.txt")), sys.argv[2])
