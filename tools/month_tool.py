"""
辅助方法 求当前/前/后某月的字符串
"""

def cur_month(date:str):
    return date[0:6]

def prev_month(month:str, n:int=1):
    """
    当前月过去第 n 月
    :param month: 当前月 "yyyymm"
    :param n: 过去月数
    :return:
    """
    y = month[0:4]
    m = month[4:6]
    y = str(int(y)-int((n-int(m))/12+1)).zfill(4)
    m = str((int(m)-n-1)%12+1).zfill(2)
    return y+m

def next_month(month:str, n:int=1):
    """
    当前月未来第 n 月
    :param month: 当前月 "yyyymm"
    :param n: 未来月数
    :return:
    """
    y = month[0:4]
    m = month[4:6]
    y = str(int(y)+int((n+int(m)-1)/12)).zfill(4)
    m = str((int(m)+n-1)%12+1).zfill(2)
    return y+m



if __name__ == '__main__':
    # print(cur_month('20250630'))

    for m in range (1,13):
        m = str(m).zfill(2)
        print()
        print(m)
        for i in range(25):
            print(i,prev_month('2025'+m,i))