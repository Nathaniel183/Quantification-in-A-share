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

    return result

def build_industry_dummies():
    data = _get_industry_dummies()
    #print(_get_industry_dummies())
    data.to_csv(factors.fpath('industry'), index=False)
