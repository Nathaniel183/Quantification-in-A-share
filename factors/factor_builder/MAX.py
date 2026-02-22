"""
波动因子MAX -- 最大平均收益，最近1个月最大的5个日收益率的均值
"""

import pandas as pd
from tools import month_tool
from data_api import get_daily_hfq


def _compute_MAX(codes: pd.Series, date: str):
    """
    波动因子MAX -- 最大平均收益，最近1个月最大的5个日收益率的均值
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'MAX'])
    """
    # 去重 并 转换成 DataFrame
    codes = codes.drop_duplicates(keep='first')
    codes = codes.to_frame('股票代码')


    # 获取日收益率标准差
    m_1 = month_tool.prev_month(date, 1)+'01'
    date = date + '01'
    change = get_daily_hfq(['涨跌幅'])
    change = change[(change.index.get_level_values('date') >= m_1) & (change.index.get_level_values('date') <= date)]
    change = change.groupby(level='code').apply(lambda x: x['涨跌幅'].nlargest(5).mean()).rename('MAX')
    change = change.reset_index().rename(columns={'code': '股票代码'})

    # 合并
    datas = codes.merge(change, on='股票代码', how='left')

    return datas[['股票代码', 'MAX']]


from tools import datapath
if __name__ == '__main__':
    codes = pd.read_csv(datapath.stock_path, dtype=str)['股票代码']
    datas = _compute_MAX(codes, '202602')
    print(len(datas[datas['MAX'].isna()]))
    print(datas)
