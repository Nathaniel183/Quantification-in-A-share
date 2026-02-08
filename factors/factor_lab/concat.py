import pandas as pd
from factors import Factor

def concat(vals:list[Factor]):
    """
    变量合并
    :param vals: 需要合并的变量列表
    :return: 合并后的DataFrame
    """
    # 1.提取code和date
    code_index = pd.DataFrame(columns=[])
    date_index = pd.DataFrame(columns=[])
    for val in vals:
        if val.get_dshape()=='NT_K':
            code_index = val.get_data().index.get_level_values('code').unique().tolist()
            date_index = val.get_data().index.get_level_values('date').unique().tolist()
        elif val.get_dshape()=='N_K':
            code_index = val.get_data().index.get_level_values('code').unique().tolist()
        elif val.get_dshape()=='T_K':
            date_index = val.get_data().index.get_level_values('date').unique().tolist()
        if len(code_index)>0 and len(date_index)>0:
            break
    multi_index = pd.MultiIndex.from_product([code_index, date_index], names=['code', 'date'])
    ret = pd.DataFrame(index=multi_index)

    # 2.合并
    for val in vals:
        df = val.get_data()
        if val.get_dshape()=='NT_K':
            ret = ret.join(df, how='inner')
        elif val.get_dshape()=='N_K':
            df = df.xs('all', level='date')
            ret = ret.join(df, on='code', how='inner')
        elif val.get_dshape()=='T_K':
            df = df.xs('all', level='code')
            ret = ret.join(df, on='date', how='inner')
    return ret
