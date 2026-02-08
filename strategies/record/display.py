# display.py
import os
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import List
from pathlib import Path
from data_api import get_stock_list

app = FastAPI(title="Strategy Viewer")

# Allow local requests from the same origin (the frontend is served by this app).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path("").resolve()

# Try to import user-provided get_stock_info; otherwise provide a simple fallback.
try:
    # from stock_api import get_stock_info  # expecting: def get_stock_info(codes: pd.Series) -> pd.DataFrame
    # print("Imported get_stock_info from stock_api.py")
    def get_stock_info(codes: pd.Series) -> pd.DataFrame:
        #df = get_stock_list(codes)[['股票代码','股票名称','所属行业', '地域','实控人企业性质']].rename(columns={'股票代码':'code'})
        df = get_stock_list(codes)[['股票代码','股票名称','所属行业']].rename(columns={'股票代码':'code'})
        return df
except Exception:
    print("No stock_api.get_stock_info found — using fallback stub (put your own stock_api.py to override).")
    def get_stock_info(codes: pd.Series) -> pd.DataFrame:
        # Minimal stub: returns code, name, market columns
        unique = pd.Series(sorted(pd.unique(codes)))
        df = pd.DataFrame({"code": unique})
        df["name"] = df["code"].apply(lambda c: f"股票{c}")
        df["market"] = "N/A"
        return df

def list_strategies() -> List[str]:
    """Find subdirectories that look like a strategy (have income_record.csv and position_record.csv)."""
    res = []
    for entry in sorted(BASE_DIR.iterdir()):
        if entry.is_dir():
            if (entry / "income_record.csv").exists() and (entry / "position_record.csv").exists():
                res.append(entry.name)
    return res

def normalize_date_str(s: str) -> str:
    """Normalize date string 'yyyymm' or 'yyyymmdd' or other parseable strings to 'YYYY-MM-DD' string.
       For yyyymm we return the first day of month."""
    s = str(s).strip()
    if len(s) == 6 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-01"
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    # fallback: let pandas try
    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return s

def safe_strategy_path(name: str) -> Path:
    # avoid path traversal; only allow names that are existing subdirectories
    candidate = BASE_DIR / name
    if not candidate.exists() or not candidate.is_dir():
        raise HTTPException(status_code=404, detail="Strategy not found")
    if not (candidate / "income_record.csv").exists() or not (candidate / "position_record.csv").exists():
        raise HTTPException(status_code=404, detail="Strategy missing required files")
    return candidate

@app.get("/", response_class=FileResponse)
async def index():
    # serve the provided display.html file in the same folder
    fp = BASE_DIR / "display.html"
    if not fp.exists():
        raise HTTPException(status_code=500, detail="display.html not found in current directory")
    return FileResponse(str(fp))

@app.get("/api/strategies")
async def api_strategies():
    return {"strategies": list_strategies()}

@app.get("/api/strategy/{name}/readme")
async def api_readme(name: str):
    p = safe_strategy_path(name)
    readme = p / "readme.txt"
    if not readme.exists():
        return PlainTextResponse("", status_code=200)
    text = readme.read_text(encoding="utf-8")
    return PlainTextResponse(text, status_code=200)

@app.get("/api/strategy/{name}/income")
async def api_income(name: str):
    p = safe_strategy_path(name)
    f = p / "income_record.csv"
    try:
        df = pd.read_csv(f, dtype={"date": str})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read income_record.csv: {e}")
    if "date" not in df.columns or "income" not in df.columns:
        raise HTTPException(status_code=400, detail="income_record.csv must contain 'date' and 'income' columns")
    df["norm_date"] = df["date"].apply(normalize_date_str)
    # ensure numeric income
    df["income"] = pd.to_numeric(df["income"], errors="coerce")
    df = df.dropna(subset=["income"])
    df = df.sort_values("norm_date")
    # return list of {date, income}
    records = [{"date": d, "income": float(v)} for d, v in zip(df["norm_date"], df["income"])]
    return {"income_series": records}

