# -*- coding: utf-8 -*-
"""
Memory-optimized A-share daily/monthly builder (unadjusted, qfq, hfq)
from per-stock daily CSVs + qfq factors.

Key optimizations vs previous version
- build_daily: no big concat; append file-by-file to output (codes are naturally grouped)
- build_daily_qfq / build_daily_hfq: stream-read daily.csv in chunks, process one-stock-at-a-time
  (works because build_daily writes files in sorted filename order -> codes are contiguous)
- build_monthly*: also stream one-stock-at-a-time
- Fix dtype warnings: enforce dtype for 日期/股票代码 as string
- Fix ZeroDivisionError: safe division when prev_close == 0 (set derived metrics to 0)

Assumptions
- {code}_daily.csv files each contain only one stock code (as in your examples)
- Factor dir contains files like 000001.SZ.csv; we match by leading 6 digits
- daily.csv produced by build_daily is grouped by 股票代码 contiguously (because we write files in
  sorted order). Do NOT shuffle daily.csv after building, otherwise streaming-by-code won't work.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

import numpy as np
import pandas as pd

# ---------- Columns ----------
COL_DATE = "日期"
COL_CODE = "股票代码"

PRICE_COLS = ["开盘", "收盘", "最高", "最低"]
DERIVED_COLS = ["振幅", "涨跌幅", "涨跌额"]
KEEP_COLS = [
    "日期", "股票代码",
    "开盘", "收盘", "最高", "最低",
    "成交量", "成交额",
    "振幅", "涨跌幅", "涨跌额",
    "换手率",
]

FACTOR_DATE = "交易日期"
FACTOR_VAL = "复权因子"


# ---------- IO Helpers ----------
def _ensure_parent_dir(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _safe_read_csv(path: str | Path, dtype: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """
    Try utf-8-sig first, fallback to gbk. Force dtype for specified columns to avoid mixed-type warnings.
    """
    path = str(path)
    try:
        return pd.read_csv(path, encoding="utf-8-sig", dtype=dtype, low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="gbk", dtype=dtype, low_memory=False)


def _to_yyyymmdd_str(series: pd.Series) -> pd.Series:
    """
    Convert 'YYYY-MM-DD' or 'YYYYMMDD' to 'YYYYMMDD' (string).
    """
    s = series.astype(str).str.strip()
    mask8 = s.str.match(r"^\d{8}$", na=False)
    out = pd.Series(index=s.index, dtype="object")
    out[mask8] = s[mask8]
    if (~mask8).any():
        dt = pd.to_datetime(s[~mask8], errors="coerce")
        out[~mask8] = dt.dt.strftime("%Y%m%d")
    return out


def _normalize_code(code: str) -> str:
    """
    '000001.SZ' -> '000001', '000001' -> '000001'
    """
    if code is None:
        return ""
    code = str(code).strip()
    m = re.match(r"^(\d{6})", code)
    return m.group(1) if m else code


def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ---------- Math Helpers ----------
def _safe_divide(numer: np.ndarray, denom: np.ndarray) -> np.ndarray:
    """
    elementwise numer/denom, but denom==0 or nan -> nan (no ZeroDivisionError)
    """
    out = np.full_like(numer, np.nan, dtype="float64")
    mask = np.isfinite(denom) & (denom != 0)
    out[mask] = numer[mask] / denom[mask]
    return out


def _recompute_daily_derived_one_stock(df_one: pd.DataFrame) -> pd.DataFrame:
    """
    df_one: single stock, sorted by 日期 ascending, with adjusted OHLC already.
    Recompute:
      涨跌额 = close - prev_close
      涨跌幅 = 涨跌额 / prev_close * 100
      振幅   = (high - low) / prev_close * 100
    For first row OR prev_close==0 -> set derived to 0.0
    """
    df = df_one.copy()
    close = df["收盘"].to_numpy(dtype="float64")
    high = df["最高"].to_numpy(dtype="float64")
    low = df["最低"].to_numpy(dtype="float64")

    prev_close = np.roll(close, 1)
    prev_close[0] = np.nan

    diff = close - prev_close
    pct = _safe_divide(diff, prev_close) * 100.0
    amp = _safe_divide(high - low, prev_close) * 100.0

    # where prev_close is nan or 0, set to 0
    bad = ~np.isfinite(prev_close) | (prev_close == 0)
    diff[bad] = 0.0
    pct[bad] = 0.0
    amp[bad] = 0.0

    df["涨跌额"] = diff
    df["涨跌幅"] = pct
    df["振幅"] = amp
    return df


def _recompute_monthly_derived_one_stock(df_one_monthly: pd.DataFrame) -> pd.DataFrame:
    """
    monthly derived metrics using prev monthly close (same formula)
    """
    df = df_one_monthly.copy()
    close = df["收盘"].to_numpy(dtype="float64")
    high = df["最高"].to_numpy(dtype="float64")
    low = df["最低"].to_numpy(dtype="float64")

    prev_close = np.roll(close, 1)
    prev_close[0] = np.nan

    diff = close - prev_close
    pct = _safe_divide(diff, prev_close) * 100.0
    amp = _safe_divide(high - low, prev_close) * 100.0

    bad = ~np.isfinite(prev_close) | (prev_close == 0)
    diff[bad] = 0.0
    pct[bad] = 0.0
    amp[bad] = 0.0

    df["涨跌额"] = diff
    df["涨跌幅"] = pct
    df["振幅"] = amp
    return df


# ---------- Factor Loading ----------
def _find_factor_file_for_code(qfq_factor_dir: str | Path, code6: str) -> Optional[Path]:
    """
    Find {code6}.??.csv like 000001.SZ.csv. Return first match if exists.
    """
    qfq_factor_dir = Path(qfq_factor_dir)
    # Most common: 000001.SZ.csv or 000001.SH.csv
    candidates = sorted(qfq_factor_dir.glob(f"{code6}.*.csv"))
    if candidates:
        return candidates[0]
    # fallback: any file starting with code6
    candidates = sorted(qfq_factor_dir.glob(f"{code6}*.csv"))
    return candidates[0] if candidates else None


def _load_factor_for_code(qfq_factor_dir: str | Path, code6: str) -> pd.Series:
    """
    Return a Series indexed by 日期(YYYYMMDD) -> 复权因子(float).
    If file missing, return empty Series.
    """
    fp = _find_factor_file_for_code(qfq_factor_dir, code6)
    if fp is None:
        return pd.Series(dtype="float64")

    f = _safe_read_csv(fp, dtype={"股票代码": "string", FACTOR_DATE: "string"})
    need = {"股票代码", FACTOR_DATE, FACTOR_VAL}
    if not need.issubset(set(f.columns)):
        raise ValueError(f"Factor file {fp.name} missing required columns: {need}")

    f = f[["股票代码", FACTOR_DATE, FACTOR_VAL]].copy()
    f["股票代码"] = f["股票代码"].map(_normalize_code)
    f = f[f["股票代码"] == code6]
    f[FACTOR_DATE] = _to_yyyymmdd_str(f[FACTOR_DATE])
    f[FACTOR_VAL] = pd.to_numeric(f[FACTOR_VAL], errors="coerce")
    f = f.dropna(subset=[FACTOR_DATE, FACTOR_VAL])

    s = f.set_index(FACTOR_DATE)[FACTOR_VAL].astype("float64")
    # if duplicate date, keep last
    s = s[~s.index.duplicated(keep="last")]
    return s.sort_index()


# ---------- Streaming daily.csv grouped-by-code ----------
def _iter_daily_by_code(
    daily_csv_path: str | Path,
    chunksize: int = 400_000,
) -> Iterator[Tuple[str, pd.DataFrame]]:
    """
    Stream read daily.csv and yield (code, df_one_stock) in order.

    IMPORTANT: This assumes daily.csv is grouped by 股票代码 contiguously.
    That is guaranteed if you generate daily.csv by build_daily() in this file
    and do not shuffle it afterwards.
    """
    dtype = {COL_DATE: "string", COL_CODE: "string"}
    usecols = KEEP_COLS

    reader = pd.read_csv(
        daily_csv_path,
        encoding="utf-8-sig",
        dtype=dtype,
        usecols=usecols,
        low_memory=False,
        chunksize=chunksize,
    )

    cur_code: Optional[str] = None
    buf_parts: list[pd.DataFrame] = []

    for chunk in reader:
        chunk[COL_CODE] = chunk[COL_CODE].map(_normalize_code)
        chunk[COL_DATE] = _to_yyyymmdd_str(chunk[COL_DATE])
        chunk = _coerce_numeric(
            chunk,
            PRICE_COLS + ["成交量", "成交额", "换手率", "振幅", "涨跌幅", "涨跌额"],
        )

        # iterate by code blocks in this chunk
        # Because codes are contiguous, we can split by changes
        codes = chunk[COL_CODE].to_numpy()
        if len(codes) == 0:
            continue

        # find boundaries where code changes
        change_idx = np.nonzero(codes[1:] != codes[:-1])[0] + 1
        starts = np.r_[0, change_idx]
        ends = np.r_[change_idx, len(chunk)]

        for s, e in zip(starts, ends):
            part = chunk.iloc[s:e].copy()
            code = str(part[COL_CODE].iloc[0])

            if cur_code is None:
                cur_code = code
                buf_parts = [part]
            elif code == cur_code:
                buf_parts.append(part)
            else:
                df_one = pd.concat(buf_parts, ignore_index=True)
                yield cur_code, df_one
                cur_code = code
                buf_parts = [part]

    if cur_code is not None and buf_parts:
        df_one = pd.concat(buf_parts, ignore_index=True)
        yield cur_code, df_one


# ---------- Core Build Functions ----------
def build_daily(daily_dir: str | Path, out_path: str | Path) -> None:
    """
    Merge {code}_daily.csv into one daily.csv.
    Memory-optimized: write incrementally (no big concat).
    Output 日期 -> YYYYMMDD.
    """
    daily_dir = Path(daily_dir)
    files = sorted(daily_dir.glob("*_daily.csv"))
    if not files:
        raise FileNotFoundError(f"No '*_daily.csv' found in: {daily_dir}")

    _ensure_parent_dir(out_path)
    out_path = Path(out_path)
    if out_path.exists():
        out_path.unlink()  # overwrite

    wrote_header = False
    for fp in files:
        x = _safe_read_csv(fp, dtype={COL_DATE: "string", COL_CODE: "string"})
        if not set(KEEP_COLS).issubset(x.columns):
            missing = [c for c in KEEP_COLS if c not in x.columns]
            raise ValueError(f"{fp.name} missing columns: {missing}")

        x = x[KEEP_COLS].copy()
        x[COL_DATE] = _to_yyyymmdd_str(x[COL_DATE])
        x[COL_CODE] = x[COL_CODE].map(_normalize_code)

        x = _coerce_numeric(x, PRICE_COLS + ["成交量", "成交额", "换手率", "振幅", "涨跌幅", "涨跌额"])
        x = x.dropna(subset=[COL_DATE, COL_CODE])

        # per-file (per stock) ensure date sorted
        x = x.sort_values(COL_DATE).reset_index(drop=True)

        x.to_csv(
            out_path,
            index=False,
            encoding="utf-8-sig",
            mode="a",
            header=not wrote_header,
        )
        wrote_header = True


def _apply_adjustment_streaming(
    daily_csv_path: str | Path,
    qfq_factor_dir: str | Path,
    out_path: str | Path,
    mode: str,  # "qfq" or "hfq"
    chunksize: int = 400_000,
) -> None:
    """
    Stream version: process one stock at a time to reduce memory.
    """
    mode = mode.lower().strip()
    if mode not in ("qfq", "hfq"):
        raise ValueError("mode must be 'qfq' or 'hfq'")

    _ensure_parent_dir(out_path)
    out_path = Path(out_path)
    if out_path.exists():
        out_path.unlink()  # overwrite

    wrote_header = False

    for code, df_one in _iter_daily_by_code(daily_csv_path, chunksize=chunksize):
        # sort by date just in case
        df_one = df_one.sort_values(COL_DATE).reset_index(drop=True)

        fac = _load_factor_for_code(qfq_factor_dir, code)
        # map factor to rows; missing -> 1.0
        factor = df_one[COL_DATE].map(fac).astype("float64").fillna(1.0).to_numpy(dtype="float64")

        if mode == "qfq":
            adj = factor
        else:
            # hfq derived from qfq factor
            first = factor[0] if len(factor) else 1.0
            if (not np.isfinite(first)) or first == 0:
                first = 1.0
            adj = factor / first

        # apply adj to OHLC
        for c in PRICE_COLS:
            df_one[c] = pd.to_numeric(df_one[c], errors="coerce") * adj

        # recompute derived metrics safely (fix divide-by-zero)
        df_one = _recompute_daily_derived_one_stock(df_one)

        out = df_one[KEEP_COLS].copy()
        out.to_csv(
            out_path,
            index=False,
            encoding="utf-8-sig",
            mode="a",
            header=not wrote_header,
        )
        wrote_header = True


def build_daily_qfq(daily_csv_path: str | Path, qfq_factor_dir: str | Path, out_path: str | Path) -> None:
    _apply_adjustment_streaming(daily_csv_path, qfq_factor_dir, out_path, mode="qfq")


def build_daily_hfq(daily_csv_path: str | Path, qfq_factor_dir: str | Path, out_path: str | Path) -> None:
    _apply_adjustment_streaming(daily_csv_path, qfq_factor_dir, out_path, mode="hfq")


def build_monthly(daily_csv_path: str | Path, out_path: str | Path, chunksize: int = 400_000) -> None:
    """
    Stream daily -> monthly. One stock at a time.
    Monthly fields:
      日期: last trading day of month (YYYYMMDD)
      开盘: first open of month
      收盘: last close of month
      最高/最低: max/min
      成交量/成交额: sum
      换手率: sum
      振幅/涨跌幅/涨跌额: recomputed using prev monthly close (safe)
    """
    _ensure_parent_dir(out_path)
    out_path = Path(out_path)
    if out_path.exists():
        out_path.unlink()

    wrote_header = False

    for code, df_one in _iter_daily_by_code(daily_csv_path, chunksize=chunksize):
        df_one = df_one.sort_values(COL_DATE).reset_index(drop=True)

        # build dt + month key
        dt = pd.to_datetime(df_one[COL_DATE], format="%Y%m%d", errors="coerce")
        df_one = df_one[dt.notna()].copy()
        dt = pd.to_datetime(df_one[COL_DATE], format="%Y%m%d", errors="coerce")
        df_one["__dt"] = dt
        df_one["__ym"] = df_one["__dt"].dt.to_period("M")

        # aggregate
        agg = {
            "开盘": "first",
            "收盘": "last",
            "最高": "max",
            "最低": "min",
            "成交量": "sum",
            "成交额": "sum",
            "换手率": "sum",
            "__dt": "last",  # last trading day
        }
        m = df_one.groupby([COL_CODE, "__ym"], as_index=False).agg(agg)
        m[COL_DATE] = m["__dt"].dt.strftime("%Y%m%d")
        m = m.drop(columns=["__ym", "__dt"])

        # recompute derived
        m = m.sort_values(COL_DATE).reset_index(drop=True)
        m = _recompute_monthly_derived_one_stock(m)

        out = m[KEEP_COLS].copy()
        out.to_csv(out_path, index=False, encoding="utf-8-sig", mode="a", header=not wrote_header)
        wrote_header = True


def build_monthly_qfq(daily_qfq_csv_path: str | Path, out_path: str | Path) -> None:
    build_monthly(daily_qfq_csv_path, out_path)


def build_monthly_hfq(daily_hfq_csv_path: str | Path, out_path: str | Path) -> None:
    build_monthly(daily_hfq_csv_path, out_path)


# ---------- Pipeline ----------
def pipeline(
    daily_dir: str | Path,
    qfq_factor_dir: str | Path,
    out_daily_csv: str | Path,
    out_daily_qfq_csv: str | Path,
    out_daily_hfq_csv: str | Path,
    out_monthly_csv: str | Path,
    out_monthly_qfq_csv: str | Path,
    out_monthly_hfq_csv: str | Path,
) -> None:
    print("[1/6] build_daily: merge per-stock daily files -> daily.csv (stream append)")
    # build_daily(daily_dir, out_daily_csv)
    print(f"      saved: {out_daily_csv}")

    print("[2/6] build_daily_qfq: compute qfq adjusted daily.csv (stream by code)")
    # build_daily_qfq(out_daily_csv, qfq_factor_dir, out_daily_qfq_csv)
    print(f"      saved: {out_daily_qfq_csv}")

    print("[3/6] build_daily_hfq: compute hfq adjusted daily.csv (derived from qfq factors, stream by code)")
    # build_daily_hfq(out_daily_csv, qfq_factor_dir, out_daily_hfq_csv)
    print(f"      saved: {out_daily_hfq_csv}")

    print("[4/6] build_monthly: daily -> monthly (stream by code)")
    # build_monthly(out_daily_csv, out_monthly_csv)
    print(f"      saved: {out_monthly_csv}")

    print("[5/6] build_monthly_qfq: qfq daily -> qfq monthly (stream by code)")
    # build_monthly_qfq(out_daily_qfq_csv, out_monthly_qfq_csv)
    print(f"      saved: {out_monthly_qfq_csv}")

    print("[6/6] build_monthly_hfq: hfq daily -> hfq monthly (stream by code)")
    build_monthly_hfq(out_daily_hfq_csv, out_monthly_hfq_csv)
    print(f"      saved: {out_monthly_hfq_csv}")

    print("✅ pipeline done.")


from tools import datapath
if __name__ == "__main__":
    # -----------------------------
    # Assumed paths (edit to yours)
    # -----------------------------
    DAILY_DIR = datapath.data_path + "daily/"
    QFQ_FACTOR_DIR = datapath.data_path + "复权因子_前复权/"

    OUT_DIR = datapath.data_path + "pv/"
    OUT_DAILY = OUT_DIR + "daily.csv"
    OUT_DAILY_QFQ = OUT_DIR + "daily_qfq.csv"
    OUT_DAILY_HFQ = OUT_DIR + "daily_hfq.csv"
    OUT_MONTHLY = OUT_DIR + "monthly.csv"
    OUT_MONTHLY_QFQ = OUT_DIR + "monthly_qfq.csv"
    OUT_MONTHLY_HFQ = OUT_DIR + "monthly_hfq.csv"

    pipeline(
        daily_dir=DAILY_DIR,
        qfq_factor_dir=QFQ_FACTOR_DIR,
        out_daily_csv=OUT_DAILY,
        out_daily_qfq_csv=OUT_DAILY_QFQ,
        out_daily_hfq_csv=OUT_DAILY_HFQ,
        out_monthly_csv=OUT_MONTHLY,
        out_monthly_qfq_csv=OUT_MONTHLY_QFQ,
        out_monthly_hfq_csv=OUT_MONTHLY_HFQ,
    )