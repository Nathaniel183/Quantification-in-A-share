"""
获取股票列表
"""
import pandas as pd
from tools import datapath

def get_stock_list(codes:pd.Series=None):
    """
    获取指定股票的基本信息列表
    :param codes: 指定股票列表
    :return:
    """
    if codes is None:
        datas = pd.read_csv(datapath.stock_path)
        datas['股票代码'] = datas['股票代码'].astype(str).str.zfill(6)

    else:
        datas = pd.read_csv(datapath.stock_path)
        datas['股票代码'] = datas['股票代码'].astype(str).str.zfill(6)
        datas = datas.loc[datas['股票代码'].isin(codes)]
    return datas

def get_index_list():
    datas = pd.read_csv(datapath.index_path)
    datas['symbol_num'] = datas['symbol_num'].astype(str).str.zfill(6)
    return datas

def get_st_list():
    """
    获取st(但未退市)股票列表
    :return: Series('股票代码')
    """
    datas = pd.read_csv(datapath.stock_path)
    datas['股票代码'] = datas['股票代码'].astype(str).str.zfill(6)
    datas = datas[datas['股票名称'].str.contains('st', case=False, na=False)]
    return datas['股票代码']

def get_t_list():
    """
    获取退市股票列表
    :return: Series('股票代码')
    """
    datas = pd.read_csv(datapath.st_path)
    datas['股票代码'] = datas['symbol'].astype(str).str.zfill(6)
    return datas['股票代码']


if __name__ == '__main__':
    data = get_stock_list().loc[0:1, '股票代码']
    df = get_stock_list(data)
    print(df)

    df = get_stock_list(data)[['股票代码', '股票名称', '地域', '所属行业']].rename(columns={'股票代码': 'code'})
    print(df)
