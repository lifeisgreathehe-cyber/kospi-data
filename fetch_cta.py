"""NDX CTA positioning proxy.

Goldman's "CTA Positioning in NDX Index" is proprietary, so this builds a
public proxy from two free sources:
  1. data/ndx_daily.csv  : Nasdaq-100 daily close (yfinance ^NDX, FDR fallback)
  2. data/cftc_ndx.csv   : CFTC Traders in Financial Futures, E-mini Nasdaq-100
                           (weekly, leveraged funds / asset managers net)
and computes data/cta_ndx.csv, a trend-following model position:
  for lookbacks 1M/3M/6M (21/63/126 days), trend z = log return / (63d daily vol
  * sqrt(L)), signal = clip(z/0.5, -1, 1); raw = mean of the 3 signals (-1..+1);
  position = raw * min(15% / 126d realized vol, 3)  (vol-targeted, like CTAs).
  est_bn = 8.44 * position + 1.53 maps the model onto the scale of Goldman's chart
  (least-squares fit to 27 points read off that chart, 2017-2026, r = 0.96).
  flip_1m/3m/6m: NDX level at which each lookback's signal turns (price L days ago).
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


A, B = 8.44, 1.53  # calibration to Goldman chart units


def cta_model(px, lookbacks=(21, 63, 126), zcap=0.5, target=0.15, cap=3.0):
    r = np.log(px).diff()
    vol_d = r.rolling(63).std()
    sig = []
    for L in lookbacks:
        z = np.log(px / px.shift(L)) / (vol_d * np.sqrt(L))
        sig.append((z / zcap).clip(-1, 1))
    raw = pd.concat(sig, axis=1).mean(axis=1)
    vol_a = r.rolling(126).std() * np.sqrt(252)
    pos = raw * (target / vol_a).clip(upper=cap)
    out = pd.DataFrame({"close": px, "s1m": sig[0], "s3m": sig[1], "s6m": sig[2],
                        "raw": raw, "vol126": vol_a, "position": pos,
                        "est_bn": A * pos + B,
                        "flip_1m": px.shift(21), "flip_3m": px.shift(63),
                        "flip_6m": px.shift(126)})
    return out.dropna()


def cftc_ndx(raw, px):
    """Consolidated Nasdaq-100 (E-mini equivalents, $20 x index)."""
    c = raw[raw["cftc_contract_market_code"].astype(str) == "20974+"].copy()
    c["date"] = pd.to_datetime(c["report_date_as_yyyy_mm_dd"]).dt.normalize()
    num = lambda k: pd.to_numeric(c[k], errors="coerce")
    c["oi"] = num("open_interest_all")
    c["lev_net"] = num("lev_money_positions_long") - num("lev_money_positions_short")
    c["am_net"] = num("asset_mgr_positions_long") - num("asset_mgr_positions_short")
    c = c.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
    p = px.reindex(c.index, method="ffill")
    c["lev_net_bn"] = (c["lev_net"] * 20 * p / 1e9).round(2)
    c["am_net_bn"] = (c["am_net"] * 20 * p / 1e9).round(2)
    c["lev_net_pct_oi"] = (100 * c["lev_net"] / c["oi"]).round(1)
    out = c[["oi", "lev_net", "am_net", "lev_net_bn", "am_net_bn", "lev_net_pct_oi"]]
    out.index = out.index.strftime("%Y-%m-%d")
    return out


px = ndx_close()
pd.DataFrame({"close": px.round(2)}).rename_axis("date").to_csv(
    "data/ndx_daily.csv", date_format="%Y-%m-%d")

m = cta_model(px).round(4)
m.index = m.index.strftime("%Y-%m-%d")
m.index.name = "date"
m.to_csv("data/cta_ndx.csv")
print("CTA last", m.tail(3).to_string())

try:
    c = cftc_ndx(cftc(), px)
    c.to_csv("data/cftc_ndx.csv")
    print("CFTC last", c.tail(3).to_string())
except Exception as e:
    print("CFTC failed (keeping previous file):", e)
