"""Fetch ~20 years of daily commodity prices and FX rates into data/macro_daily.csv.

Sources: Yahoo Finance (yfinance) first; FRED daily series fill gaps
(when reachable); IMF monthly averages via DBnomics cover
aluminum before COMEX futures became liquid. Crosses vs KRW are computed
from USD legs (USD/KRW x EUR/USD etc.), which is cleaner than Yahoo's
direct cross tickers.
"""
import io, json, os, sys, urllib.request
import pandas as pd

START = "2005-01-01"

# column -> (yahoo symbol, FRED daily series or None)
COMMOD = {
    "wti":      ("CL=F", "DCOILWTICO"),    # USD/bbl
    "brent":    ("BZ=F", "DCOILBRENTEU"),  # USD/bbl
    "natgas":   ("NG=F", "DHHNGSP"),       # USD/MMBtu
    "gold":     ("GC=F", None),            # USD/oz
    "silver":   ("SI=F", None),            # USD/oz
    "copper":   ("HG=F", None),            # USD/lb
    "aluminum": ("ALI=F", None),           # USD/t
}
LEGS = {  # USD legs used to build the FX table
    "usdkrw": ("KRW=X", "DEXKOUS"),        # KRW per USD
    "eurusd": ("EURUSD=X", "DEXUSEU"),     # USD per EUR
    "usdcny": ("CNY=X", "DEXCHUS"),        # CNY per USD
    "usdjpy": ("JPY=X", "DEXJPUS"),        # JPY per USD
}
# Metals whose free daily futures history is short or stale (COMEX ALI=F
# barely traded before 2020): IMF monthly averages (LME) are used before CUTOVER.
MONTHLY = {"aluminum": ("PALUM", "2020-01-01")}


def yahoo(sym):
    import yfinance as yf
    df = yf.download(sym, start=START, progress=False, auto_adjust=False, threads=False)
    if df is None or df.empty:
        raise RuntimeError("empty")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    s = df["Close"].astype(float)
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s[s > 0].dropna()


FRED_OK = [True]


def fred(series):
    """FRED often times out from GitHub runners: give up after the first failure."""
    if not FRED_OK[0]:
        raise RuntimeError("skipped (FRED unreachable earlier)")
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={START}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        txt = urllib.request.urlopen(req, timeout=15).read().decode()
    except Exception:
        FRED_OK[0] = False
        raise
    df = pd.read_csv(io.StringIO(txt))
    df.columns = ["date", "v"]
    s = pd.to_numeric(df["v"], errors="coerce")
    s.index = pd.to_datetime(df["date"])
    return s[s > 0].dropna()


def imf_monthly(code):
    """IMF primary commodity prices (monthly average, USD) via DBnomics."""
    url = f"https://api.db.nomics.world/v22/series/IMF/PCPS/M.W00.{code}.USD?observations=1&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    doc = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())["series"]["docs"][0]
    s = pd.Series(pd.to_numeric(doc["value"], errors="coerce"), index=pd.to_datetime(doc["period"]))
    return s[s > 0].dropna()


def despike(s, tol):
    """Drop one-day bad ticks: a point that jumps away from both neighbours
    (same direction, more than tol) while the neighbours agree with each other."""
    s = s.copy()
    for _ in range(2):
        a, b = s.shift(1), s.shift(-1)
        r1, r2, nb = s / a - 1, s / b - 1, (a / b - 1).abs()
        bad = (r1 * r2 > 0) & (r1.abs() > tol) & (r2.abs() > tol) & (nb < tol / 2)
        if not bad.any():
            break
        print(f"  despike: dropped {int(bad.sum())} points: {list(s.index[bad].strftime('%Y-%m-%d'))[:8]}")
        s = s[~bad]
    return s


def get(name, ysym, fsym, tol):
    parts = []
    for label, fn, sym in (("yahoo", yahoo, ysym), ("fred", fred, fsym)):
        if not sym:
            continue
        try:
            s = fn(sym)
            print(f"{name}: {label} {sym} {len(s)} rows {s.index[0].date()}..{s.index[-1].date()} last={s.iloc[-1]:.4f}")
            parts.append(s)
        except Exception as e:
            print(f"{name}: {label} {sym} failed: {e}")
    if not parts:
        return None
    out = parts[0]
    for p in parts[1:]:
        out = out.combine_first(p)
    return despike(out.sort_index(), tol)


cols = {}
for k, (y, f) in COMMOD.items():
    s = get(k, y, f, tol=0.2 if k == "natgas" else 0.12)  # catch only gross bad ticks
    if s is not None:
        cols[k] = s
legs = {}
for k, (y, f) in LEGS.items():
    s = get(k, y, f, tol=0.04 if k == "usdkrw" else 0.025)
    if s is not None:
        legs[k] = s
if "usdkrw" not in legs:
    sys.exit("USD/KRW unavailable")

# Monthly fallback before the daily series is usable
for k, (code, cut) in MONTHLY.items():
    try:
        m = imf_monthly(code)
        m = m[(m.index >= START) & (m.index < cut)]
        d = cols.get(k)
        d = d[d.index >= cut] if d is not None else None
        print(f"{k}: IMF monthly {code} {len(m)} months before {cut}")
        cols[k] = m if d is None else pd.concat([m, d]).sort_index()
    except Exception as e:
        print(f"{k}: IMF monthly {code} failed: {e}; keeping daily futures only")

fx = pd.DataFrame(legs).sort_index()
# Cross rates need same-day legs; carry a leg forward at most 3 days
fx = fx.ffill(limit=3)
cols["usdkrw"] = legs["usdkrw"]
if "eurusd" in fx: cols["eurkrw"] = (fx.usdkrw * fx.eurusd).dropna()
if "usdcny" in fx: cols["cnykrw"] = (fx.usdkrw / fx.usdcny).dropna()
if "usdjpy" in fx:
    cols["jpykrw100"] = (fx.usdkrw / fx.usdjpy * 100).dropna()
    cols["usdjpy"] = legs["usdjpy"]
# Keep cross values only on days the USD/KRW leg itself traded
for k in ("eurkrw", "cnykrw", "jpykrw100"):
    if k in cols:
        cols[k] = despike(cols[k][cols[k].index.isin(legs["usdkrw"].index)], 0.025)

order = ["wti", "brent", "natgas", "gold", "silver", "copper", "aluminum",
         "usdkrw", "eurkrw", "cnykrw", "jpykrw100", "usdjpy"]
df = pd.DataFrame({k: cols[k] for k in order if k in cols}).sort_index()
df = df[df.index >= START]
# Drop today's row before the Asian close is in (runs land at odd hours)
now = pd.Timestamp.now(tz="Asia/Seoul")
df = df[df.index.date < now.date()] if now.hour < 16 else df[df.index.date <= now.date()]
df = df.dropna(how="all")
rnd = {"wti": 2, "brent": 2, "natgas": 3, "gold": 1, "silver": 3, "copper": 4,
       "aluminum": 1, "usdkrw": 2, "eurkrw": 2, "cnykrw": 3, "jpykrw100": 2, "usdjpy": 3}
df = df.round({k: v for k, v in rnd.items() if k in df})
df.index = df.index.strftime("%Y-%m-%d")
df.index.name = "date"
os.makedirs("data", exist_ok=True)
df.to_csv("data/macro_daily.csv")
print("wrote", len(df), "rows", df.index[0], "..", df.index[-1])
print(df.tail(3).to_string())
print(df.notna().sum().to_string())
