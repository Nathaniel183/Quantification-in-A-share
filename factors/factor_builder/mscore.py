"""
M-Score指标 用于判断财务造假
"""
import numpy as np
import pandas as pd
from tools import quarter_tool, safe_div
from data_api import get_financial_data

def _compute_mscore(codes:pd.Series, date:str):
    """
    M-Score计算
    :param codes: 股票代码
    :param date: 当前日期
    :param m_gate: M-Score的阈值
    :param backtrack: 数据不足时，是否回溯前一期
    :param bt_gate: 回溯阈值，当数据不足codes的多少比例时回溯
    :return: DataFrame(['股票代码', 'M-Score'])
    """
    # 去重
    codes = codes.drop_duplicates(keep='first')

    # 获取期数
    q = quarter_tool.current_quarter(date)
    q_1 = quarter_tool.prev_quarter(q)
    q_2 = quarter_tool.prev_quarter(q_1)

    # 尝试获取当期 M-Score 数据
    datas = _compute(codes, date, q)

    # 第一次找出未获取到数据的代码
    remain_codes = datas.loc[datas['M-Score'].isna(), '股票代码']

    # 尝试获取前期 M-Score 数据
    datas_1 = _compute(remain_codes, date, q_1)

    # 合并前后数据
    map = datas_1.set_index('股票代码')['M-Score'].to_dict()
    datas.loc[datas['M-Score'].isna(), 'M-Score'] = datas.loc[datas['M-Score'].isna(), '股票代码'].map(map)

    # 第二次找出未获取到数据的代码
    remain_codes = datas.loc[datas['M-Score'].isna(), '股票代码']

    # 尝试获取前前期 M-Score 数据
    datas_2 = _compute(remain_codes, date, q_2)

    # 合并前后数据
    map = datas_2.set_index('股票代码')['M-Score'].to_dict()
    datas.loc[datas['M-Score'].isna(), 'M-Score'] = datas.loc[datas['M-Score'].isna(), '股票代码'].map(map)

    return datas



