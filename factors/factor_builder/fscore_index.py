"""
F-Score计算 —— 淘宝数据计算
"""

import pandas as pd
import numpy as np
from tools import quarter_tool
from data_api import get_financial_data

def _compute_fscore(codes:pd.Series, date:str):
    """
    F-Score计算
    :param codes: 股票代码
    :param date: 当前日期
    :param backtrack: 数据不足时，是否回溯前一期
    :param bt_gate: 回溯阈值，当数据不足codes的多少比例时回溯
    :return: DataFrame(['股票代码', 'F-Score'])
    """
    # 去重
    codes = codes.drop_duplicates(keep='first')

    # 获取期数
    q = quarter_tool.current_quarter(date)
    q_1 = quarter_tool.prev_quarter(q)
    q_2 = quarter_tool.prev_quarter(q_1)

    # 尝试获取当期 F-Score 数据
    datas = _compute(codes, date, q)

    # 第一次找出未获取到数据的代码
    remain_codes = datas.loc[datas['F-Score']==0,'股票代码']

    # 尝试获取前期 F-Score 数据
    datas_1 = _compute(remain_codes, date, q_1)

    # 合并前后数据
    map = datas_1.set_index('股票代码')['F-Score'].to_dict()
    datas.loc[datas['F-Score']==0, 'F-Score'] = datas.loc[datas['F-Score']==0, '股票代码'].map(map)

    # 第二次找出未获取到数据的代码
    remain_codes = datas.loc[datas['F-Score'] == 0, '股票代码']

    # 尝试获取前前期 F-Score 数据
    datas_2 = _compute(remain_codes, date, q_2)

    # 合并前后数据
    map = datas_2.set_index('股票代码')['F-Score'].to_dict()
    datas.loc[datas['F-Score'] == 0, 'F-Score'] = datas.loc[datas['F-Score'] == 0, '股票代码'].map(map)

    return datas