@app.get("/api/strategy/{name}/dates")
async def api_dates(name: str):
    p = safe_strategy_path(name)
    f = p / "position_record.csv"
    try:
        df = pd.read_csv(f, dtype={"date": str})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read position_record.csv: {e}")
    if "date" not in df.columns:
        raise HTTPException(status_code=400, detail="position_record.csv must contain 'date' column")
    df["norm_date"] = df["date"].apply(normalize_date_str)
    dates = sorted(df["norm_date"].dropna().unique(), reverse=True)
    return {"dates": dates}

@app.get("/api/strategy/{name}/positions")
async def api_positions(name: str, date: str = Query(None, description="date in yyyymm or yyyymmdd or any parseable form")):
    """
    Return positions for a given strategy and date.

    The returned JSON structure:
    {
      "columns": ["code", "name", "...", "收益率"],
      "rows": [
        ["600000", "浦发银行", "...", 12.34],
        ...
      ],
      "date": "YYYY-MM-DD"
    }

    NOTE: For converting the raw 'income' value in position_record.csv to percentage:
      - if income >= 1.0, we assume it's a ratio like 1.05 and convert to (income - 1) * 100
      - else assume it's a decimal return like 0.05 and convert to income * 100
    """
    if date is None:
        raise HTTPException(status_code=400, detail="query param 'date' is required")
    norm_date = normalize_date_str(date)
    p = safe_strategy_path(name)
    f = p / "position_record.csv"
    try:
        df = pd.read_csv(f, dtype={"date": str, "code": str})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read position_record.csv: {e}")
    if not {"date", "code", "income"}.issubset(set(df.columns)):
        raise HTTPException(status_code=400, detail="position_record.csv must contain 'date','code','income' columns")
    df["norm_date"] = df["date"].apply(normalize_date_str)
    df_date = df[df["norm_date"] == norm_date].copy()
    if df_date.empty:
        return {"columns": ["code", "收益率"], "rows": [], "date": norm_date}

    # numeric
    df_date["income_raw"] = pd.to_numeric(df_date["income"], errors="coerce")
    df_date = df_date.dropna(subset=["income_raw"])

    # convert to percentage display with a best-effort rule:
    def to_pct(x):
        try:
            v = float(x)
        except:
            return None
        if v >= 1.0:
            return round((v - 1.0) * 100.0, 2)
        else:
            return round(v * 100.0, 2)
    df_date["pct_return"] = df_date["income_raw"].apply(to_pct)

    # fetch stock info (external API provided by user) and merge
    codes = df_date["code"].astype(str)

    try:
        info_df = get_stock_info(codes)
        # ensure code column exists
        if "code" not in info_df.columns:
            raise ValueError("get_stock_info must return DataFrame with a 'code' column")
        # normalize types
        info_df["code"] = info_df["code"].astype(str)
    except Exception as e:
        # fallback minimal
        info_df = pd.DataFrame({"code": codes.unique()})
        info_df["name"] = info_df["code"].apply(lambda c: f"股票{c}")

    merged = pd.merge(df_date, info_df, on="code", how="left", suffixes=("", "_info"))

    # prepare column order: code, [info columns except 'code'], then '收益率'
    info_cols = [c for c in info_df.columns if c != "code"]
    cols = ["股票代码"] + info_cols + ["收益率"]
    # rows: for each code, values in that order
    merged = merged.sort_values("pct_return", ascending=False)
    rows = []
    for _, row in merged.iterrows():
        code = str(row["code"])
        info_values = [row.get(c, "") for c in info_cols]
        pct = row.get("pct_return")
        # if pct is nan, keep None
        if pd.isna(pct):
            pct_val = None
        else:
            pct_val = float(pct)
        rows.append([code] + info_values + [pct_val])
    return {"columns": cols, "rows": rows, "date": norm_date}

if __name__ == "__main__":
    # run uvicorn programmatically so user can just run `python display.py`
    uvicorn.run("display:app", host="127.0.0.1", port=8000, reload=False)
