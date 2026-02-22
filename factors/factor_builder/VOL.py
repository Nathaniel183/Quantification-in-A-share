"""
波动因子VOL -- 波动率，最近1个月日收益率的标准差
"""

import pandas as pd
import numpy as np
from tools import month_tool
from data_api import get_daily_hfq


def _compute_VOL(codes: pd.Series, date: str):
    """
    波动因子VOL -- 波动率，最近1个月日收益率的标准差
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'VOL'])
    """
    # 去重 并 转换成 DataFrame
    codes = codes.drop_duplicates(keep='first')
    codes = codes.to_frame('股票代码')


    # 获取日收益率标准差
    m_1 = month_tool.prev_month(date, 1)+'01'
    date = date + '01'
    change = get_daily_hfq(['涨跌幅'])
    change = change[(change.index.get_level_values('date') >= m_1) & (change.index.get_level_values('date') <= date)]
    change = change.groupby(level='code').std()
    change = change.reset_index().rename(columns={'code': '股票代码', '涨跌幅': 'VOL'})

    # 合并
    datas = codes.merge(change, on='股票代码', how='left')

    datas['VOL'] = datas['VOL'].where(datas['VOL'] >= 0, other=np.nan)
    return datas[['股票代码', 'VOL']]


from tools import datapath
if __name__ == '__main__':
    codes = pd.read_csv(datapath.stock_path, dtype=str)['股票代码']
    datas = _compute_VOL(codes, '202602')
    print(len(datas[datas['VOL'].isna()]))
    print(datas)
