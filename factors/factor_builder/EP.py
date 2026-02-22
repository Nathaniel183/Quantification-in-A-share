"""
规模因子EP -- 月末最后一个交易日，1/市盈率TTM
"""

import pandas as pd
import numpy as np
from tools import month_tool
from data_api import get_daily_hfq


def _compute_EP(codes: pd.Series, date: str):
    """
    规模因子EP -- 月末最后一个交易日，1/市盈率TTM
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'EP'])
    """
    # 去重 并 转换成 DataFrame
    codes = codes.drop_duplicates(keep='first')
    codes = codes.to_frame('股票代码')

    # 获取日收益率标准差
    m_1 = month_tool.prev_month(date, 1)+'01'
    date = date + '01'
    ret = get_daily_hfq(['市盈率TTM'])
    ret = ret[(ret.index.get_level_values('date') >= m_1) & (ret.index.get_level_values('date') <= date)]

    last = ret.sort_index(level=0).groupby(level=1, group_keys=False).tail(1)
    last["EP"] = (1 / last["市盈率TTM"]).where(last["市盈率TTM"].gt(0) & np.isfinite(last["市盈率TTM"]), None)

    EP = last.reset_index().rename(columns={'code': '股票代码'})

    # 合并
    datas = codes.merge(EP, on='股票代码', how='left')

    return datas[['股票代码', 'EP']]


from tools import datapath
if __name__ == '__main__':
    codes = pd.read_csv(datapath.stock_path, dtype=str)['股票代码']
    datas = _compute_EP(codes, '202602')
    print(len(datas[datas['EP'].isna()]))
    print(datas)