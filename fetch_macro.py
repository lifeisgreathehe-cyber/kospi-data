"""Fetch ~20 years of daily commodity prices and FX rates into data/macro_daily.csv.

Sources: Yahoo Finance (yfinance) first; FRED daily series fill gaps
(and supply history where Yahoo is short). Crosses vs KRW are computed
from USD legs (USD/KRW x EUR/USD etc.), which is cleaner than Yahoo's
direct cross tickers.
"""
import io, os, sys, urllib.request
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
# FRED monthly fallbacks for metals with no free daily history (IMF prices)
MONTHLY = {"aluminum": "PALUMUSDM", "copper": "PCOPPUSDM"}


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


def fred(series):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={START}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    txt = urllib.request.urlopen(req, timeout=60).read().decode()
    df = pd.read_csv(io.StringIO(txt))
    df.columns = ["date", "v"]
    s = pd.to_numeric(df["v"], errors="coerce")
    s.index = pd.to_datetime(df["date"])
    return s[s > 0].dropna()


def despike(s, tol=0.12):
    """Drop isolated bad ticks: points far from both the rolling median."""
    med = s.rolling(11, center=True, min_periods=3).median()
    bad = (s / med - 1).abs() > tol
    if bad.any():
        print(f"  despike: dropped {int(bad.sum())} points")
    return s[~bad]


def get(name, ysym, fsym, tol=0.12):
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
    s = get(k, y, f, tol=0.25)  # commodities move a lot; only catch gross errors
    if s is not None:
        cols[k] = s
legs = {}
for k, (y, f) in LEGS.items():
    s = get(k, y, f)
    if s is not None:
        legs[k] = s
if "usdkrw" not in legs:
    sys.exit("USD/KRW unavailable")

# Monthly fallback: fill daily gaps before the daily series starts
for k, sid in MONTHLY.items():
    try:
        m = fred(sid)
        d = cols.get(k)
        first = d.index[0] if d is not None and len(d) else pd.Timestamp("2100-01-01")
        if k == "copper":
            m = m / 2204.62  # USD/t -> USD/lb to match COMEX HG
        m = m[m.index < first]
        if len(m):
            print(f"{k}: monthly {sid} fills {len(m)} months before {first.date()}")
            cols[k] = m if d is None else pd.concat([m, d]).sort_index()
    except Exception as e:
        print(f"{k}: monthly {sid} failed: {e}")

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
        cols[k] = cols[k][cols[k].index.isin(legs["usdkrw"].index)]

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
