import os, sys, glob, csv
sys.path.insert(0, os.path.dirname(__file__))
from parse import parse, prev_month, MFG, SVC
def build(rawdir):
    out = {}
    for fam, rows in (("mfg", MFG), ("svc", SVC)):
        cur, prv = {}, {}
        for f in sorted(glob.glob(f"{rawdir}/{fam}_*.txt")) + sorted(glob.glob(f"{rawdir}/prn_*.txt")):
            t = open(f).read()
            if os.path.basename(f).startswith("prn_"):
                low = t[:400].lower()
                is_svc = "services" in low or "non-manufacturing" in low
                if (fam == "svc") != is_svc:
                    continue
            r = parse(t, fam)
            if not r: continue
            ym, got = r
            for k, (a, b) in got.items():
                if a is not None: cur.setdefault(ym, {})[k] = a      # later snapshots overwrite: latest print of own report
                if b is not None: prv.setdefault(prev_month(ym), {})[k] = b
        months = sorted(set(cur) | set(prv))
        for ym in months:
            row = out.setdefault(ym, {})
            for k, _ in rows:
                v = cur.get(ym, {}).get(k, prv.get(ym, {}).get(k))
                if v is not None: row[f"{fam[0]}_{k}"] = v
    return out
if __name__ == "__main__":
    d = build(sys.argv[1])
    cols = ["m_" + k for k, _ in MFG] + ["s_" + k for k, _ in SVC]
    w = csv.writer(open(sys.argv[2], "w", newline=""), lineterminator="\n"); w.writerow(["month"] + cols)
    for ym in sorted(d):
        w.writerow([f"{ym[0]}-{ym[1]:02d}"] + [d[ym].get(c, "") for c in cols])
