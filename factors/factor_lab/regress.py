import numpy as np
import pandas as pd
import factors
import statsmodels.api as sm

def ols_regress(change:factors.Factor, vals:pd.DataFrame):

    t_values = []
    coefs = []
    date_list = change.get_date_index()
    for i, date in enumerate(date_list):

        change_t = change.get_data(date)

        val = vals.xs(date, level='date')
        val = pd.concat([val, change_t], axis=1, join='inner')
        y = val['change']
        z = val.drop(columns=['change'])

        z_with_const = sm.add_constant(z)  # 添加截距项
        model = sm.OLS(y, z_with_const)
        results = model.fit()

        t_values.append(results.tvalues[:])
        params = results.params
        params['date'] = date
        coefs.append(params)

        # if i == 0:
        #     print(results.summary())
        #     # 获取具体统计量
        #     print(f"R-squared: {results.rsquared}")
        #     print(f"Coefficients: {results.params}")
        #     print(f"P-values: {results.pvalues}")
        #     print(f"Confidence Intervals:\n{results.conf_int()}")

    # 计算时间序列T值
    t_values_df = pd.DataFrame(t_values)
    mean_t = t_values_df.mean() / t_values_df.std() * np.sqrt(len(date_list))
    print("OLS回归 T值:")
    print(mean_t)
    print()

    coefs = pd.DataFrame(coefs).set_index('date')
    # coefs_m = coefs.mean()
    print("OLS回归 系数和截距:")
    print(coefs)
    print()
    return coefs


def wls_regress(change:factors.Factor, vals:pd.DataFrame, w:pd.DataFrame):

    w.columns = ['w']
    t_values = []
    coefs = []
    resid_rows = []
    date_list = change.get_date_index()
    for i, date in enumerate(date_list):

        change_t = change.get_data(date)
        w_t = w.xs(date, level='date')
        val = vals.xs(date, level='date')
        val = pd.concat([val, change_t, w_t], axis=1, join='inner')
        y = val['change']
        w_t = val['w']
        z = val.drop(columns=['change','w'])

        z_with_const = sm.add_constant(z)  # 添加截距项
        model = sm.WLS(y, z_with_const, weights=w_t)
        results = model.fit()

        # 记录t值、系数和截距
        t_values.append(results.tvalues[:])
        params = results.params
        params['date'] = date
        coefs.append(params)

        # 计算残差
        eps = y - results.predict(z_with_const)
        eps.name = 'eps'
        eps.index = pd.MultiIndex.from_product([[date], eps.index], names=['date', 'code'])
        resid_rows.append(eps)

        # if i == 0:
        #     print(results.summary())
        #     # 获取具体统计量
        #     print(f"R-squared: {results.rsquared}")
        #     print(f"Coefficients: {results.params}")
        #     print(f"P-values: {results.pvalues}")
        #     print(f"Confidence Intervals:\n{results.conf_int()}")

    # 计算时间序列T值
    t_values_df = pd.DataFrame(t_values)
    mean_t = t_values_df.mean() / t_values_df.std() * np.sqrt(len(date_list))
    print("WLS回归 T值:")
    print(mean_t)
    print()

    coefs = pd.DataFrame(coefs).set_index('date').sort_index()
    residuals = pd.concat(resid_rows).sort_index() if resid_rows else pd.Series(dtype=float, name='eps')
    # coefs_m = coefs.mean()
    # print("WLS回归 系数和截距:")
    # print(coefs)
    # print()
    return coefs, residuals
