"""
计算股票 F-Score 和 momentum 双重排序
"""
import pandas as pd
import data_api
import factors

date = '202512'

ret = pd.read_csv(factors.wpath('prediction1'), dtype={'code':str, 'date':str}).rename(columns={'code':'股票代码'})
ret = ret.loc[ret['date']==date].sort_values('prediction',ascending=False)

info = data_api.get_stock_list(ret['股票代码'])
ret = ret.merge(info, on='股票代码', how='left').reset_index(drop=True)
ret.to_csv('./202512_因子模型1.csv', index=False)