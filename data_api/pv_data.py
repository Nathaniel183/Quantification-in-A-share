import os
import pandas as pd
from tools import datapath

def get_monthly_hfq_change(start_time:str='20000101', end_time:str='20991231'):
    """
    获取所有股票涨跌幅 月度后复权
    :param start_time:
    :param end_time:
    :return: DataFrame(index=('date', 'code'), col=['change'])
    """
    datas = get_monthly_hfq(start_time=start_time, end_time=end_time, attr=['日期','股票代码','开盘','收盘','涨跌幅'])
    datas.rename(columns={'涨跌幅': 'change'}, inplace=True)
    return datas['change']


def get_monthly_hfq(start_time:str='19900101', end_time:str='20991231',attr:list = ['日期','股票代码','开盘','收盘']):
    """
    获取所有股票数据 月线后复权
    :param start_time:
    :param end_time:
    :param attr:
    :return:
    """

    stocks = pd.read_csv(datapath.stock_path, dtype={'股票代码':str})
    datas = pd.DataFrame({
        '日期': pd.Series(dtype='str'),
        '股票代码': pd.Series(dtype='str'),
        '开盘': pd.Series(dtype='float'),
        '收盘': pd.Series(dtype='float')
    })
    for index, row in stocks.iterrows():
        code:str = row['股票代码']

        # 去除科创版
        if code.startswith('688') or code.startswith('3') or code.startswith('9'):
            continue
        if True: #code.startswith('0'):
            # print(code)
            file_path = datapath.pv_monthly_hfq_path(code)
            if not os.path.exists(file_path):
                continue
            data = pd.read_csv(file_path, dtype={'股票代码':str}).loc[:,attr]
            data['日期'] = data['日期'].str.replace('-','')
            data = data.loc[(data['日期'] >= start_time) & (data['日期'] <= end_time)]
            data['日期'] = data.loc[:,'日期'].str.slice(0,6)

            datas = pd.concat([datas, data], ignore_index=True)

    datas.rename(columns={'日期':'date', '股票代码':'code','开盘':'open','收盘':'close'},inplace=True)
    datas.set_index(['date','code'], inplace=True)
    # print(datas['date'])
    return datas


def get_monthly_qfq(start_time:str='19900101', end_time:str='20991231',attr:list = ['日期','股票代码','开盘','收盘']):
    """
    获取所有股票数据 月线前复权
    :param start_time:
    :param end_time:
    :param attr:
    :return:
    """

    stocks = pd.read_csv(datapath.stock_path, dtype={'股票代码':str})
    datas = pd.DataFrame({
        '日期': pd.Series(dtype='str'),
        '股票代码': pd.Series(dtype='str'),
        '开盘': pd.Series(dtype='float'),
        '收盘': pd.Series(dtype='float')
    })
    for index, row in stocks.iterrows():
        code:str = row['股票代码']

        # 去除科创版
        if code.startswith('688') or code.startswith('3') or code.startswith('9'):
            continue
        if True: #code.startswith('0'):
            # print(code)
            file_path = datapath.pv_monthly_qfq_path(code)
            if not os.path.exists(file_path):
                continue
            data = pd.read_csv(file_path, dtype={'股票代码':str}).loc[:,attr]
            data['日期'] = data['日期'].str.replace('-','')
            data = data.loc[(data['日期'] >= start_time) & (data['日期'] <= end_time)]
            data['日期'] = data.loc[:,'日期'].str.slice(0,6)

            datas = pd.concat([datas, data], ignore_index=True)

    datas.rename(columns={'日期':'date', '股票代码':'code','开盘':'open','收盘':'close'},inplace=True)
    datas.set_index(['date','code'], inplace=True)
    # print(datas['date'])
    return datas


def get_monthly(start_time:str='19900101', end_time:str='20991231',attr:list = ['日期','股票代码','开盘','收盘']):
    """
    获取所有股票数据 月线不复权
    :param start_time:
    :param end_time:
    :param attr:
    :return:
    """

    stocks = pd.read_csv(datapath.stock_path, dtype={'股票代码':str})
    datas = pd.DataFrame({
        '日期': pd.Series(dtype='str'),
        '股票代码': pd.Series(dtype='str'),
        '开盘': pd.Series(dtype='float'),
        '收盘': pd.Series(dtype='float')
    })
    for index, row in stocks.iterrows():
        code:str = row['股票代码']

        # 去除科创版
        if code.startswith('688') or code.startswith('3') or code.startswith('9'):
            continue
        if True: #code.startswith('0'):
            # print(code)
            file_path = datapath.pv_monthly_path(code)
            if not os.path.exists(file_path):
                continue
            data = pd.read_csv(file_path, dtype={'股票代码':str}).loc[:,attr]
            data['日期'] = data['日期'].str.replace('-','')
            data = data.loc[(data['日期'] >= start_time) & (data['日期'] <= end_time)]
            data['日期'] = data.loc[:,'日期'].str.slice(0,6)

            datas = pd.concat([datas, data], ignore_index=True)

    datas.rename(columns={'日期':'date', '股票代码':'code','开盘':'open','收盘':'close'},inplace=True)
    datas.set_index(['date','code'], inplace=True)
    # print(datas['date'])
    return datas


