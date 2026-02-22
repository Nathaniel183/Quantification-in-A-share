"""
该软件包用于获取、计算、记录、更新因子和指标
在软件包内，使用 build 模块调用各指标计算方法，并记录计算结果CSV，同时在有新数据时更新
在软件包外，使用获取接口直接从记录的数据中获取
"""
from .factor import (Factor, Change, Market, Industry,
                    Size, Turnover, Value, Momentum, FScore, MScore,
                     EP, BM, ROE, VOL, MAX, TO, ABTO, ILL, STR)

import os
current_file_path = os.path.dirname(os.path.abspath(__file__))

def wpath(name: str) -> str:
    return current_file_path + f"/weight/{name}.csv"

def fpath(name: str) -> str:
    return current_file_path + f"/factor_data/{name}.csv"

__all__ = ['wpath', # 获取权重文件路径
           'fpath', # 因子数据文件路径
           'Factor', # 因子抽象类
           'Change', # 涨跌幅
           'Market', # 市场因子 不可用于预测
           'Industry', # 行业哑变量
           'Size', # 规模因子
           'Turnover', # 换手率因子
           'Value', # 价值因子
           'Momentum', # 动量因子
           'FScore', # 基本面因子
           'MScore', # 造假因子

           'EP',    # 规模，净利润/总市值
           'BM',    # 价值，账面价值/总市值
           'ROE',   # 盈利，净利润/净资产
           'VOL',   # 波动，最近1个月日收益率的标准差
           'MAX',   # 波动，最近1个月最大的5个日收益率的均值
           'TO',    # 换手，最近12个月换手率均值
           'ABTO',  # 换手，最近一个月日均换手率/最近12个月日均换手率
           'ILL',   # 流动性， (日绝对收益绝对值/日成交额)的月平均值
           'STR',   # 反转，最近1个月收益率
           ]
