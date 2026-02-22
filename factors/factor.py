import os

import numpy as np
import pandas as pd

class Factor:
    """
    因子类（包括任何变量）
    Attributes:
        name(str):变量名称
        dshape(str):原数据文件格式，
                    'N_T' col=['code', 'date1', 'date2',...],
                    'N_K' col=['code', 'val1', 'val2',...],
                    'NT_K'col=['code', 'date', 'val1', 'val2',...].
        data(pd.DataFrame):读取的数据，会被组织成格式 DataFrame(index=(code, date), col=[vals])，
                            注意'N_K'格式数据不随时间变化，date索引全为'all';'T_K'格式数据不随标的变化，code索引全为'all'.
        standardize(bool):是否需要去极值和标准化
        extremum(float):去除极值比例
    Methods:
        get_name:获取变量名称
        get_dshape:获取数据形状
        get_data:获取数据，可传入date索引
        get_date_index:获取数据所有date索引
        get_code_index:获取数据所有code索引
    """
    def __init__(self, name:str, dshape:str,
                 standardize:bool=True, extremum:float=0.05,
                 need_log:bool=False, log_bias:float=0.0):
        self.name = name
        self.dshape = dshape # N_T, NT_K, N_K, T_K
        self.data = None
        self.standardize = standardize
        self.extremum = extremum
        self.need_log = need_log
        self.log_bias = log_bias

        print(f"读取变量 {self.name} -- {self.dshape}")
        self._init_data()
        print(self.data)
        print()

    def _init_data(self):
        # 1.判断原始数据类型
        if self.dshape == 'N_T':
            data = pd.read_csv(self._factor_path(), dtype={'code': str})
            data = data.set_index(['code'])
            data = data.stack().reset_index()
            data.columns = ['code', 'date', self.name]
            data = data.set_index(['code','date'])
            data = data.reorder_levels(['code', 'date'])
            self.dshape = 'NT_K'
            self.data = data
        elif self.dshape == 'NT_K':
            data = pd.read_csv(self._factor_path(), index_col=(0, 1), dtype={'date': str, 'code': str})
            data = data.reorder_levels(['code', 'date'])
            self.data = data
        elif self.dshape == 'N_K':
            data = pd.read_csv(self._factor_path(), index_col=(0), dtype={'code': str})
            data['date'] = 'all'  # 添加date列，所有行赋值为'all'
            data = data.set_index('date', append=True)  # 将date设为索引，保持原有索引
            data = data.reorder_levels(['code', 'date'])
            self.data = data
        elif self.dshape == 'T_K':
            data = pd.read_csv(self._factor_path(), index_col=(0), dtype={'date': str})
            data['code'] = 'all'  # 添加code列，所有行赋值为'all'
            data = data.set_index('code', append=True)  # 将code设为索引，保持原有索引
            data = data.reorder_levels(['code', 'date'])
            self.data = data
        else:
            self.data = None

        # 2.去极值 和 标准化
        if self.standardize:
            self._standardize()

        if self.data is not None:
            self.data = self.data.dropna()

    def _factor_path(self):
        """
        获取因子数据文件路径
        :return: 文件路径
        """
        factor_name = self.name
        current_file_path = os.path.dirname(os.path.abspath(__file__))
        file_path = current_file_path + f"/factor_data/{factor_name}.csv"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        return file_path

    def _standardize(self):
        """
        将因子数据去极值和标准化
        :param data: DataFrame(col=['股票代码', xxx]), 因子数据
        :param extremum: 去除 n分位的极值
        :return: DataFrame(col=['股票代码', xxx]), 处理后的因子数据
        """
        extremum = self.extremum

        result_list = []
        for date, df in self.data.groupby(level='date'):
            df_copy = df.copy()

            # 对每个因子列进行处理
            factor_cols = [col for col in df_copy.columns]

            for col in factor_cols:
                # 1. 取log
                if self.need_log:
                    df_copy[col] = np.log(df_copy[col]+self.log_bias)

                # 2. 去极值
                lower = df_copy[col].quantile(extremum)
                upper = df_copy[col].quantile(1 - extremum)
                df_copy[col] = df_copy[col].clip(lower=lower, upper=upper)

                # 3. 标准化
                mean_val = df_copy[col].mean()
                std_val = df_copy[col].std()
                if std_val > 0:
                    df_copy[col] = (df_copy[col] - mean_val) / std_val
                else:
                    df_copy[col] = 0
            result_list.append(df_copy)
        self.data = pd.concat(result_list)

    def get_name(self)->str:
        return self.name

    def get_dshape(self)->str:
        return self.dshape

    def get_data(self, date:str=None)->pd.DataFrame:
        """
        获取因子数据
        :return: DataFrame(index=(code, date), column=['因子名'])
                或 DataFrame(index=(code), column=['因子名'])
        """
        try:
            if date is None:
                return self.data.copy()
            else:
                return self.data.xs(date, level='date').copy()
        except:
            print(f"获取{self.name}失败: 索引{date}")

    def get_date_index(self)->pd.Index:
        return self.data.index.get_level_values('date').unique()

    def get_code_index(self)->pd.Index:
        return self.data.index.get_level_values('code').unique()


class Change(Factor):
    def __init__(self):
        super().__init__(f"change", "NT_K", False)

class Market(Factor):
    def __init__(self):
        super().__init__(f"market", "T_K", False)

class Industry(Factor):
    def __init__(self):
        super().__init__(f"industry", "N_K", False)

class Size(Factor):
    def __init__(self):
        super().__init__("size", "N_T")

class Value(Factor):
    def __init__(self):
        super().__init__("value", "N_T")

class Turnover(Factor):
    def __init__(self):
        super().__init__("turnover", "N_T")

class FScore(Factor):
    def __init__(self):
        super().__init__("F-Score", "N_T", extremum=0)

class MScore(Factor):
    def __init__(self):
        super().__init__("M-Score", "N_T")

class Momentum(Factor):
    def __init__(self, n:int=6, skip:int=0, extremum:float=0.05):
        super().__init__(f"momentum_n{n}_s{skip}", "N_T", extremum=extremum)

class EP(Factor):
    def __init__(self):
        super().__init__("EP", "N_T", extremum=0.01)

class BM(Factor):
    def __init__(self):
        super().__init__("BM", "N_T", extremum=0.01,
                         need_log=True, log_bias=0.0)

class ROE(Factor):
    def __init__(self):
        super().__init__("ROE", "N_T", extremum=0.02)

class VOL(Factor):
    def __init__(self):
        super().__init__("VOL", "N_T", extremum=0.01)

class MAX(Factor):
    def __init__(self):
        super().__init__("MAX", "N_T", extremum=0.02)

class TO(Factor):
    def __init__(self):
        super().__init__("TO", "N_T", extremum=0.01,
                         need_log=True, log_bias=1.0)

class ABTO(Factor):
    def __init__(self):
        super().__init__("ABTO", "N_T", extremum=0.02,
                         need_log=True, log_bias=1.0)

class ILL(Factor):
    def __init__(self):
        super().__init__("ILL", "N_T", extremum=0.02,
                         need_log=True, log_bias=1.0)

class STR(Momentum):
    def __init__(self):
        super().__init__(n=1, skip=0, extremum=0.01)

if __name__ == '__main__':
    factor1 = Change()
    factor2 = Momentum()
    factor3 = Industry()

    factor4 = Market()
    # print(factor1.get_data('202512'))
    # print(factor2.get_data('202511'))
