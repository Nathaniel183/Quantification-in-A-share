import pandas as pd
from tools.datapath import data_path
import os

def get_nsq_m(start_time:str='19900101', end_time:str='20991231'):
    """
    获取纳斯达克指数月线数据
    :param start_time:
    :param end_time:
    :param attr:
    :return: 
    """

    datas = pd.DataFrame({
        'date': pd.Series(dtype='str'),
        'open': pd.Series(dtype='float'),
        'close': pd.Series(dtype='float')
    })

    file_path = data_path + 'ndq_m.csv'
    if not os.path.exists(file_path):
        return None
    data = pd.read_csv(file_path).loc[:,  ['date','open','close']]
    data['date'] = data['date'].str.replace('-', '')
    data = data.loc[(data['date'] >= start_time) & (data['date'] <= end_time)]
    data['date'] = data.loc[:, 'date'].str.slice(0, 6)

    datas = pd.concat([datas, data], ignore_index=True)
    datas['code'] = 'nsq'  # 添加date列，所有行赋值为'all'
    datas = datas.set_index(['date', 'code'])  # 将date设为索引，保持原有索引
    return datas


def get_nsq_d(start_time:str='19900101', end_time:str='20991231'):
    """
    获取纳斯达克指数月线数据
    :param start_time:
    :param end_time:
    :param attr:
    :return:
    """

    datas = pd.DataFrame({
        'date': pd.Series(dtype='str'),
        'open': pd.Series(dtype='float'),
        'close': pd.Series(dtype='float')
    })

    file_path = data_path + 'ndq_d.csv'
    if not os.path.exists(file_path):
        return None
    data = pd.read_csv(file_path).loc[:,  ['date','open','close']]
    data['date'] = data['date'].str.replace('-', '')
    data = data.loc[(data['date'] >= start_time) & (data['date'] <= end_time)]

    datas = pd.concat([datas, data], ignore_index=True)
    datas['code'] = 'nsq'  # 添加date列，所有行赋值为'all'
    datas = datas.set_index(['date', 'code'])  # 将date设为索引，保持原有索引
    return datas


if __name__ == '__main__':
    datas = get_nsq_d('20161201','20260201')
    print(datas)