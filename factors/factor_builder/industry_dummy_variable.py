"""
计算行业哑变量（固定）
"""
import pandas as pd
from data_api import get_stock_list
import factors

def _get_industry_dummies() -> pd.DataFrame:
    """
    获取行业哑变量
    :return: DataFrame(col=['股票代码', 'ind_xx', ...])
    """
    # 1.配置列名和获取数据
    industry_col = "所属行业"
    code_col = "股票代码"
    prefix = "ind"
    datas = get_stock_list()[['股票代码','所属行业']]

    # 2.检查必要的列是否存在
    required_cols = [code_col, industry_col]
    for col in required_cols:
        if col not in datas.columns:
            raise ValueError(f"DataFrame必须包含列: '{col}'")

    # 3.复制原始数据，避免修改原数据
    result = datas.copy()

    # 4.使用pandas的get_dummies（推荐）
    dummies = pd.get_dummies(
        result[industry_col],
        prefix=prefix,
        drop_first=False,
        dtype=int
    )

    # 5.将哑变量合并到原数据
    result = pd.concat([result['股票代码'], dummies], axis=1)

    result = result.rename(columns={'股票代码': 'code'})
    return result

def build_industry_dummies():
    data = _get_industry_dummies()
    data.to_csv(factors.fpath('industry'), index=False)

def build_industry_dummies_rm():

    data = _get_industry_dummies().copy()

    if 'code' not in data.columns:
        raise ValueError("_get_industry_dummies() 返回结果中必须包含 'code' 列")

    # 识别行业哑变量列
    ind_cols = [c for c in data.columns if c.startswith('ind_')]
    if not ind_cols:
        raise ValueError("_get_industry_dummies() 返回结果中未找到行业哑变量列（需以 'ind_' 开头）")

    # 缺失值填 0
    data[ind_cols] = data[ind_cols].fillna(0)

    # 强制转为 0/1 整型
    for col in ind_cols:
        data[col] = (data[col] != 0).astype(int)

    # 检查每只股票是否恰好属于一个行业
    ind_sum = data[ind_cols].sum(axis=1)
    bad_mask = ind_sum != 1
    if bad_mask.any():
        bad_rows = data.loc[bad_mask, ['code'] + ind_cols]
        raise ValueError(
            "行业哑变量存在异常：每只股票应当恰好属于一个行业，但发现有股票行业哑变量和不等于 1。\n"
            f"异常样本前10行：\n{bad_rows.head(10).to_string(index=False)}"
        )

    # 选择一个基准行业删除，以消除与截距项的完全共线性
    # 这里删除样本数最多的行业，使基准行业更稳定
    base_col = data[ind_cols].sum(axis=0).sort_values(ascending=False).index[0]

    out = data.drop(columns=[base_col])

    # 保存
    out.to_csv(factors.fpath('industry'), index=False)

    print(f"[industry] 已保存去共线性的行业哑变量文件：{factors.fpath('industry')}")
    print(f"[industry] 基准行业（已删除）: {base_col}")
    print(f"[industry] 保留行业列数: {len(ind_cols) - 1}")