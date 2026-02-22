"""
流动性因子ILL -- 非流动性指标，(日绝对收益绝对值/日成交额)的月平均值
"""

import pandas as pd
import numpy as np
from tools import month_tool
from data_api import get_daily_hfq


def _compute_ILL(codes: pd.Series, date: str):
    """
    流动性因子ILL -- 非流动性指标，(日绝对收益绝对值/日成交额)的月平均值
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'ILL'])
    """
    # 去重 并 转换成 DataFrame
    codes = codes.drop_duplicates(keep='first')
    codes = codes.to_frame('股票代码')

    # 获取日收益率标准差
    m_1 = month_tool.prev_month(date, 1)+'01'
    date = date + '01'
    ret = get_daily_hfq(['涨跌幅','成交额(千元)'])
    ret = ret[(ret.index.get_level_values('date') >= m_1) & (ret.index.get_level_values('date') <= date)]

    ret['ILL'] = (ret['涨跌幅'].abs() / ret['成交额(千元)']).where(
        (ret['成交额(千元)'] != 0) & ret[['涨跌幅', '成交额(千元)']].notna().all(axis=1))

    ILL = ret.groupby('code')['ILL'].mean()
    ILL = ILL.reset_index().rename(columns={'code': '股票代码'})

    # 合并
    datas = codes.merge(ILL, on='股票代码', how='left')

    datas['ILL'] = datas['ILL'].where(datas['ILL'] >= 0, other=np.nan)
    return datas[['股票代码', 'ILL']]


from tools import datapath
if __name__ == '__main__':
    codes = pd.read_csv(datapath.stock_path, dtype=str)['股票代码']
    datas = _compute_ILL(codes, '202602')
    print(len(datas[datas['ILL'].isna()]))
    print(datas)