# -*- coding: utf-8 -*-
"""
月度涨跌停（开盘即涨停/跌停）检测

输入:
    datas: DataFrame, MultiIndex=(date, code)
           columns=['open','close']
           date 为 YYYYMM 字符串或 int (例如 199104)

逻辑:
    对每个 code:
        gap_ret = open_t / close_{t-1} - 1
        gap_ret > 0.099  -> 认为该月初首个交易日“开盘涨停”
        gap_ret < -0.099 -> 认为该月初首个交易日“开盘跌停”

输出:
    保存一个 DataFrame (index=(date, code))，包含:
        prev_close, open, close, gap_ret, is_limit_up, is_limit_down

并提供查询函数:
    get_limit_up_codes(yyyymm)  -> Series[code]
    get_limit_down_codes(yyyymm)-> Series[code]
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from tools import datapath

def build_month_open_limit_df(
    datas: pd.DataFrame,
    up_th: float = 0.099,      # 9.9%
    down_th: float = -0.099,   # -9.9%
) -> pd.DataFrame:
    """
    计算每个股票每月 open / 上月 close - 1，并判断月初开盘是否触发涨跌停。

    参数:
        datas: MultiIndex=(date, code) 的月度不复权数据，至少包含 open, close
        save_path: 输出文件路径（建议 parquet/csv/pkl 自选）
        up_th / down_th: 阈值，默认 9.9%/-9.9%

    返回:
        out: MultiIndex=(date, code) 的结果 DataFrame
    """
    save_path = datapath.limit_path
    if not isinstance(datas.index, pd.MultiIndex) or datas.index.nlevels != 2:
        raise ValueError("datas.index 必须是 MultiIndex=(date, code)")
    if not {"open", "close"}.issubset(datas.columns):
        raise ValueError("datas.columns 必须至少包含 ['open','close']")

    df = datas[["open", "close"]].copy()

    # 统一 date 为 YYYYMM 字符串，确保排序正确
    date_level = df.index.get_level_values(0)
    df = df.copy()
    df.index = pd.MultiIndex.from_arrays(
        [date_level.astype(str), df.index.get_level_values(1).astype(str)],
        names=[df.index.names[0] or "date", df.index.names[1] or "code"],
    )

    # 排序：先 code 再 date，便于 shift
    df = df.sort_index(level=[1, 0])

    # 上月收盘
    df["prev_close"] = df.groupby(level=1)["close"].shift(1)

    # gap return
    df["gap_ret"] = df["open"] / df["prev_close"] - 1

    # 特殊情况置 NaN：prev_close<=0、open<=0、inf等
    bad = (
        df["prev_close"].isna()
        | (df["prev_close"] <= 0)
        | df["open"].isna()
        | (df["open"] <= 0)
        | ~np.isfinite(df["gap_ret"])
    )
    df.loc[bad, "gap_ret"] = np.nan

    # 涨跌停标记（NaN 自动为 False）
    df["is_limit_up"] = df["gap_ret"] > up_th
    df["is_limit_down"] = df["gap_ret"] < down_th

    out = df[["prev_close", "open", "close", "gap_ret", "is_limit_up", "is_limit_down"]]

    # 保存（按扩展名决定格式；你也可以固定用 parquet）
    save_lower = save_path.lower()
    if save_lower.endswith(".parquet"):
        out.to_parquet(save_path)
    elif save_lower.endswith(".csv"):
        out.to_csv(save_path)
    elif save_lower.endswith(".pkl") or save_lower.endswith(".pickle"):
        out.to_pickle(save_path)
    else:
        # 默认用 parquet（如果给的是无后缀路径，也能保存为该路径）
        out.to_parquet(save_path)

    return out


def get_limit_up_codes(
    yyyymm: str,
) -> pd.Series:
    """
    输入结果 DataFrame 或其保存路径，返回该月份“开盘涨停”的股票代码 Series。
    """
    limit_df_or_path = datapath.limit_path
    df = _load_limit_df(limit_df_or_path)
    yyyymm = str(yyyymm)

    # 过滤指定月
    idx_date = df.index.get_level_values(0).astype(str)
    sub = df.loc[idx_date == yyyymm]

    codes = sub.index.get_level_values(1)[sub["is_limit_up"].fillna(False)]
    ret =  pd.Series(codes.unique(), name="code")
    ret = ret.astype('str').str.zfill(6)
    return ret


def get_limit_down_codes(
    yyyymm: str,
) -> pd.Series:
    """
    输入结果 DataFrame 或其保存路径，返回该月份“开盘跌停”的股票代码 Series。
    """
    limit_df_or_path = datapath.limit_path
    df = _load_limit_df(limit_df_or_path)
    yyyymm = str(yyyymm)

    idx_date = df.index.get_level_values(0).astype(str)
    sub = df.loc[idx_date == yyyymm]

    codes = sub.index.get_level_values(1)[sub["is_limit_down"].fillna(False)]
    ret = pd.Series(codes.unique(), name="code")
    ret = ret.astype('str').str.zfill(6)
    return ret


def get_limit_codes(
    yyyymm: str,
) -> tuple[pd.Series, pd.Series]:
    """
    一次返回(涨停codes, 跌停codes)
    """
    return (
        get_limit_up_codes(yyyymm),
        get_limit_down_codes(yyyymm),
    )


def _load_limit_df(limit_df_or_path: pd.DataFrame | str) -> pd.DataFrame:
    if isinstance(limit_df_or_path, pd.DataFrame):
        return limit_df_or_path
    path = str(limit_df_or_path)
    lower = path.lower()
    if lower.endswith(".parquet"):
        return pd.read_parquet(path)
    if lower.endswith(".csv"):
        # 注意：csv读回 MultiIndex 需要你保存时包含 index；这里做一个尽量通用的读取
        df = pd.read_csv(path, index_col=[0, 1])
        df.index.names = ["date", "code"]
        return df
    if lower.endswith(".pkl") or lower.endswith(".pickle"):
        return pd.read_pickle(path)
    # 默认 parquet
    return pd.read_parquet(path)

from data_api import get_monthly
if __name__ == "__main__":
    # build_month_open_limit_df(get_monthly())
    (up,down) = get_limit_codes('202601')
    print(up)
    print(down)