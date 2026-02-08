"""
该软件包用于获取、计算、记录、更新因子和指标
在软件包内，使用 build 模块调用各指标计算方法，并记录计算结果CSV，同时在有新数据时更新
在软件包外，使用获取接口直接从记录的数据中获取
"""
from .factor import (Factor, Change, Market, Industry,
                    Size, Turnover, Value, Momentum, FScore, MScore)

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
           ]
