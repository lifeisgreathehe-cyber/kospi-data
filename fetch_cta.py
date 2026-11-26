"""NDX CTA positioning proxy.

Goldman's "CTA Positioning in NDX Index" is proprietary, so this builds a
public proxy from two free sources:
  1. data/ndx_daily.csv  : Nasdaq-100 daily close (yfinance ^NDX, FDR fallback)
  2. data/cftc_ndx.csv   : CFTC Traders in Financial Futures, E-mini Nasdaq-100
                           (weekly, leveraged funds / asset managers net)
and computes data/cta_ndx.csv, a trend-following model position:
  for lookbacks 1M/3M/6M/12M, trend z = log return / (63d daily vol * sqrt(L)),
  signal = clip(z, -1, 1); raw = mean of the 4 signals (-1..+1);
  position = raw * min(target_vol / realized_vol, cap)  (vol-targeted, like CTAs).
"""
import os, json, urllib.request, urllib.parse
import numpy as np, pandas as pd

START = "1999-01-01"
os.makedirs("data", exist_ok=True)


def ndx_close():
    frames = []
    try:
        import yfinance as yf
        df = yf.download("^NDX", start=START, progress=False, auto_adjust=False, threads=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        s = df["Close"].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
        print(f"^NDX yfinance ok {len(s)} last {s.index[-1].date()}")
        frames.append(s)
    except Exception as e:
        print("yfinance failed:", e)
    for sym in ("NDX", "^NDX"):
        try:
            import FinanceDataReader as fdr
            s = fdr.DataReader(sym, START)["Close"].dropna()
            s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
            print(f"FDR {sym} ok {len(s)} last {s.index[-1].date()}")
            frames.append(s)
            break
        except Exception as e:
            print(f"FDR {sym} failed:", e)
    if not frames:
        raise SystemExit("no NDX data")
    out = frames[0]
    for s in frames[1:]:
        out = out.combine_first(s)
    # Drop today's row while the US market is still open (before 16:15 New York).
    now = pd.Timestamp.now(tz="America/New_York")
    if out.index[-1].date() == now.date() and (now.hour, now.minute) < (16, 15):
        print("dropping intraday NDX row", now.date())
        out = out.iloc[:-1]
    return out.sort_index()


def cftc():
    """CFTC TFF futures-only, all NASDAQ markets (filtered later by code)."""
    base = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
    q = {"$where": "upper(market_and_exchange_names) like '%NASDAQ%'",
         "$limit": "50000", "$order": "report_date_as_yyyy_mm_dd"}
    url = base + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "kospi-data-bot"})
    rows = json.load(urllib.request.urlopen(req, timeout=60))
    df = pd.DataFrame(rows)
    print("CFTC rows", len(df), "markets:",
          df.groupby(["cftc_contract_market_code", "market_and_exchange_names"]).size().to_dict())
    return df


def cta_model(px, lookbacks=(21, 63, 126, 252), target=0.15, cap=2.0):
    r = np.log(px).diff()
    vol_d = r.rolling(63).std()
    sig = []
    for L in lookbacks:
        z = np.log(px / px.shift(L)) / (vol_d * np.sqrt(L))
        sig.append(z.clip(-1, 1))
    raw = pd.concat(sig, axis=1).mean(axis=1)
    vol_a = r.rolling(21).std() * np.sqrt(252)
    lev = (target / vol_a).clip(upper=cap)
    pos = raw * lev
    out = pd.DataFrame({"close": px, "s1m": sig[0], "s3m": sig[1], "s6m": sig[2],
                        "s12m": sig[3], "raw": raw, "vol21": vol_a, "position": pos})
    return out.dropna()


px = ndx_close()
pd.DataFrame({"close": px.round(2)}).rename_axis("date").to_csv(
    "data/ndx_daily.csv", date_format="%Y-%m-%d")

m = cta_model(px).round(4)
m.index = m.index.strftime("%Y-%m-%d")
m.index.name = "date"
m.to_csv("data/cta_ndx.csv")
print("CTA last", m.tail(3).to_string())

try:
    c = cftc()
    c.to_csv("data/cftc_nasdaq_raw.csv", index=False)
except Exception as e:
    print("CFTC failed (keeping previous file):", e)