def get_monthly_index(codes:pd.Series=pd.Series(['000001'], name='代码'),
                      start_time:str='19900101', end_time:str='20991231'):
    """
    获取指定指数月线数据 默认只获取上证指数
    :param codes:
    :param start_time:
    :param end_time:
    :param attr:
    :return: DataFrame(column=['日期','收盘'])
    """

    datas = pd.DataFrame({
        '日期': pd.Series(dtype='str'),
        '代码': pd.Series(dtype='str'),
        '开盘': pd.Series(dtype='float'),
        '收盘': pd.Series(dtype='float')
    })
    for code in codes:
        file_path = datapath.pv_index_path(code)
        if not os.path.exists(file_path):
            continue
        data = pd.read_csv(file_path, dtype={'代码': str}).loc[:,  ['日期','代码','开盘','收盘']]
        data['日期'] = data['日期'].str.replace('-', '')
        data = data.loc[(data['日期'] >= start_time) & (data['日期'] <= end_time)]
        data['日期'] = data.loc[:, '日期'].str.slice(0, 6)

        datas = pd.concat([datas, data], ignore_index=True)

    return datas


def update_daily_hfq(start_time:str='19900101', end_time:str='20991231'):
    stocks = pd.read_csv(datapath.stock_path, dtype={'股票代码': str})
    datas = pd.DataFrame({
        '交易日期': pd.Series(dtype='str'),
        '股票代码': pd.Series(dtype='str'),
    })
    for index, row in stocks.iterrows():
        code: str = row['TS代码']

        # 去除科创版
        if code.startswith('68') or code.startswith('3') or code.startswith('9'):
            continue

        file_path = datapath.pv_daily_hfq_path(code)
        if not os.path.exists(file_path):
            continue

        print(code)
        data = pd.read_csv(file_path, dtype={'股票代码': str, '交易日期': str})
        data['交易日期'] = data['交易日期'].str.replace('-', '')
        data['股票代码'] = data['股票代码'].str.split('.').str[0]
        data = data.loc[(data['交易日期'] >= start_time) & (data['交易日期'] <= end_time)]

        datas = pd.concat([datas, data], ignore_index=True)

    datas.rename(columns={'交易日期': 'date', '股票代码': 'code'}, inplace=True)
    datas.set_index(['date', 'code'], inplace=True)
    datas.to_csv(datapath.con_daily_hfq_path)
    print(datas)


def get_daily_hfq(attr: list = ['开盘价', '收盘价']):
    """

    :param attr: 需要的数据list
        股票代码	交易日期	开盘价	最高价	最低价	收盘价	昨收价
        涨跌额	涨跌幅	成交量(手)	成交额(千元)	换手率	换手率(自由流通股)	量比
        市盈率	市盈率TTM	市净率	市销率	市销率TTM	股息率	股息率TTM
        总股本(万股)	流通股本(万股)	自由流通股本(万股)	总市值(万元)	流通市值(万元)
    :return: DataFrame(index=(date,code), col=attr)
    """
    fix_attr = ['date', 'code']
    attr = fix_attr + attr

    # 使用函数属性作为缓存
    if not hasattr(get_daily_hfq, '_cache'):
        get_daily_hfq._cache = pd.read_csv(datapath.con_daily_hfq_path,
                                           dtype={'date': str, 'code': str})

    datas = get_daily_hfq._cache.loc[:, attr]
    datas[['date', 'code']] = datas[['date', 'code']].astype(str)
    datas.set_index(['date', 'code'], inplace=True)
    return datas



if __name__ == "__main__":
    # datas = get_daily_hfq()
    # print(datas)
    # datas = get_daily_hfq(attr=['换手率'])
    # print(datas)
    # datas = get_daily_hfq(attr=['市盈率'])
    # print(datas)
    # datas = get_daily_hfq(attr=['市销率'])
    # print(datas)

    datas = get_monthly()
    print(datas)



