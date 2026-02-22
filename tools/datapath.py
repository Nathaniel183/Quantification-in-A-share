import os

# # 获取当前文件的绝对路径
# current_file_path = os.path.dirname(os.path.abspath(__file__))
# data_path = current_file_path+"/../dataset/"

# 指定系统中数据库绝对路径
data_path = "D:/Projects/PythonProject/A-share_database/"

stock_path = data_path + "股票列表.csv"
index_path = data_path + "指数列表.csv"
name_path = data_path + "name.csv"
st_path = data_path + "退市股票列表.csv"
con_daily_hfq_path = data_path + "daily_hfq.csv"

def pv_daily_hfq_path(code:str)->str:
    return data_path + f"daily_hfq/{code}.csv"

def pv_monthly_hfq_path(code:str)->str:
    return data_path + f"monthly_hfq/{code}_monthly_hfq.csv"

def pv_monthly_qfq_path(code:str)->str:
    return data_path + f"monthly_qfq/{code}_monthly_qfq.csv"

def pv_index_path(code:str)->str:
    return data_path + f"指数_月_kline/{code}_月.csv"

def financial_path(quarter:str)->str:
    return data_path + f"历史详细数据_CSV/全部上市公司财务信息_{quarter}.csv"

def financial_path_v2(quarter:str)->str:
    return data_path + f"财务数据/转换结果/{quarter}.csv"