import pandas as pd

import factors

w = pd.read_csv(factors.wpath('w1'), index_col=(0, 1), dtype={'date': str, 'code': str})

date_list = w.index.get_level_values('date').unique().tolist()
for date in date_list:
    print(f"Date: {date}")
    w_t = w.xs(date, level='date')
    print(w_t[w_t['w']!=0])