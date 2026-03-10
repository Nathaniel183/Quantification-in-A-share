import pandas as pd
import numpy as np
import factors
from factors import factor_lab

def revenue(vals:list[factors.Factor],
            period:int = 12,
            period_dict:dict=None,
            method='mean',
            **kwargs):
    # 1.构建收益率和变量
    change = factors.Change()
    df = factor_lab.concat(vals)
    date_list = df.index.get_level_values('date').unique().tolist()
    date_list = sorted(date_list)

    # 2.回归获得系数
    params = factor_lab.ols_regress(change, df)
    if 'market' in df.columns: df = df.drop('market', axis=1)
    # 3.计算预计收益率
    result_list = []

    if period_dict is None:
        max_period = period
    else:
        max_period = max(period_dict.values())

    for d_i, date in enumerate(date_list[1:]):
        i = params.index.get_loc(date_list[d_i])
        # print(f"时期 -- {date}")
        # 4.跳过前period个时期
        if i < max_period-1:
            continue

        # 5.计算参数平均值
        # if period_dict is None:
        #     par_m = params[i-period+1:i+1].mean()
        # else:
        #     par_m = pd.Series({
        #         col: params[col].iloc[i - period_dict.get(col, period) + 1:i + 1].mean()
        #         if col in period_dict else
        #         params[col].iloc[i - period + 1:i + 1].mean()
        #         for col in params.columns
        #     })

        if period_dict is None:
            if method == 'mean':
                par_m = params.iloc[i - period + 1:i + 1].mean()
            elif method == 'ewma':
                lam = kwargs.get('lam', 0.94)
                par_m = params.iloc[i - period + 1:i + 1].apply(
                    lambda s: ewma_beta(s, lam=lam)
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
        else:
            if method == 'mean':
                par_m = pd.Series({
                    col: params[col].iloc[i - period_dict.get(col, period) + 1:i + 1].mean()
                    for col in params.columns
                })
            elif method == 'ewma':
                lam_default = kwargs.get('lam', 0.94)
                lam_dict = kwargs.get('lam_dict', None)

                par_m = pd.Series({
                    col: ewma_beta(
                        params[col].iloc[i - period_dict.get(col, period) + 1:i + 1],
                        lam=lam_dict.get(col, lam_default) if lam_dict is not None else lam_default
                    )
                    for col in params.columns
                })
            else:
                raise ValueError(f"Unsupported method: {method}")

        # 6.预测
        result = factor_lab.predict(df, par_m, date)
        result_list.append(result)
    ret = pd.concat(result_list, axis=0, ignore_index=False)
    return ret


def risk(vals:list[factors.Factor], period:int=12):
    # 1.构建收益率和变量
    change = factors.Change()
    size = factors.Size().get_data()
    w = np.exp(0.5 * size)

    df = factor_lab.concat(vals)
    date_list = df.index.get_level_values('date').unique().tolist()
    date_list = sorted(date_list)
    # 2.回归获得系数和残差
    params, residuals = factor_lab.wls_regress(change, df, w)

    # print("WLS")
    # print(params)
    # print(residuals)
    # return None
    # 3.计算预计收益率
    sigmas = {}
    for d_i, date in enumerate(date_list[1:]):
        i = params.index.get_loc(date_list[d_i])
        # print(f"时期 -- {date}")
        # 4.跳过前period个时期
        if i < period-1:
            continue
        # 5.计算参数平均值
        # df_t: DataFrame(index=code, columns=exposure factors at this date)
        # par_t: DataFrame(index=date_window, columns=factor coefficients + 'const')  # 你已截取好窗口
        # residuals: Series(index=(date, code), value=eps)

        df_t = df.xs(date, level='date')
        par_t = params[i - period + 1:i + 1]

        # =========================
        # 在 date 循环里：你已有 df_t / par_t / residuals
        # df_t: DataFrame(index=code, columns=因子暴露)
        # par_t: DataFrame(index=dates_win, columns=因子系数 + const)  # 你已截取好窗口
        # residuals: Series(index=(date, code), value=eps)
        # =========================

        # ---------- 0) 统一 residuals 的 MultiIndex 层级顺序，并排序（建议放到循环外做一次；放这里也能跑） ----------
        if isinstance(residuals.index, pd.MultiIndex):
            if residuals.index.names != ['date', 'code']:
                residuals = residuals.reorder_levels(['date', 'code'])
            residuals = residuals.sort_index()
        else:
            raise TypeError("residuals.index 需要是 MultiIndex，且包含 ['date','code'] 两层。")

        # ---------- 1) 对齐因子列 ----------
        # 只取 df_t 和 par_t 都有的列，并排除 const
        factor_cols = [c for c in df_t.columns if (c in par_t.columns) and (c != 'const')]
        X = df_t[factor_cols].astype(float)  # N x K
        F_ret = par_t[factor_cols].astype(float)  # L x K

        # ---------- 2) 估计因子协方差 F ----------
        # 最干净：样本协方差（你也可以换 EWMA）
        F = F_ret.cov()  # K x K

        # ---------- 3) 估计特质方差 D：用窗口期残差 eps 的方差 ----------
        codes = X.index
        dates_win = par_t.index  # 你窗口期 date 列表（必须与 residuals 的 date level 类型一致）

        # 关键：构造 dates_win × codes 的完整 MultiIndex，再 reindex（缺失不报错 -> NaN）
        mi = pd.MultiIndex.from_product([list(dates_win), list(codes)], names=['date', 'code'])
        eps_win = residuals.reindex(mi)

        # 每只股票的 residual 方差（NaN 自动忽略）
        spec_var = eps_win.groupby(level='code').var(ddof=1)

        # 缺失/样本太少 -> 用中位数兜底；再加下限防 0
        fallback = float(spec_var.median()) if spec_var.notna().any() else 1e-6
        spec_var = spec_var.reindex(codes).fillna(fallback).clip(lower=1e-12)

        D = pd.DataFrame(np.diag(spec_var.to_numpy()), index=codes, columns=codes)  # N x N

        # ---------- 4) 拼 Σ = X F X^T + D ----------
        Sigma = X.to_numpy() @ F.to_numpy() @ X.to_numpy().T + D.to_numpy()
        result = pd.DataFrame(Sigma, index=codes, columns=codes)

        # 现在 result 就是当期 date 的协方差矩阵 Σ，可用来后续风险评估/优化
        # 例如：sigmas[date] = result

        # 6.预测
        sigmas[date] = result
    # ret = pd.concat(result_list, axis=0, ignore_index=False)
    return sigmas

"""
辅助函数
"""
def ewma_beta(beta_series: pd.Series, lam: float = 0.94) -> float:
    """
    对一段历史系数做指数加权平均（EWMA）。

    参数
    ----
    beta_series : pd.Series
        历史系数序列，建议按时间从旧到新排列。
    lam : float, default 0.94
        指数衰减系数，范围通常在 (0, 1]。
        - 越接近 1：越平滑，越接近简单均值
        - 越小：越重视最近几期

    返回
    ----
    float
        EWMA 加权后的系数值
    """
    s = pd.Series(beta_series).dropna()

    if len(s) == 0:
        return np.nan

    if not (0 < lam <= 1):
        raise ValueError(f"lam must be in (0, 1], got {lam}")

    # 假设 s 按时间从旧到新排列
    # 越新的数据权重越大
    n = len(s)
    weights = lam ** np.arange(n - 1, -1, -1)

    return float(np.dot(s.values, weights) / weights.sum())