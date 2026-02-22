import pandas as pd
from tools import quarter_tool
from tools import datapath


def get_financial_data(date: str, quarter: str = '') -> pd.DataFrame:
    """
    获取财务数据 -- 返回quarter期的数据，公告日期要在date之前
    :param date: 当前date
    :param quarter: 返回期
    :return:
    """
    if quarter == '':
        # 获取当前 date 属于的期
        quarter = quarter_tool.current_quarter(date)

    # 从数据库读取当期财务数据
    ret = pd.read_csv(datapath.financial_path(quarter))

    # 修正股票代码
    ret['股票代码'] = ret['股票代码'].astype(str).str.zfill(6)

    # 修正公告日期 (完善年份)
    ret['财报公告日期'] = quarter[0:2] + (ret['财报公告日期'].astype(str))

    # 去重
    ret = ret.drop_duplicates(subset='股票代码', keep='first')

    # 根据日期筛选
    ret = ret.loc[ret['财报公告日期'] < date].reset_index(drop=True)

    return ret


def get_financial_data_v2(date: str, quarter: str = '') -> pd.DataFrame:
    """
    获取财务数据 -- 返回quarter期的数据，公告日期要在date之前
    :param date: 当前date
    :param quarter: 返回期
    :return:
    """
    if quarter == '':
        # 获取当前 date 属于的期
        quarter = quarter_tool.current_quarter(date)

    # 从数据库读取当期财务数据
    ret = pd.read_csv(datapath.financial_path_v2(quarter))
    print(ret)

    # 修正股票代码
    ret['股票代码'] = ret['股票代码'].astype(str).str.split('.').str[0]

    # 去重
    ret = ret.drop_duplicates(subset='股票代码', keep='first')

    ret['公告日期'] = ret['公告日期'].astype(str)

    # 根据日期筛选
    ret = ret.loc[ret['公告日期'] < date].reset_index(drop=True)

    return ret

if __name__ == "__main__":
    datas = get_financial_data_v2('20250331')
    print(datas)