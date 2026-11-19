"""Fetch KOSPI (and KOSDAQ) daily OHLCV and write data/kospi_daily.csv.
Tries yfinance first, then FinanceDataReader as a fallback."""
import sys, pandas as pd

START = "2000-01-01"

def via_yf(sym):
    import yfinance as yf
    df = yf.download(sym, start=START, progress=False, auto_adjust=False, threads=False)
    if df is None or df.empty:
        raise RuntimeError("yfinance empty")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]]

def via_fdr(sym):
    import FinanceDataReader as fdr
    df = fdr.DataReader(sym, START)
    if df is None or df.empty:
        raise RuntimeError("fdr empty")
    return df[["Open", "High", "Low", "Close", "Volume"]]

def get(yf_sym, fdr_sym):
    """Fetch from both sources and fill gaps: yfinance first, FDR fills
    missing or NaN closes (Yahoo sometimes leaves the latest day NaN)."""
    frames, errs = [], []
    for name, f, s in (("yfinance", via_yf, yf_sym), ("fdr", via_fdr, fdr_sym)):
        try:
            df = f(s)
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            ok = df.dropna(subset=["Close"])
            print(f"{yf_sym}: {name} ok, {len(ok)} rows with close, last {ok.index[-1].date()}")
            frames.append(df)
        except Exception as e:
            errs.append(f"{name}: {e}")
            print(f"{yf_sym}: {name} failed: {e}")
    if not frames:
        raise SystemExit(f"{yf_sym} failed: {errs}")
    out = frames[0]
    for df in frames[1:]:
        out = out.combine_first(df)
    return out

import os; os.makedirs("data", exist_ok=True)
for yf_sym, fdr_sym, out in (("^KS11", "KS11", "data/kospi_daily.csv"),
                             ("^KQ11", "KQ11", "data/kosdaq_daily.csv")):
    try:
        df = get(yf_sym, fdr_sym)
    except SystemExit as e:
        if out.endswith("kospi_daily.csv"):
            raise
        print(e); continue
    df = df.dropna(subset=["Close"])
    # Drop today's row while the market is still open (before 15:45 KST):
    # GitHub often runs the schedule hours late, so a run can land intraday.
    now = pd.Timestamp.now(tz="Asia/Seoul")
    if len(df) and pd.Timestamp(df.index[-1]).date() == now.date() and (now.hour, now.minute) < (15, 45):
        print(f"{out}: dropping intraday row {now.date()}")
        df = df.iloc[:-1]
    df.index = pd.to_datetime(df.index).strftime("%Y-%m-%d")
    df.index.name = "date"
    df.round(2).to_csv(out)
