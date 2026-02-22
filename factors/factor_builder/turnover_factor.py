"""
换手率因子 —— 淘宝数据计算
"""

import pandas as pd
import numpy as np
from tools import month_tool
from data_api import get_monthly_hfq

def _compute_turnover(codes:pd.Series, date:str):
    """
    换手率因子 -- 直接获取
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'turnover'])
    """
    # 去重
    codes = codes.drop_duplicates(keep='first')

    # 转换成 DataFrame
    codes = codes.to_frame('股票代码')
    
    # 获取上一月换手率
    m = month_tool.prev_month(date,1)
    turnover = get_monthly_hfq(m, date,
                               attr=['日期','股票代码','开盘','收盘','换手率']).xs(m, level='date')['换手率']
    turnover = turnover.reset_index().rename(columns={'code':'股票代码','换手率':'turnover'})

    # 合并
    datas = codes.merge(turnover, on='股票代码', how='left')
    datas['turnover'] = datas['turnover'].where(datas['turnover'] > 0, other=np.nan)

    return datas[['股票代码', 'turnover']]


# if __name__ == '__main__':
#     codes = pd.read_csv("../../dataset/股票列表.csv", dtype=str)['股票代码']
#     ret = _compute_turnover(codes, '202512')
#     print(len(ret[ret['turnover'].isna()]))
#     print(ret)
