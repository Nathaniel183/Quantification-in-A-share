"""
换手率TO -- 最近12个月换手率均值
"""

import pandas as pd
import numpy as np
from tools import month_tool
from data_api import get_monthly_hfq


def _compute_TO(codes: pd.Series, date: str):
    """
    换手率TO -- 最近12个月换手率均值
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'TO'])
    """
    # 去重
    codes = codes.drop_duplicates(keep='first')

    # 转换成 DataFrame
    codes = codes.to_frame('股票代码')

    # 获取前12个月换手率
    m = month_tool.prev_month(date, 12)
    turnover = get_monthly_hfq(m, date,
                               attr=['日期', '股票代码', '开盘', '收盘', '换手率'])['换手率']

    turnover = turnover.groupby(level='code').mean()

    turnover = turnover.reset_index().rename(columns={'code': '股票代码', '换手率': 'TO'})

    # 合并
    datas = codes.merge(turnover, on='股票代码', how='left')
    datas['TO'] = datas['TO'].where(datas['TO'] > 0, other=np.nan)

    return datas[['股票代码', 'TO']]


from tools import datapath
if __name__ == '__main__':
    codes = pd.read_csv(datapath.stock_path, dtype=str)['股票代码']
    datas = _compute_TO(codes, '202602')
    print(datas)