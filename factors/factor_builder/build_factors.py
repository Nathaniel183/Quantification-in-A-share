from .momentum_factor import _compute_momentum
from .fscore_index import _compute_fscore
from .mscore_index import _compute_mscore
from .size_factor import _compute_size
from .value_factor import _compute_value
from .turnover_factor import _compute_turnover

from .ROE import _compute_ROE
from .TO import _compute_TO
from .ABTO import _compute_ABTO
from .VOL import _compute_VOL
from .MAX import _compute_MAX
from .ILL import _compute_ILL
from .EP import _compute_EP
from .BM import _compute_BM
# from .CFP import *

import data_api
from tools import month_tool
import pandas as pd
import factors



def build_factors(start:str='200001', end:str='209912'):
    """
    构建因子数据库 -- 由于目前股票列表接口未处理完善，未计算已经退市的票
    :param start:
    :param end:
    :return:
    """

    codes = data_api.get_stock_list()['股票代码']
    print(codes)

    _build_factor(_compute_ROE,codes,start,end,'ROE')
    _build_factor(_compute_TO,codes,start,end,'TO')
    _build_factor(_compute_ABTO,codes,start,end,'ABTO')
    _build_factor(_compute_VOL,codes,start,end,'VOL')
    _build_factor(_compute_MAX,codes,start,end,'MAX')
    _build_factor(_compute_ILL,codes,start,end,'ILL')
    _build_factor(_compute_EP,codes,start,end,'EP')
    _build_factor(_compute_BM,codes,start,end,'BM')

    fscore = _build_factor(_compute_fscore,codes,start,end,'F-Score')
    mscore = _build_factor(_compute_mscore,codes,start,end,'M-Score')
    size = _build_factor(_compute_size,codes,start,end,'size')
    value = _build_factor(_compute_value,codes,start,end,'value')
    turnover = _build_factor(_compute_turnover,codes,start,end,'turnover')
    mmt_n1 = _build_factor(_compute_momentum,codes,start,end,"momentum_n1_s0", n=1,skip=0)
    mmt_n3s0 = _build_factor(_compute_momentum,codes,start,end,"momentum_n3_s0", n=3,skip=0)
    mmt_n6s0 = _build_factor(_compute_momentum,codes,start,end,"momentum_n6_s0", n=6,skip=0)
    mmt_n12s1 = _build_factor(_compute_momentum,codes,start,end,"momentum_n12_s1", n=12,skip=1)

def _build_factor(
        compute_func,  # 计算函数
        codes:pd.Series,  # 股票代码
        start: str,  # 开始月份
        end: str,  # 结束月份
        indicator_name:str,  # 指标名称
        **kwargs  # 传递给计算函数的额外参数
):
    """
    支持额外参数的指标计算函数
    """
    import pandas as pd
    import os

    # 1. 检查是否已有文件
    csv_path = factors.fpath(indicator_name)

    result_df = pd.DataFrame({'code': codes})
    if os.path.exists(csv_path):
        existing_df = pd.read_csv(csv_path, dtype={'code': str})
        result_df = existing_df
        month_cols = [col for col in existing_df.columns if col != 'code' and col.isdigit()]
        if month_cols:
            last_month = max(month_cols)
            start = month_tool.next_month(str(last_month))

    # 2. 准备存储结果

    # 3. 遍历月份计算
    current_month = start
    while current_month <= end:
        print(f"计算 {indicator_name} - {current_month}")

        # 调用计算函数，传入额外参数
        month_data = compute_func(codes, current_month, **kwargs)

        # 假设返回的DataFrame包含指标值
        # 这里需要知道指标列的列名
        # 方法1：假设指标列名就是 indicator_name
        if indicator_name in month_data.columns:
            month_data = month_data.rename(columns={indicator_name: current_month})
        # 方法2：如果计算函数返回的不是标准格式，可以取第一列数值列
        else:
            value_col = [c for c in month_data.columns if c != '股票代码'][0]
            month_data = month_data.rename(columns={value_col: current_month})

        # 合并到结果
        month_data = month_data.rename(columns={'股票代码':'code'})
        result_df = pd.merge(result_df, month_data[['code', current_month]],
                             on='code', how='left')

        # 保存
        result_df.to_csv(csv_path, index=False)

        print("零数据：",len(month_data[month_data[current_month]==0]))
        print("空数据：",len(month_data[month_data[current_month].isna()]))

        # 获取下一个月
        current_month = month_tool.next_month(str(current_month))


    return result_df


if __name__ == '__main__':
    build_factors(start='201001',end='202602')

