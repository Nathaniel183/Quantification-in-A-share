import os
import numpy as np
import pandas as pd
import factors
from factors import factor_lab

def ic_report(
    vals:list[factors.Factor],
    method: str = "spearman",        # "spearman" or "pearson"
    ic_abs_threshold: float = 0.02,  # 2%
    min_obs_per_date: int = 5,       # 每个date最少股票数，否则该date的IC记为NaN
):
    """
    vals: DataFrame, index=(code,date) MultiIndex, columns=[因子名...]

    返回：
      summary_df: 每因子一行的汇总
      ic_ts_df:   index=date, columns=因子名 的IC序列
    """
    vals = factor_lab.concat(vals)
    change = factors.Change().get_data()
    out_dir: str = "./ic_result"

    if not isinstance(vals, pd.DataFrame):
        raise TypeError("vals 必须是 pandas DataFrame")

    # change 统一成 Series
    if isinstance(change, pd.DataFrame):
        if change.shape[1] != 1:
            raise ValueError("change 如果是DataFrame，必须只有一列")
        change = change.iloc[:, 0]
    if not isinstance(change, pd.Series):
        raise TypeError("change 必须是 pandas Series 或 单列DataFrame")

    if not isinstance(vals.index, pd.MultiIndex) or not isinstance(change.index, pd.MultiIndex):
        raise ValueError("vals 和 change 的 index 都必须是 MultiIndex: (code, date)")

    method = method.lower().strip()
    if method not in {"spearman", "pearson"}:
        raise ValueError("method 只能是 'spearman' 或 'pearson'")

    # 取交集并拼接
    change_name = change.name or "change"
    common = vals.join(change.rename(change_name), how="inner")

    # 找到date所在的层（优先按名字，其次默认第二层）
    idx_names = list(common.index.names)
    if "date" in idx_names:
        date_level = "date"
    else:
        date_level = 1  # (code, date) 通常 date 是第二层

    factor_cols = list(vals.columns)

    def _ic_one_group(g: pd.DataFrame) -> pd.Series:
        # g 的index是 (code,date) 的子集，且同一date
        y = g[change_name]
        X = g[factor_cols]

        # 对齐有效样本：每个因子自己dropna，同时y也要非空
        out = {}
        for c in factor_cols:
            tmp = pd.concat([X[c], y], axis=1).dropna()
            if tmp.shape[0] < min_obs_per_date:
                out[c] = np.nan
                continue

            x1 = tmp.iloc[:, 0]
            y1 = tmp.iloc[:, 1]

            if method == "spearman":
                # Spearman = rank 后做 Pearson
                x1 = x1.rank(method="average")
                y1 = y1.rank(method="average")

            # 防止常数序列导致nan
            if x1.nunique(dropna=True) <= 1 or y1.nunique(dropna=True) <= 1:
                out[c] = np.nan
            else:
                out[c] = x1.corr(y1, method="pearson")
        return pd.Series(out)

    # 按date分组计算IC序列
    ic_ts_df = common.groupby(level=date_level, sort=True).apply(_ic_one_group)
    ic_ts_df.index.name = "date"
    ic_ts_df = ic_ts_df.sort_index()

    # 汇总统计
    summary_rows = []
    for c in factor_cols:
        s = ic_ts_df[c].dropna()
        n = int(s.shape[0])
        ic_mean = float(s.mean()) if n > 0 else np.nan
        ic_std = float(s.std(ddof=1)) if n > 1 else np.nan
        ir = (ic_mean / ic_std) if (n > 1 and ic_std and np.isfinite(ic_std) and ic_std != 0) else np.nan
        abs_gt_ratio = float((s.abs() > ic_abs_threshold).mean()) if n > 0 else np.nan

        # t = mean / (std/sqrt(n))
        t_value = (ic_mean / (ic_std / np.sqrt(n))) if (n > 1 and ic_std and np.isfinite(ic_std) and ic_std != 0) else np.nan

        summary_rows.append({
            "factor": c,
            "n_dates": n,
            "IC_mean": ic_mean,
            "IC_std": ic_std,
            "IR(IC_mean/IC_std)": ir,
            f"abs(IC)>{ic_abs_threshold:.2%}_ratio": abs_gt_ratio,
            "IC_mean_t_value": t_value,
        })

    summary_df = pd.DataFrame(summary_rows).set_index("factor")
    # 更直观：按IR或|t|排序
    summary_df = summary_df.sort_values(by="IR(IC_mean/IC_std)", ascending=False)

    # 打印（你也可以自己改成logger）
    print("\n========== Factor IC Report ==========")
    print(f"IC method: {method} | abs threshold: {ic_abs_threshold:.2%} | min_obs/date: {min_obs_per_date}")
    print(f"Intersection sample size: {common.shape[0]} rows, dates: {ic_ts_df.shape[0]}")
    print("\n--- Summary ---")
    with pd.option_context("display.max_rows", 200, "display.width", 160):
        print(summary_df.round(6))

    # 组织输出csv（可选）
    if out_dir is not None:
        os.makedirs(out_dir, exist_ok=True)
        summary_path = os.path.join(out_dir, f"ic_summary.csv")
        ic_path = os.path.join(out_dir, f"ic_timeseries.csv")
        ic_fig_path = os.path.join(out_dir, f"ic_timeseries.jpg")

        summary_df.to_csv(summary_path, encoding="utf-8-sig")
        ic_ts_df.to_csv(ic_path, encoding="utf-8-sig")

        print("\n--- CSV saved ---")
        print(summary_path)
        print(ic_path)

        plot_ic(ic_ts_df, ic_fig_path)

    return summary_df, ic_ts_df


import matplotlib.pyplot as plt
def plot_ic(df, save_path, figsize=(12, 6)):
    """
    绘制DataFrame所有列的折线图并保存

    Parameters:
    -----------
    df : pandas.DataFrame
        输入数据，index名为'date'，每列将被绘制为一条折线
    save_path : str
        图像保存路径（需包含文件名和扩展名，如：'./output/plot.png'）
    figsize : tuple, optional
        图像尺寸，默认(12, 6)
    """
    # 检查输入
    if df.index.name != 'date':
        raise ValueError("DataFrame索引必须命名为'date'")

    if df.empty:
        raise ValueError("DataFrame为空")

    # 创建图形
    plt.figure(figsize=figsize)

    # 为每一列绘制折线
    for column in df.columns:
        plt.plot(df.index, df[column], label=column, linewidth=2)

    # 设置横轴标签和标题
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Value', fontsize=12)
    plt.title('Multi-line Plot', fontsize=14)

    # 添加图例
    plt.legend(fontsize=10)

    # 自动调整横轴标签显示密度（防止重叠）
    plt.gcf().autofmt_xdate()

    # 自动调整布局
    plt.tight_layout()

    # 确保保存目录存在
    save_dir = os.path.dirname(save_path)
    if save_dir and not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 保存图像
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    vals = [
        # factors.Market(),
        # factors.Size(),
        # factors.Value(),
        factors.Turnover(),
        # factors.Momentum(12,1),
        factors.FScore(),
        # factors.MScore(),
        # factors.Industry(),
        factors.EP(),
        factors.BM(),
        factors.ROE(),
        factors.VOL(),
        factors.MAX(),
        factors.TO(),
        factors.ABTO(),
        factors.ILL(),
        factors.STR(),
    ]

    summary_df, ic_ts_df = ic_report(vals)
    print(summary_df)
    print(ic_ts_df)