import pandas as pd
import numpy as np

def get_sharp(stg_dir:str=''):
    """
    计算策略夏普比率，无风险利率设为0
    :param stg_dir: 策略运行保存目录
    :return: 夏普比率，float
    """
    df = pd.read_csv(f"./record/{stg_dir}/income_record.csv")

    df["return"] = df["income"].pct_change()

    r = df["return"].dropna()

    sharpe = r.mean() / r.std() * np.sqrt(12)

    print(f"{sharpe:.2f}")

def main():
    # get_sharp("pred_T_FS_20260303_01_23_36_1772472216")
    get_sharp("pred_T_FS_ILL_ROE_20260223_01_49_29_1771782569")


if __name__ == "__main__":
    main()


"""
参考标准
| Sharpe  | 评价  |
| ------- | --- |
| <0.5    | 很差  |
| 0.5 – 1 | 一般  |
| 1 – 1.5 | 可以  |
| 1.5 – 2 | 较好  |
| 2 – 3   | 优秀  |
| >3      | 非常强 |

典型策略
| 策略类型  | Sharpe  |
| ----- | ------- |
| 基本面多头 | 0.6–1.2 |
| 多因子选股 | 1–2     |
| 中性对冲  | 2–4     |
| 高频    | 3–6     |

月度多头
Sharpe > 1.2  不错
Sharpe > 1.5  比较优秀
"""