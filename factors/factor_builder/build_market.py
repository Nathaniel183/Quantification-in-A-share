import data_api
import factors

def build_market():
    # 构造市场因子
    datas = data_api.get_monthly_index()
    datas['market'] = (datas['收盘']/datas['开盘'])-1
    market = datas[['日期','market']].rename(columns={'日期':'date'})
    print(market)
    market.to_csv(factors.fpath('market'), index=False)