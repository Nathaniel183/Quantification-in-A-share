"""
辅助方法 求当前/前/后一期的字符串
"""

def prev_quarter(quarter:str):
    choices = ['0331','0630', '0930', '1231']
    y = quarter[0:4]
    q = quarter[4:8]
    if q not in choices:
        return -1

    q_index = choices.index(q)
    if q_index == 0:
        y = str(int(y)-1)
    q_index = (q_index-1)%4
    q = choices[q_index]
    return y+q

def next_quarter(quarter:str):
    choices = ['0331','0630', '0930', '1231']
    y = quarter[0:4]
    q = quarter[4:8]
    if q not in choices:
        return -1

    q_index = choices.index(q)
    if q_index == 3:
        y = str(int(y)+1)
    q_index = (q_index+1)%4
    q = choices[q_index]
    return y+q

def current_quarter(date:str):
    choices = ['0331','0630', '0930', '1231']
    y = date[0:4]
    d = date[4:8]
    for index, quarter in enumerate(choices):
        if d<quarter:
            d = choices[index-1]
            if index == 0:
                y = str(int(y)-1)
            break
    return y+d

def fixed_quarter(date:str):
    """
    获取指定日期时按照约定应该获取的期数
    :param date: 'YYYYMMDD' / 'YYYYMM'
    :return: 期数str
    """
    choices = ['0331', '0630', '0930', '1231']
    y = date[0:4]
    m = date[4:6]
    if m in ['01', '02', '03', '04']:
        y = str(int(y)-1)
        d = choices[2]
    elif m in ['05', '06', '07', '08']:
        d = choices[0]
    elif m in ['09', '10']:
        d = choices[1]
    elif m in ['11', '12']:
        d = choices[2]
    return y + d


if __name__ == '__main__':
    for m in range(1,13):
        date = f"2025{m:02d}01"
        print(f"{date}->{fixed_quarter(date)}")