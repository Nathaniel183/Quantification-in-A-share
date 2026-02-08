"""
构建/更新收益率（涨跌幅）
"""
import factors
from data_api import get_monthly_hfq_change

def build_change():
    """
    更新月涨跌幅后复权并保存
    :return:
    """
    datas = get_monthly_hfq_change().reset_index()
    datas.to_csv(factors.fpath('change'), index=False)

if __name__ == "__main__":
    build_change()