def _compute(codes:pd.Series, date:str, q:str):
    # 转换成 DataFrame
    codes = codes.to_frame('股票代码')

    # 获取期数
    q_1 = quarter_tool.prev_quarter(q)

    # 获取财务数据
    ret = get_financial_data(date, q)
    ret_1 = get_financial_data(date, q_1)

    # 添加后缀
    ret_1 = ret_1.rename(columns={col: f"{col}_1" for col in ret_1.columns if col != '股票代码'})

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

    ret = ret.merge(ret_1, on='股票代码', how='outer').fillna(fill_dict)

    # 提取所需数据
    datas = codes.merge(ret[['股票代码',
                             '其中：营业收入', '其中：营业收入_1',
                             '其中：营业成本', '其中：营业成本_1',
                             '应收票据', '应收账款', '其他应收款',
                             '应收关联公司款', '应收利息', '应收股利',
                             '应收票据_1', '应收账款_1', '其他应收款_1',
                             '应收关联公司款_1', '应收利息_1', '应收股利_1',
                             '流动资产合计', '固定资产', '在建工程',
                             '工程物资', '生产性生物资产', '交易性金融资产', '资产总计',
                             '流动资产合计_1', '固定资产_1', '在建工程_1',
                             '工程物资_1', '生产性生物资产_1', '交易性金融资产_1', '资产总计_1',
                             '固定资产折旧、油气资产折耗、生产性生物资产折旧',
                             '固定资产折旧、油气资产折耗、生产性生物资产折旧_1',
                             '销售费用', '管理费用', '销售费用_1', '管理费用_1',
                             '长期借款', '应付债券', '长期应付款', '流动负债合计',
                             '长期借款_1', '应付债券_1', '长期应付款_1', '流动负债合计_1',
                             '归属于母公司所有者的净利润', '经营活动产生的现金流量净额',
                             # '', '', '', '', '', '',
                             ]], on='股票代码', how='left').fillna(np.nan)

    # print(datas)

    YSHJ = (datas['应收票据'] + datas['应收账款'] + datas['其他应收款']
            + datas['应收关联公司款'] + datas['应收利息'] + datas['应收股利'])

    YSHJ_1 = (datas['应收票据_1'] + datas['应收账款_1'] + datas['其他应收款_1']
              + datas['应收关联公司款_1'] + datas['应收利息_1'] + datas['应收股利_1'])

    # 1.DSRI
    DSRI = safe_div(a=safe_div(YSHJ, datas['其中：营业收入'], None),
                    b=safe_div(YSHJ_1, datas['其中：营业收入_1'], None),
                    default=None)

    # print(DSRI)

    # 2.GMI
    ML = datas['其中：营业收入'] - datas['其中：营业成本']
    ML_1 = datas['其中：营业收入_1'] - datas['其中：营业成本_1']
    GMI = safe_div(a=safe_div(ML_1, datas['其中：营业收入_1'], None),
                   b=safe_div(ML, datas['其中：营业收入'], None),
                   default=None)

    # print(GMI)

    # 3.AQI
    CurrentAssets = datas['流动资产合计']
    CurrentAssets_1 = datas['流动资产合计_1']

    PPE = datas['固定资产'] + datas['在建工程'] + datas['工程物资'] + datas['生产性生物资产']
    PPE_1 = datas['固定资产_1'] + datas['在建工程_1'] + datas['工程物资_1'] + datas['生产性生物资产_1']

    Securities = datas['交易性金融资产']
    Securities_1 = datas['交易性金融资产_1']

    AQI = safe_div(1 - safe_div(CurrentAssets + PPE + Securities, datas['资产总计'], None),
                   1 - safe_div(CurrentAssets_1 + PPE_1 + Securities_1, datas['资产总计_1'], None),
                   None)

    # print(AQI)

    # 4.SGI
    SGI = safe_div(datas['其中：营业收入'], datas['其中：营业收入_1'], None)

    # print(SGI)

    # 5.DEPI
    ZJ = datas['固定资产折旧、油气资产折耗、生产性生物资产折旧']
    ZJ_1 = datas['固定资产折旧、油气资产折耗、生产性生物资产折旧_1']
    DEPI = safe_div(safe_div(ZJ_1, ZJ_1 + PPE_1, None),
                    safe_div(ZJ, ZJ + PPE, None),
                    0)

    # print(DEPI)

    # 6.SGAI
    SGA = datas['销售费用'] + datas['管理费用']
    SGA_1 = datas['销售费用_1'] + datas['管理费用_1']

    SGAI = safe_div(safe_div(SGA, datas['其中：营业收入'], None),
                    safe_div(SGA_1, datas['其中：营业收入_1'], None),
                    None)

    # print(SGAI)

    # 7.LVGI
    LongTermDebt = datas['长期借款'] + datas['应付债券'] + datas['长期应付款']
    LongTermDebt_1 = datas['长期借款_1'] + datas['应付债券_1'] + datas['长期应付款_1']
    CurrentLiab = datas['流动负债合计']
    CurrentLiab_1 = datas['流动负债合计_1']

    LVGI = safe_div(safe_div(CurrentLiab + LongTermDebt, datas['资产总计'], None),
                    safe_div(CurrentLiab_1 + LongTermDebt_1, datas['资产总计_1'], None),
                    None)

    # print(LVGI.tail(300))

    # 8.TATA
    TATA = safe_div(datas['归属于母公司所有者的净利润'] + datas['经营活动产生的现金流量净额'],
                    datas['资产总计'], None)
    # print(TATA)

    # M
    datas['M-Score'] = (-4.84
                        + 0.92 * DSRI
                        + 0.528 * GMI
                        + 0.404 * AQI
                        + 0.892 * SGI
                        + 0.115 * DEPI
                        - 0.172 * SGAI
                        + 4.679 * TATA
                        - 0.327 * LVGI
                        )

    return datas[['股票代码', 'M-Score']]

# if __name__ == '__main__':
#     codes = pd.read_csv("../../dataset/股票列表.csv", dtype=str)['股票代码']
#     ret = _compute_mscore(codes, '202004')
#     print(len(ret[ret['M-Score'].isna()]))
#     print(ret)
