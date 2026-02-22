"""
盈利因子ROE -- 季度
"""
import pandas as pd
from tools import quarter_tool
from data_api import get_financial_data_v2

def _compute_ROE(codes:pd.Series, date:str):
    """
    盈利因子ROE -- 净利润/净资产
    :param codes: 股票代码
    :param date: 当前日期
    :return: DataFrame(['股票代码', 'ROE'])
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
    remain_codes = datas.loc[datas['ROE'].isna(),'股票代码']

    # 尝试获取前期 财务 数据
    datas_1 = _compute(remain_codes, date, q_1)

    # 合并前后数据
    map = datas_1.set_index('股票代码')['ROE'].to_dict()
    datas.loc[datas['ROE'].isna(), 'ROE'] = datas.loc[datas['ROE'].isna(), '股票代码'].map(map)

    # 第二次找出未获取到数据的代码
    remain_codes = datas.loc[datas['ROE'].isna(), '股票代码']

    # 尝试获取前前期 财务 数据
    datas_2 = _compute(remain_codes, date, q_2)

    # 合并前后数据
    map = datas_2.set_index('股票代码')['ROE'].to_dict()
    datas.loc[datas['ROE'].isna(), 'ROE'] = datas.loc[datas['ROE'].isna(), '股票代码'].map(map)

    print(datas)
    return datas[['股票代码', 'ROE']]


def _compute(codes:pd.Series, date:str, q:str):

    # 转换成 DataFrame
    codes = codes.to_frame('股票代码')

    # 获取财务数据
    ret = get_financial_data_v2(date, q)

    # 提取所需数据
    datas = codes.merge(ret[['股票代码',
                             '财务指标数据_加权平均净资产收益率',
                             ]], on='股票代码', how='left')

    datas['ROE'] = datas['财务指标数据_加权平均净资产收益率']

    return datas[['股票代码', 'ROE']]


from tools import datapath
if __name__ == '__main__':
    codes = pd.read_csv(datapath.stock_path, dtype=str)['股票代码']
    ret = _compute_ROE(codes, '202001')
    print(len(ret[ret['ROE'].isna()]))
    print(ret)
