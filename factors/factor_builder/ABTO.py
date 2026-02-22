"""
异常换手率ABTO -- 最近一个月日均换手率/最近12个月日均换手率
"""

import pandas as pd
import numpy as np
from tools import month_tool
from data_api import get_monthly_hfq, get_daily_hfq


def _compute_ABTO(codes: pd.Series, date: str):
    """
    异常换手率ABTO -- 最近一个月日均换手率/最近12个月日均换手率
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'ABTO'])
    """
    # 去重 并 转换成 DataFrame
    codes = codes.drop_duplicates(keep='first')
    codes = codes.to_frame('股票代码')

    # 获取前12月均换手率
    m_12 = month_tool.prev_month(date, 12)
    turnover_m = get_monthly_hfq(m_12, date,
                               attr=['日期', '股票代码', '开盘', '收盘', '换手率'])['换手率']
    turnover_m = turnover_m.groupby(level='code').mean()
    turnover_m = turnover_m.reset_index().rename(columns={'code': '股票代码', '换手率': 'TO'})

    # 获取日均换手率
    m_1 = month_tool.prev_month(date, 1)+'01'
    date = date + '01'
    turnover_d = get_daily_hfq(['换手率(自由流通股)'])
    turnover_d = turnover_d[(turnover_d.index.get_level_values('date') >= m_1) & (turnover_d.index.get_level_values('date') <= date)]
    turnover_d = turnover_d.groupby(level='code').mean()
    turnover_d = turnover_d.reset_index().rename(columns={'code': '股票代码', '换手率(自由流通股)': 'TO_d'})

    # 合并并计算
    datas = codes.merge(turnover_m, on='股票代码', how='left')
    datas = datas.merge(turnover_d, on='股票代码', how='left')

    datas['TO_d'] = datas['TO_d'].where(datas['TO_d'] > 0, other=np.nan)
    datas['TO'] = datas['TO'].where(datas['TO'] > 0, other=np.nan)
    datas['ABTO'] = datas['TO_d'].div(datas['TO']).replace([float('inf'), -float('inf')], None).where(
        pd.notnull(datas['TO_d']) & pd.notnull(datas['TO']) & (datas['TO'] != 0))
    datas['ABTO'] = datas['ABTO'].where(datas['ABTO'] > 0, other=np.nan)
    return datas[['股票代码', 'ABTO']]


from tools import datapath
if __name__ == '__main__':
    codes = pd.read_csv(datapath.stock_path, dtype=str)['股票代码']
    datas = _compute_ABTO(codes, '202602')
    print(len(datas[datas['ABTO'].isna()]))
    print(datas)
