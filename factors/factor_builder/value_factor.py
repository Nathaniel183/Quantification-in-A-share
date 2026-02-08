"""
价值因子 —— 淘宝数据计算
"""

import pandas as pd
import numpy as np
from tools import quarter_tool, month_tool, safe_div
from data_api import get_financial_data, get_monthly_hfq

def _compute_value(codes:pd.Series, date:str):
    """
    价值因子 -- 每股净资产/价格
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'value'])
    """
    # 去重
    codes = codes.drop_duplicates(keep='first')

    # 获取期数
    q = quarter_tool.current_quarter(date)
    q_1 = quarter_tool.prev_quarter(q)
    q_2 = quarter_tool.prev_quarter(q_1)

    # 尝试获取当期 财务 数据
    datas = _compute(codes, date, q)

    # 第一次找出未获取到数据的代码
    remain_codes = datas.loc[datas['每股净资产']==0,'股票代码']

    # 尝试获取前期 财务 数据
    datas_1 = _compute(remain_codes, date, q_1)

    # 合并前后数据
    map = datas_1.set_index('股票代码')['每股净资产'].to_dict()
    datas.loc[datas['每股净资产']==0, '每股净资产'] = datas.loc[datas['每股净资产']==0, '股票代码'].map(map)

    # 第二次找出未获取到数据的代码
    remain_codes = datas.loc[datas['每股净资产'] == 0, '股票代码']

    # 尝试获取前前期 财务 数据
    datas_2 = _compute(remain_codes, date, q_2)

    # 合并前后数据
    map = datas_2.set_index('股票代码')['每股净资产'].to_dict()
    datas.loc[datas['每股净资产'] == 0, '每股净资产'] = datas.loc[datas['每股净资产'] == 0, '股票代码'].map(map)

    # 获取上一月价格
    m = month_tool.prev_month(date,1)
    price = get_monthly_hfq(m, date).xs(m, level='date')['close']
    price = price.reset_index().rename(columns={'code':'股票代码'})

    # 合并
    datas = datas.merge(price, on='股票代码', how='left')
    datas['value'] = safe_div(datas['每股净资产'], datas['close'], None)
    datas['value'] = datas['value'].where(datas['value'] > 0, other=np.nan)
    print(datas)

    return datas[['股票代码', 'value']]


def _compute(codes:pd.Series, date:str, q:str):

    # 转换成 DataFrame
    codes = codes.to_frame('股票代码')

    # 获取财务数据
    ret = get_financial_data(date, q)

    # 提取所需数据
    datas = codes.merge(ret[['股票代码',
                             '每股净资产'
                             ]], on='股票代码', how='left').fillna(0)

    return datas[['股票代码', '每股净资产']]



if __name__ == '__main__':
    codes = pd.read_csv("../../dataset/股票列表.csv", dtype=str)['股票代码']
    ret = _compute_value(codes, '202001')
    print(len(ret[ret['value'].isna()]))
    print(ret)