def _compute(codes:pd.Series, date:str, q:str):

    # 转换成 DataFrame
    codes = codes.to_frame('股票代码')

    # 获取期数
    q_1 = quarter_tool.prev_quarter(q)
    q_2 = quarter_tool.prev_quarter(q_1)

    # 获取财务数据
    ret = get_financial_data(date, q)
    ret_1 = get_financial_data(date, q_1)
    ret_2 = get_financial_data(date, q_2)

    # 添加后缀
    ret_1 = ret_1.rename(columns={col: f"{col}_1" for col in ret_1.columns if col != '股票代码'})
    ret_2 = ret_2.rename(columns={col: f"{col}_2" for col in ret_2.columns if col != '股票代码'})

    # 合并多期数据
    # 创建填充字典：数值列填0，对象列填空字符串
    fill_dict = {}
    for col in ret.columns:
        if pd.api.types.is_numeric_dtype(ret[col]):
            fill_dict[col] = 0
        else:
            fill_dict[col] = ''
    for col in ret_1.columns:
        if pd.api.types.is_numeric_dtype(ret_1[col]):
            fill_dict[col] = 0
        else:
            fill_dict[col] = ''
    for col in ret_2.columns:
        if pd.api.types.is_numeric_dtype(ret_2[col]):
            fill_dict[col] = 0
        else:
            fill_dict[col] = ''

    ret = ret.merge(ret_1, on='股票代码', how='outer').fillna(fill_dict)
    ret = ret.merge(ret_2, on='股票代码', how='outer').fillna(fill_dict)

    # 提取所需数据
    datas = codes.merge(ret[['股票代码',
                             '归属于母公司所有者的净利润', '资产总计_1', '资产总计',
                             '经营活动产生的现金流量净额',
                             '归属于母公司所有者的净利润_1', '资产总计_2',
                             '非流动负债合计', '非流动负债合计_1',
                             '流动资产合计', '流动负债合计',
                             '流动资产合计_1', '流动负债合计_1',
                             '总股本', '总股本_1',
                             '其中：营业收入', '其中：营业成本',
                             '其中：营业收入_1', '其中：营业成本_1',
                             ]], on='股票代码', how='left').fillna(0)

    # 计算条件
    # c1
    ROA = np.where(datas['资产总计_1'] != 0, datas['归属于母公司所有者的净利润'] / datas['资产总计_1'], 0)
    datas['c1'] = np.where(ROA > 0, 1, 0)

    # c2
    datas['c2'] = np.where(datas['经营活动产生的现金流量净额'] > 0, 1, 0)

    # c3
    ROA_1 = np.where(datas['资产总计_2'] != 0, datas['归属于母公司所有者的净利润_1'] / datas['资产总计_2'], 0)
    datas['c3'] = np.where((ROA != 0) & (ROA_1 != 0) & (ROA > ROA_1), 1, 0)

    # c4
    CFO_scaled = np.where(datas['资产总计_1'] != 0, datas['经营活动产生的现金流量净额'] / datas['资产总计_1'], 0)
    datas['c4'] = np.where((CFO_scaled != 0) & (ROA != 0) & (CFO_scaled > ROA), 1, 0)

    # c5
    LEV = np.where(datas['资产总计'] != 0, datas['非流动负债合计'] / datas['资产总计'], 0)
    LEV_1 = np.where(datas['资产总计_1'] != 0, datas['非流动负债合计_1'] / datas['资产总计_1'], 0)
    datas['c5'] = np.where((LEV != 0) & (LEV_1 != 0) & (LEV > LEV_1), 1, 0)

    # c6
    CurrentRatio = np.where(datas['流动负债合计'] != 0, datas['流动资产合计'] / datas['流动负债合计'], 0)
    CurrentRatio_1 = np.where(datas['流动负债合计_1'] != 0, datas['流动资产合计_1'] / datas['流动负债合计_1'], 0)
    datas['c6'] = np.where((CurrentRatio != 0) & (CurrentRatio_1 != 0) & (CurrentRatio > CurrentRatio_1), 1, 0)

    # c7
    ZGB = datas['总股本']
    ZGB_1 = datas['总股本_1']
    datas['c7'] = np.where((ZGB != 0) & (ZGB_1 != 0) & (ZGB <= ZGB_1), 1, 0)

    # c8
    GrossMargin = np.where(datas['其中：营业收入'] != 0,
                           (datas['其中：营业收入'] - datas['其中：营业成本']) / datas['其中：营业收入'], 0)
    GrossMargin_1 = np.where(datas['其中：营业收入_1'] != 0,
                             (datas['其中：营业收入_1'] - datas['其中：营业成本_1']) / datas['其中：营业收入_1'], 0)
    datas['c8'] = np.where((GrossMargin != 0) & (GrossMargin_1 != 0) & (GrossMargin > GrossMargin_1), 1, 0)

    # c9
    AssetTurn = np.where(datas['资产总计'] != 0, datas['其中：营业收入'] / datas['资产总计'], 0)
    AssetTurn_1 = np.where(datas['资产总计_1'] != 0, datas['其中：营业收入_1'] / datas['资产总计_1'], 0)
    datas['c9'] = np.where((AssetTurn != 0) & (AssetTurn_1 != 0) & (AssetTurn > AssetTurn_1), 1, 0)

    # 计算 F-Score
    datas['F-Score'] = (datas['c1'] + datas['c2'] + datas['c3'] +
                        datas['c4'] + datas['c5'] + datas['c6'] +
                        datas['c7'] + datas['c8'] + datas['c9'])

    # print(datas[['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'F-Score']])

    return datas[['股票代码', 'F-Score']]



if __name__ == '__main__':
    codes = pd.read_csv("../../dataset/股票列表.csv", dtype=str)['股票代码']
    ret = _compute_fscore(codes, '202011')
    print(len(ret[ret['F-Score']==0]))
    print(ret)
