"""
自行设计需要的计算方式
"""

import factors
from factors import factor_lab

vals1 = [
    # factors.Market(),
    # factors.Size(),
    # factors.Value(),
    factors.Turnover(),
    # factors.Momentum(12,1),
    # factors.FScore(),
    factors.FScore_fix(),
    # factors.MScore(),
    # factors.Industry(),
    # factors.EP(),
    # factors.BM(),
    # factors.ROE(),
    # factors.VOL(),
    # factors.MAX(),
    # factors.TO(),
    # factors.ABTO(),
    # factors.ILL(),
    # factors.STR(),
]

period_dict = {
    'turnover':36,
    'TO':24,
    'F-Score':36,
    'F-Score_fix':36,
    'EP':24,
    'BM':24,
    'ROE':24,
    'ILL':12,
}

lam_dict = {
    'turnover': 0.94,
    'TO': 0.95,
    'F-Score': 0.98,
    'EP': 0.97,
    'BM': 0.97,
    'ROE': 0.98,
    'ILL': 0.93,
}

pred = factor_lab.revenue(vals1, 36, period_dict, method='mean', lam_dict=lam_dict)
print(pred)
pred.to_csv(factors.wpath('pred_T_FSf'))


# vals2 = [
#     factors.Market(),
#     factors.Size(),
#     # factors.Value(),
#     # factors.Turnover(),
#     factors.Momentum(12,1),
#     # factors.FScore(),
#     # factors.MScore(),
#     factors.Industry(),
#     # factors.EP(),
#     # factors.BM(),
#     # factors.ROE(),
#     factors.VOL(),
#     # factors.MAX(),
#     # factors.TO(),
#     # factors.ABTO(),
#     # factors.ILL(),
#     # factors.STR(),
# ]
#
# rsk = factor_lab.risk(vals2, 36)
# print(rsk)
#
# w = factor_lab.mvw2(pred, rsk, 20)
# print(w)
#
# w.to_csv(factors.wpath('w_T_FS_r_MISMoV'))