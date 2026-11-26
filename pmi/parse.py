"""Parse the 'AT A GLANCE' table of an ISM Report On Business page (text form)."""
import re
MONTHS = {m: i + 1 for i, m in enumerate(["january","february","march","april","may","june","july","august","september","october","november","december"])}
MFG = [("pmi", r"^(manufacturing )?pmi"), ("neword", r"^new orders"), ("prod", r"^production"), ("emp", r"^employment"),
       ("supdel", r"^supplier deliveries"), ("inv", r"^inventories"), ("cusinv", r"^customers.? inventories"),
       ("prices", r"^prices"), ("backlog", r"^backlog of orders"), ("exp", r"^(new export orders|exports)"), ("imp", r"^imports")]
SVC = [("pmi", r"^(services pmi|nmi(/pmi)?|non-manufacturing (index|pmi)|pmi)"), ("busact", r"^business activity( ?/ ?production)?"), ("neword", r"^new orders"),
       ("emp", r"^employment"), ("supdel", r"^supplier deliveries"), ("inv", r"^inventories"), ("prices", r"^prices"),
       ("backlog", r"^backlog of orders"), ("exp", r"^(new export orders|exports)"), ("imp", r"^imports"), ("invsent", r"^inventory sentiment")]
NUM = re.compile(r"^-?\d{1,3}(\.\d)?$")

def prev_month(ym):
    y, m = ym
    return (y - 1, 12) if m == 1 else (y, m - 1)

def parse(text, fam):
    i = text.upper().find("AT A GLANCE")
    if i < 0:
        return None
    seg = text[i:i + 6000]
    hm = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", seg, re.I)
    if not hm:
        return None
    ym = (int(hm.group(2)), MONTHS[hm.group(1).lower()])
    cells = [re.sub(r"\s+", " ", c).strip().replace("®", "").replace("™", "").strip() for c in seg[hm.end():].split("|")]
    cells = [c for c in cells if c]
    rows = MFG if fam == "mfg" else SVC
    got = {}
    for j, c in enumerate(cells):
        lc = c.lower().replace("’", "'")
        if lc.startswith("overall economy") or (fam == "mfg" and lc.startswith("manufacturing sector")):
            break
        for key, pat in rows:
            if key in got or not re.match(pat + r"\W*\*?$", lc):
                continue
            nums = []
            for c2 in cells[j + 1:j + 4]:
                if NUM.match(c2):
                    nums.append(float(c2))
                elif c2.upper() in ("N/A", "NA", "*"):
                    nums.append(None)
                else:
                    break
            if len(nums) >= 2:
                got[key] = (nums[0], nums[1])
            break
    if "pmi" not in got:
        return None
    return ym, got
