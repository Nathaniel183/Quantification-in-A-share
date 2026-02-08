"""
动量因子 -- 淘宝数据计算
"""
import pandas as pd
import numpy as np
from data_api import get_monthly_hfq
from tools import month_tool
from tools import safe_div

def _compute_momentum(codes:pd.Series, date:str, n:int=6, skip:int=0):
    """
    获取动量因子 （收益率）
    :param codes: 股票代码
    :param date: 当前日期 （会被转换成上一个月）
    :param n: 过去 n 月
    :param skip: 跳过最近 skip 月
    :return: DataFrame(['股票代码', 'momentum'])
    """
    #print(n,skip)

    # 获取当前月份 和 n月前月份
    m = month_tool.cur_month(date)
    m = month_tool.prev_month(m, 1)
    m_start = month_tool.prev_month(m, n)
    m_end = month_tool.prev_month(m, skip)

    # 获取量价数据 （指定月份范围内）
    datas = get_monthly_hfq(start_time=m_start+'01', end_time=m_end+'99')
    datas = datas.reset_index()
    # print(datas)

    # 转换成 DataFrame
    codes = codes.to_frame('股票代码')

    # 获取起止月收盘数据
    close_start = datas[datas['date'] == m_start][['code','close']].rename(columns={'code':'股票代码','close':'close_start'})
    close_end = datas[datas['date'] == m_end][['code','close']].rename(columns={'code':'股票代码','close':'close_end'})

    # 合并数据
    ret = pd.merge(close_start, close_end, on='股票代码', how='inner')

    # 计算收益率 （动量因子）
    # ret['momentum'] = np.where(ret['close_start']!=0, ret['close_end']/ret['close_start']-1, None)
    ret['momentum'] = safe_div(ret['close_end'], ret['close_start'], None)-1

    # 根据codes筛选
    ret = ret[ret['股票代码'].isin(codes['股票代码'])]

    # print(ret)
    # print(m_start, m_end)

    return ret[['股票代码', 'momentum']]

if __name__ == '__main__':
    pass
    # codes = pd.read_csv("../dataset/股票列表.csv", dtype=str)['股票代码']
    # # print(codes)
    # ret = _compute_momentum(codes, '20251101', n=12, skip=0)
    # print(ret)