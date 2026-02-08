"""
数据文件构建：
更新涨跌幅、行业哑变量以及各种基本因子
每月更新，将时间调整为最新月份并运行
"""

import factor_builder

factor_builder.build_change()
factor_builder.build_industry_dummies()
factor_builder.build_factors(start='201512',end='202602')
