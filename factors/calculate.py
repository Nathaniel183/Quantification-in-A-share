"""
自行设计需要的计算方式
"""

import factors
from factors import factor_lab

vals1 = [
    factors.Market(),
    # factors.Size(),
    # factors.Value(),
    # factors.Turnover(),
    # factors.Momentum(12,1),
    factors.FScore(),
    # factors.MScore(),
    # factors.Industry(),
    # factors.EP(),
    # factors.BM(),
    # factors.ROE(),
    # factors.VOL(),
    # factors.MAX(),
    factors.TO(),
    # factors.ABTO(),
    factors.ILL(),
    # factors.STR(),
]

pred = factor_lab.revenue(vals1, 36)
print(pred)
pred.to_csv(factors.wpath('pred_TO_ILL_FS_36'))


# vals2 = [
#     factors.Size(),
#     factors.Value(),
#     factors.Turnover(),
#     # factors.Momentum(12,1),
#     factors.FScore(),
#     # factors.MScore(),
#     factors.Industry(),
# ]

# rsk = factor_lab.risk(vals2, 48)
# print(rsk)
#
# w = factor_lab.mvw2(pred, rsk, 20)
# print(w)
#
# w.to_csv(factors.wpath('w1'))