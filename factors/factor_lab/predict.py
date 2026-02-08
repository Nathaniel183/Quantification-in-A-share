import pandas as pd

def predict(vals:pd.DataFrame,
            params:pd.Series,
            date:str):
    """
    预测各股票收益率（涨幅）
    :param vals: concat得到的因子预测变量值
    :param params: 当前date时，各预测变量的系数，以及截距项const
    :param date: 当前日期
    :return: DataFrame(index=(date,code),col=prediction)，其中date索引统一为当前date
    """
    vals = vals.xs(date, level='date')

    if 'const' in params:
        b = params.drop('const')
        result = (vals * b).sum(axis=1) + params['const']
    else:
        result = (vals * params).sum(axis=1)
    result = pd.DataFrame(result.rename('prediction'))
    result['date'] = date
    result = result.set_index('date', append=True)  # 将date设为索引，保持原有索引
    result = result.reorder_levels(['code', 'date'])
    return result