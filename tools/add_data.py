import pandas as pd
import sys


def create_csv(input_path, output_path):
    """
    创建一个CSV文件，保留第一列数据，其他列的值都设置为0

    参数:
    input_path: 输入CSV文件路径
    output_path: 输出CSV文件路径
    """
    try:
        # 读取原始文件
        df = pd.read_csv(input_path)

        if len(df) == 0:
            print("警告: 输入文件是空的，只复制表头结构")
            # 创建空DataFrame并保存
            df.to_csv(output_path, index=False)
        else:
            # 保留第一列，其他列全部置为0
            first_column = df.columns[0]  # 获取第一列列名

            # 创建一个新的DataFrame，第一列保持不变
            new_df = pd.DataFrame()
            new_df[first_column] = df[first_column]

            # 对其他列设置值为0
            for col in df.columns[1:]:  # 从第二列开始
                # 保持原始的数据类型（如果可能），但填充0
                if df[col].dtype in ['int64', 'int32', 'int']:
                    new_df[col] = 0
                elif df[col].dtype in ['float64', 'float32', 'float']:
                    new_df[col] = 0.0
                else:
                    # 对于字符串、布尔等类型，用'0'填充
                    new_df[col] = '0'

            # 保存到输出文件
            new_df.to_csv(output_path, index=False)

            print(f"成功创建CSV文件: {output_path}")
            print(f"总行数: {len(df)}")
            print(f"第一列 '{first_column}' 保持不变")
            print(f"其他 {len(df.columns) - 1} 列的值已设置为0")

        return True

    except FileNotFoundError:
        print(f"错误: 输入文件 '{input_path}' 不存在")
        return False
    except pd.errors.EmptyDataError:
        print(f"错误: 输入文件 '{input_path}' 是空的")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False

# 使用示例
from tools import datapath
if __name__ == "__main__":
    input_file = datapath.financial_path("20250930")
    output_file = datapath.financial_path("20251231")
    create_csv(input_file, output_file)