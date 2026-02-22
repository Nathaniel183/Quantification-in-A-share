"""
基于预测收益率的策略
"""
import pandas as pd

import factors
from strategies.strategy import Strategy
import data_api
class StgPred(Strategy):
    """
    策略类
    Attributes:
        资产相关
        cash(float):现金，表示账户中可用现金，随交易成交变动。
        fund(float):资产，表示账户持股的总价值，不随交易成交立即变动，只在每次时序循环结束后使用收盘价重新计算。
        init_cash(float): 初始资金，记录程序的初始资金，设定后不再改变。

        时序量价数据
        datas(pd.DataFrame(index=(date, code), col=['open', 'close', ...]):
            时序量价数据，索引(date, code)，列必须包含['open','close']，其他属性可自定义。请传入给定格式的数据。

        时间相关
        date_list(list):日期列表，从时序数据datas的一级索引date中提取。
        date_cur(str):当前日期，在时序循环中被依次设置为date_list中的值。
        date_index(int):当前日期在date_list中的索引值。

        股票代码相关
        code_list(list):股票列表，从时序数据datas的二级索引code中提取。
        code_cur(pd.Series):当前股票列表，在时序循环中被依次设置为，在时序数据datas中指定索引date提取出的索引code列表。

        仓位相关
        position(pd.DataFrame(index=code, col=['pos'])):
            当前仓位，随交易成交变动，索引为所有股票代码code_list，列为'pos'，记录各股票持有手数（不是仓位比例）。
        position_record(pd.DataFrame(col=['date', 'code', 'income'])):
            仓位记录，每次循环结束更新，每条数据表示该循环所在时间、某持仓股票的收益（income列）。最后save将其保存为文件。
            供内置函数使用，不建议在策略中使用。

        订单相关（供内置函数使用，不建议在策略中使用）
        orders(pd.DataFrame(col=['date','type','limit','target','price','count','completed', 'canceled'])):
            订单记录，date下单时间，type为'buy'/'sell'，limit是否为限价订单，
            target为标的股票代码，price为订单价格，count为订单数量，completed是否完成，canceled为是否取消。
            该记录最终被save保存为文件。

        资产记录（供内置函数使用，仅用于结果展示，不建议在策略中使用）
        asset_record(pd.DataFrame(index=date, col=['total'])):
            总资产记录，记录每一时间现金加资产总和，每次循环结束更新。
            最终在save中各项被除以初始资金，转化为收益率形式保存。

        收益回撤记录（以下属性只在程序结束后计算，供内置函数使用，仅用于结果展示，请勿在策略中使用）
        total(float):最终总资产
        total_return(float):最终总收益率
        annualized_return(float):最终年化收益率
        max_down(float):最大回撤

        策略名
        strategy_name(str):策略名，建议实现时重写

    生命周期说明:
        1.初始化: stg = Strategy(cash=初始资金,
                                datas=构建符合要求的数据,
                                save=是否需要保存运行结果(默认True))
        2.回测程序运行: Strategy.run()，循环遍历date_list。
        3.当前数据获取: 在run函数的循环中，首先实现更新当前时间数据和股票数据。
        4.策略循环执行: 在run函数的循环中，调用next函数，执行策略逻辑。
            在其中通过buy、sell、clear函数下单会被立即尝试执行，以数据中open价格视为当前市价。
        5.订单执行: 在run函数的循环中，next调用结束后，_order_exe被调用，尝试执行未执行的订单。
        6.更新资产情况: 在run函数的循环中，_fund_update被调用，根据close价格重新计算持仓价值。
        7.循环中记录: 在run函数的循环中，_cycle_record被调用，记录当前总资产和持仓信息，用于最终展示。
        8.回测总结: 在run函数所有循环结束后，_summarize被调用，计算并显示相关回测信息。
            包括总资产、总收益率、年话收益率、最大回撤。
        9.记录保存: 如果设置save=True，_save被调用，保存相关信息为文件。
        10.用户自定义结束处理: custom_finally被调用。
        11.绘制收益曲线: _plot被调用，显示收益曲线图（以收益率形式）。

    实现说明：
        1.在init中为策略命名。
        2.在next中实现策略逻辑。
        3.可使用buy、sell、clear函数下单，使用count_compute计算相应仓位可购买的股票数量，使用notify打印信息。
        4.可选择重写custom_finally函数进行执行后处理。
        5.在主进程中初始化并调用run执行回测。
    """
    def __init__(self, cash: float, datas: pd.DataFrame, wpath:str, max_num:int=20, save:bool=True, stg_name:str=''):
        """
        :param cash: 本金
        :param datas: 固定格式，DataFrame(index=(date, code), col=['open', 'close', ...], open、close必备)
        :param wpath: 预测收益文件路径，要求为 pd.DataFrame(index=(date, code), col=['prediction'])
        :param max_num: 最大持仓股票数量
        :param save: 是否保存
        """
        super().__init__(cash, datas, save)

        # 设置策略名
        if stg_name == '':
            self.strategy_name = "预测收益率策略"
        else:
            self.strategy_name = stg_name
        self.max_num = max_num
        self.weight:pd.DataFrame = pd.read_csv(wpath, index_col=(0, 1), dtype={'code':str, 'date':str})
        self.stock_name = data_api.get_name()

    def next(self):
        """
        在这里定义你的策略（以下为示例）
        """
        # 打印信息
        self.notify(f"时间 -- {self.date_cur}")

        # 用策略计算出需要操作的标的代码

        ## 1.获取权重
        ret = self.weight.xs(self.date_cur, level='date')
        ret = ret.sort_values(ascending=False, by='prediction').reset_index(drop=False)

        # 2.剔除ST
        st = self.stock_name.loc[self.stock_name[self.date_cur].str.contains('ST', na=False) & self.stock_name[self.date_cur].notna(), '股票代码']
        ret = ret[~ret['code'].isin(st)]

        # 3.剔除无法购买的股票
        ret = ret[ret['code'].isin(self.code_cur)]

        print(ret)

        # 清仓 或使用self.sell函数单笔卖出
        self.clear()

        # 计算购买数量
        counts = []
        w = 1/self.max_num
        for index, row in ret.iterrows():
            code = row['code']
            c = self.count_compute(code, w, 100)
            if c < 100:
                continue
            counts.append({'code': code, 'count': c})
            if len(counts) >= self.max_num:
                break

        # 下单
        for item in counts:
            self.buy(item['code'], 0, item['count'], False)


    def custom_finally(self):
        # 自定义结束处理，程序结束后执行
        pass


if __name__ == '__main__':
    stg_name='pred_TO_ILL_36'
    # 策略初始化
    strategy = StgPred(cash=10000000,
                       datas=data_api.get_monthly_qfq('20240201', '20260201'),
                       wpath=factors.wpath(stg_name), max_num=5, save=False, stg_name=stg_name)

    # 回测执行
    strategy.run()