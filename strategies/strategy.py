import os
import time
from datetime import datetime
import pandas as pd
from abc import ABC, abstractmethod
from typing import final
import matplotlib.pyplot as plt


class Strategy(ABC):
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

    使用说明见示例 StrategyPattern
    """
    def __init__(self, cash: float, datas: pd.DataFrame, save: bool = True):
        """
        :param cash: 本金
        :param datas: 固定格式，DataFrame(index=(date, code), col=['open', 'close', 'high', 'low', 'volume'], open、close必备)
        :param save: 是否保存文件
        """
        # 是否保存运行数据
        self.save = save

        # 资金 —— 资产
        self.cash = cash
        self.fund = 0.0
        self.init_cash = cash

        # 时序量价数据
        self.datas = datas

        # 日期
        self.date_list = self.datas.index.levels[0]
        self.date_cur = None
        self.date_index = None

        # 股票
        self.code_list = self.datas.index.levels[1]
        self.code_cur = None

        # 仓位
        self.position = pd.DataFrame({'pos':0},
                                     index=self.code_list)
        self.position_record = pd.DataFrame({'date':pd.Series(dtype=str),
                                             'code':pd.Series(dtype=str),
                                             'income':pd.Series(dtype=float)})

        # 订单
        self.orders = pd.DataFrame({
            'date': pd.Series(dtype=str),
            'type':pd.Series(dtype=str),
            'limit':pd.Series(dtype=bool),
            'target':pd.Series(dtype=str),
            'price':pd.Series(dtype=float),
            'count':pd.Series(dtype=int),
            'completed':pd.Series(dtype=bool),
            'canceled':pd.Series(dtype=bool),
        })

        # 记录总资产
        self.asset_record = pd.DataFrame({'total':0.0},
                                         index=self.date_list)
        self.total = 0
        self.total_return = 0
        self.annualized_return = 0
        self.max_down = 0.0

        # 策略自身属性
        self.strategy_name = 'Strategy'


    @abstractmethod
    def next(self):
        pass

    @final
    def count_compute(self, target:str, position:float, mini:int=100):
        """
        计算当前资金的 position 能购买多少该股票
        :param target: 标的股票代码
        :param position: 仓位 (范围 [0, 1])
        :param mini: 要是多少的整数倍
        :return:
        """
        if position < 0 or position > 1:
            self.notify("COUNT_COMPUTE ERROR")
            return -1
        key = (self.date_cur, target)
        open_price = self.datas.loc[key, 'open'] if key in self.datas.index else None
        if open_price is None:
            return -1
        return int((self.cash * position) / (open_price * mini)) * mini

    @final
    def buy(self, target:str, price:float, count:int, limit:bool=True):
        """
        设置买单
        :param target:标的股票代码
        :param price: 购买价格（市价单时无效）
        :param count: 购买数量
        :param limit: 是否限价单
        :return:
        """
        self.orders = pd.concat([self.orders, pd.DataFrame({
            'date':self.date_cur,
            'type':['buy'], 'limit':[limit],
            'target':[target], 'price':[price],
            'count':[count], 'completed':[False], 'canceled':[False]})],ignore_index=True)
        self._order_exe()

    @final
    def sell(self, target:str, price:float, count:int, limit:bool=True):
        """
        设置卖单
        :param target:标的股票代码
        :param price: 卖出价格（市价单时无效）
        :param count: 卖出数量
        :param limit: 是否限价单
        :return:
        """
        self.orders = pd.concat([self.orders, pd.DataFrame({
            'date':self.date_cur,
            'type':['sell'], 'limit':[limit],
            'target':[target], 'price':[price],
            'count':[count], 'completed':[False], 'canceled':[False]})],ignore_index=True)
        self._order_exe()

    @final
    def clear(self):
        """
        清仓
        :return:
        """
        for code, row in self.position.iterrows():
            pos = row['pos']
            if pos != 0:
                self.sell(str(code), 0, pos, False)

    @final
    def _order_exe(self, check:bool=False):
        """
        订单执行
        :param check: 是否是循环中的检查
        :return:
        """
        if check:
            orders = self.orders
        else:
            orders = self.orders.tail(1)

        for order_index, row in orders.iterrows():
            if row['completed']: continue
            target = row['target']
            price = row['price']
            count = row['count']
            key = (self.date_cur, target)
            open_price = self.datas.loc[key,'open'] if key in self.datas.index else None
            if open_price is None: continue

            if row['type'] == 'buy':
                if row['limit']:
                    # 限价买单
                    if open_price <= row['price']:
                        if self._buy_exe(target, price, count):
                            self.orders.loc[order_index, 'completed'] = True
                        else:
                            self.orders.loc[order_index, 'completed'] = True
                            self.orders.loc[order_index, 'canceled'] = True
                else:
                    # 市价买单
                    price = open_price
                    if self._buy_exe(target, price, count):
                        self.orders.loc[order_index, 'price'] = price
                        self.orders.loc[order_index, 'completed'] = True
                    else:
                        self.orders.loc[order_index, 'completed'] = True
                        self.orders.loc[order_index, 'canceled'] = True
            elif row['type'] == 'sell':
                if row['limit']:
                    # 限价卖单
                    if open_price >= row['price']:
                        if self._sell_exe(target, price, count):
                            self.orders.loc[order_index, 'completed'] = True
                        else:
                            self.orders.loc[order_index, 'completed'] = True
                            self.orders.loc[order_index, 'canceled'] = True
                else:
                    # 市价卖单
                    price = open_price
                    if self._sell_exe(target, price, count):
                        self.orders.loc[order_index, 'price'] = price
                        self.orders.loc[order_index, 'completed'] = True
                    else:
                        self.orders.loc[order_index, 'completed'] = True
                        self.orders.loc[order_index, 'canceled'] = True

    @final
    def _buy_exe(self, target:str, price:float, count:int)->bool:
        if count <= 0 or price <= 0:
            self.notify(f"BUY : 设置错误 {target} {price:.2f} * {count}")
            return False
        if self.cash < price*count:
            self.notify(f"BUY : 资金不足 {target} {price:.2f} * {count} -- cash {self.cash:.2f}")
            return False

        self.cash -= price * count
        self.position.loc[target,'pos'] += count
        self.notify(f"BUY : {target} {price:.2f} * {count} -- cash {self.cash:.2f}")
        return True

    @final
    def _sell_exe(self, target:str, price:float, count:int)->bool:
        if count <= 0 or price <= 0:
            self.notify(f"SELL: 设置错误 {target} {price:.2f} * {count}")
            return False
        if self.position.loc[target,'pos'] < count:
            self.notify(f"SELL: 资产不足")
            return False

        self.cash += price * count
        self.position.loc[target,'pos'] -= count
        self.notify(f"SELL: {target} {price:.2f} * {count} -- cash {self.cash:.2f}")
        return True

    @final
    def _fund_update(self):
        """
        更新当前资产价值 -- 使用close计算
        """
        fund = 0.0
        for code, row in self.position.iterrows():
            key = (self.date_cur, code)
            close_price = self.datas.loc[key, 'close'] if key in self.datas.index else 0
            pos = row['pos']
            fund += pos * close_price
        self.fund = fund

    @final
    def _cycle_record(self):
        """
        在循环中记录参数
        :return:
        """
        # 总资产记录
        self.asset_record.loc[self.date_cur, 'total'] = self.cash + self.fund

        # 持仓记录
        if self.date_cur != self.date_list[0]:
            for code, row in self.position.iterrows():
                key = (self.date_cur, code)
                key_1 = (self.date_list[self.date_index-1], code)
                close_price = self.datas.loc[key, 'close'] if key in self.datas.index else 0
                open_price = self.datas.loc[key, 'open'] if key in self.datas.index else 0
                # close_price_1 = self.datas.loc[key_1, 'close'] if key_1 in self.datas.index else 0
                pos = row['pos']
                if pos != 0:
                    position_df = pd.DataFrame({
                        'date': [self.date_cur],
                        'code': [code],
                        'income': [f"{(close_price/open_price-1) if open_price != 0 else None}"],
                        # 'income': [f"{(close_price/close_price_1-1) if close_price_1 != 0 else None}"],
                    })
                    self.position_record = pd.concat([self.position_record, position_df], ignore_index=True)
        else: # 第一个 date
            for code, row in self.position.iterrows():
                key = (self.date_cur, code)
                close_price = self.datas.loc[key, 'close'] if key in self.datas.index else 0
                open_price = self.datas.loc[key, 'open'] if key in self.datas.index else 0
                pos = row['pos']
                if pos != 0:
                    position_df = pd.DataFrame({
                        'date': [self.date_cur],
                        'code': [code],
                        'income': [f"{(close_price / open_price - 1) if open_price != 0 else None}"],
                    })
                    self.position_record = pd.concat([self.position_record, position_df], ignore_index=True)

    @final
    def _summarize(self):
        """
        打印总结信息
        :return:
        """
        # 打印所有订单
        print(self.orders)

        # 打印当前仓位
        print(self.position)

        # 计算总资产、总收益率、年化收益率
        total = self.cash+self.fund
        self.total = total
        total_return = (total / self.init_cash - 1)*100 if self.init_cash > 0 else 0

        start_date = self.date_list[0]
        end_date = self.date_list[-1]

        if len(start_date) == 6:
            start_date = start_date + '01'
        if len(end_date) == 6:
            end_date = end_date + '01'

        # 转换为datetime对象
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y%m%d')
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y%m%d')

        # 计算投资年数
        days = (end_date - start_date).days
        years = days / 365.0

        # 计算年化收益率
        if years > 0:
            annualized_return = (1 + total_return/100.0) ** (1 / years) - 1
            annualized_return *=100
        else:
            annualized_return = 0


        self.total_return = total_return
        self.annualized_return = annualized_return

        # 计算最大回撤
        self.max_down = 0.0
        max_asset = self.init_cash
        for index, row in self.asset_record.iterrows():
            asset = row['total']
            if asset > max_asset:
                max_asset = asset
            if (max_asset-asset)/max_asset > self.max_down:
                self.max_down = (max_asset-asset)/max_asset

            # print(self.max_down)

        self.notify(f"Initial {self.init_cash:.2f} Cash {self.cash:.2f}, Fund {self.fund:.2f}, Total {total:.2f}")
        self.notify(f"Total_return {total_return:.2f}% Annualized_return {annualized_return:.2f}% Max_down {self.max_down*100:.2f}%")

    @final
    def _plot(self):
        """
        绘图
        :return:
        """
        plt.figure()
        plt.plot(self.date_list, self.asset_record.loc[:, 'total'], color='red')
        plt.plot(self.date_list, self.asset_record.loc[:, 'total'], color='red')
        plt.xticks(size=5, rotation=90)

        plt.tight_layout()
        plt.show()

    @final
    def _save(self):
        """
        保存运行记录
        :return:
        """
        # 获取时间戳 和 当前时间字符串
        timestamp = int(time.time())
        dt = datetime.fromtimestamp(timestamp)
        dt_str = dt.strftime("%Y%m%d_%H_%M_%S")

        # 创建目录
        dir_name = f"./record/{self.strategy_name}_{dt_str}_{str(timestamp)}"
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        # 创建txt（记录策略相关说明）
        file_path = os.path.join(dir_name, "readme.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"{self.strategy_name}\n")
            f.write(f"运行时间：{dt_str}\n")
            f.write(f"数据：{self.date_list[0]}-{self.date_list[-1]}\n")
            f.write(f"初始资金 {self.init_cash:.2f} 最终资金 {self.total:.2f}\n")
            f.write(f"总收益 {self.total_return:.2f}% 年化收益 {self.annualized_return:.2f}% 最大回撤{self.max_down*100:.2f}%\n")
            f.write(f"描述：\n")

        # 保存订单记录
        self.orders.to_csv(dir_name+'/order_record.csv', index=False)

        # 保存盈利曲线
        income_record = self.asset_record
        if self.init_cash > 0:
            income_record['total'] = income_record['total']/self.init_cash
            income_record = income_record.rename(columns={'total':'income'})
            income_record.to_csv(dir_name+'/income_record.csv', index=True)

        # 保存持仓记录
        self.position_record.to_csv(dir_name+'/position_record.csv', index=False)


    def custom_finally(self):
        """
        自定义结束函数
        :return:
        """
        pass

    @final
    def run(self):
        # 遍历时间
        self.date_index = 0
        for index, date in enumerate(self.date_list):
            # 更新当期时间
            self.date_index = index
            self.date_cur = date

            # 更新当期股票
            self.code_cur = self.datas.xs(self.date_cur, level='date').index.tolist()
            self.code_cur = pd.Series(self.code_cur, name='code')

            # 提示
            self.notify(f"\nDATE -- {self.date_cur}")

            # 运行逻辑
            self.next()

            # 执行订单
            self._order_exe(check=True)

            # 更新资产情况
            self._fund_update()

            # 记录和打印
            self._cycle_record()
            self.notify(f"Cash {self.cash:.2f}, Fund {self.fund:.2f}, Total {(self.cash+self.fund):.2f}")
        self._summarize()
        if self.save:
            self._save()
        self.custom_finally()
        self._plot()

    @staticmethod
    @final
    def notify(information: str):
        print(information)
