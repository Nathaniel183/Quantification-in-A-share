"""
双重排序
"""
import pandas as pd
import data_api

def double_sort(data1:pd.DataFrame, data2:pd.DataFrame,
                name1:str, name2:str,
                div1:int=5, div2:int=5,
                ascend1:bool=True,ascend2:bool=True):
    """
    双重排序 -- 注意，不论 ascend 如何设置，分组序号从小到大都是数据从低到高，但组内排序会改变
    :param data1: 第一个数据DataFrame(['股票代码','name1'])
    :param data2: 第二个数据DataFrame(['股票代码','name2'])
    :param name1: 属性名1
    :param name2: 属性名2
    :param div1: 属性1分组数
    :param div2: 属性2分组数
    :param ascend1: 属性1升序
    :param ascend2: 属性2升序
    :return: DataFrame(['股票代码','name1','name2','group1','group2'])
    """
    ret = pd.merge(left=data1, right=data2, on='股票代码', how='inner')

    # 创建结果DataFrame的副本
    result = ret[['股票代码', name1, name2]].copy()

    # 对第一个属性进行独立排序和分组
    result_sorted1 = result.sort_values(by=name1, ascending=ascend1)
    result_sorted1['group1'] = pd.qcut(result_sorted1[name1].rank(method='first'),
                                       q=div1, labels=range(1, div1 + 1))

    # 对第二个属性进行独立排序和分组
    result_sorted2 = result.sort_values(by=name2, ascending=ascend2)
    result_sorted2['group2'] = pd.qcut(result_sorted2[name2].rank(method='first'),
                                       q=div2, labels=range(1, div2 + 1))

    # 合并两个分组结果
    result = result.merge(result_sorted1[['股票代码', 'group1']], on='股票代码', how='left')
    result = result.merge(result_sorted2[['股票代码', 'group2']], on='股票代码', how='left')

    result = result.sort_values(by=['group1','group2', name1, name2], ascending=[ascend1, ascend2, ascend1, ascend2])
    result = result.reset_index(drop=True)
    return result



if __name__ == '__main__':
    pass


