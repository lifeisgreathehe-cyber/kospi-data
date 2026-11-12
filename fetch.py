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
    errs = []
    for name, f, s in (("yfinance", via_yf, yf_sym), ("fdr", via_fdr, fdr_sym)):
        try:
            df = f(s)
            print(f"{yf_sym}: {name} ok, {len(df)} rows, last {df.index[-1].date()}")
            return df
        except Exception as e:
            errs.append(f"{name}: {e}")
    raise SystemExit(f"{yf_sym} failed: {errs}")

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
    df.index = pd.to_datetime(df.index).strftime("%Y-%m-%d")
    df.index.name = "date"
    df.round(2).to_csv(out)
