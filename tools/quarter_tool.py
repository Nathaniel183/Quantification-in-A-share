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

if __name__ == '__main__':
    print(current_quarter('202403'))