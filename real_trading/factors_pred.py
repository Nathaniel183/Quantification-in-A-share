"""
实盘选股计算 -- 预测收益率策略
"""
import pandas as pd
import data_api
import factors

date = '202602'
stg_name='pred_TO_ILL_36'

ret = pd.read_csv(factors.wpath(stg_name), dtype={'code':str, 'date':str}).rename(columns={'code':'股票代码'})
ret = ret.loc[ret['date']==date].sort_values('prediction',ascending=False)

info = data_api.get_stock_list(ret['股票代码'])
ret = ret.merge(info, on='股票代码', how='left').reset_index(drop=True)
ret.to_csv(f'./{date}_{stg_name}.csv', index=False)