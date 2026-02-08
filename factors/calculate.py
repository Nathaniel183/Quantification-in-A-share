"""
自行设计需要的计算方式
"""

import pandas as pd
import factors
from factors import factor_lab

vals1 = [
        # factors.Size(),
        # factors.Value(),
        factors.Turnover(),
        # factors.Momentum(12,1),
        factors.FScore(),
        # factors.MScore(),
        # factors.Industry(),
]

vals2 = [
    # factors.Size(),
    # factors.Value(),
    factors.Turnover(),
    # factors.Momentum(12,1),
    factors.FScore(),
    # factors.MScore(),
    # factors.Industry(),
]

pred = factor_lab.revenue(vals1, 12)
print(pred)

pred.to_csv(factors.wpath('prediction'))

rsk = factor_lab.risk(vals2, 36)
print(rsk)

w = factor_lab.mvw2(pred, rsk, 20)
print(w)

w.to_csv(factors.wpath('w1'))