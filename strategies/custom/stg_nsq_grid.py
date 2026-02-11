"""
NSQ 网格策略（单标的：code 只有 'nsq'）
- 跌一个网格买入 n（按总资产比例换算为金额）
- 涨一个网格卖出 n
- 使用 open 作为成交价（与你框架一致）
- 参数集中在 PARAMS 区域
"""
import pandas as pd
from strategies.strategy import Strategy
from data_api import nsq_data


class StgNsqGrid(Strategy):
    """
    NSQ 简单网格交易策略（单标的：'nsq'）
    """

    # =========================
    # PARAMS：参数集中配置区
    # =========================
    PARAMS = {
        # 网格间距：百分比（例如 0.01 = 1%）
        "grid_pct": 0.01,

        # 每次触发买/卖的“交易金额占比”（按当期总资产计算）
        # 例如 0.02 = 每次买/卖约等于总资产的 2%
        "trade_value_ratio": 0.02,

        # 初始建仓比例（第一次运行时把仓位做到账户总资产的该比例）
        "init_pos_ratio": 0.80,

        # 仓位上下限（仓位=持仓市值/总资产），网格交易不会突破该范围
        "min_pos_ratio": 0.30,
        "max_pos_ratio": 1.00,

        # 每次下单的最小交易数量（美股/指数类通常 1；A股可设 100）
        "lot_size": 1,

        # 是否用“最新成交价”更新网格锚点（True 更常见）
        "update_anchor_on_trade": True,
    }

    def __init__(self, cash: float, datas: pd.DataFrame, save: bool = True):
        super().__init__(cash, datas, save)
        self.strategy_name = "NSQ_简单网格"

        # 网格锚点价格：用于判断涨/跌一个网格
        self.grid_anchor = None

        # 单标的
        self.code = "nsq"

    # --------- 工具函数 ---------
    def _get_bar(self):
        """取当前日期 nsq 的 open/close"""
        bar = self.datas.loc[(self.date_cur, self.code)]
        # bar 可能是 Series 或 1 行 DataFrame
        if isinstance(bar, pd.DataFrame):
            bar = bar.iloc[0]
        return float(bar["open"]), float(bar["close"])

    def _total_equity(self):
        """当前总资产（用框架中的 cash + fund，fund 为上一轮 close 更新后的持仓市值）"""
        return float(self.cash + self.fund)

    def _pos_count(self):
        """当前持仓数量（手数/股数）"""
        if self.code not in self.position.index:
            return 0
        v = self.position.loc[self.code, "pos"]
        try:
            return int(v)
        except Exception:
            return 0

    def _pos_ratio(self, price: float):
        """当前仓位比例（按给定价格估算）"""
        total = self._total_equity()
        if total <= 0:
            return 0.0
        pos_value = self._pos_count() * price
        return float(pos_value / total)

    def _round_lot(self, count: int):
        lot = int(self.PARAMS["lot_size"])
        if lot <= 1:
            return int(count)
        return int(count // lot * lot)

    def _count_by_value(self, price: float, value: float):
        """把交易金额 value 换算成交易数量，并按 lot_size 向下取整"""
        if price <= 0 or value <= 0:
            return 0
        cnt = int(value // price)
        return self._round_lot(cnt)

    # --------- 策略主体 ---------
    def next(self):
        open_px, close_px = self._get_bar()
        total = self._total_equity()

        # 1) 初始化：第一次进来先建核心仓，并设置锚点
        if self.grid_anchor is None:
            target_ratio = float(self.PARAMS["init_pos_ratio"])
            target_ratio = max(0.0, min(1.0, target_ratio))

            target_value = total * target_ratio
            cur_value = self._pos_count() * open_px
            need_value = max(0.0, target_value - cur_value)

            buy_cnt = self._count_by_value(open_px, min(need_value, self.cash))
            if buy_cnt > 0:
                self.buy(self.code, 0, buy_cnt, False)
                self.notify(
                    f"[INIT] {self.date_cur} open={open_px:.2f} 目标仓位={target_ratio:.0%} 买入={buy_cnt}"
                )

            self.grid_anchor = open_px
            return

        # 2) 计算网格触发线
        g = float(self.PARAMS["grid_pct"])
        up_line = self.grid_anchor * (1.0 + g)
        down_line = self.grid_anchor * (1.0 - g)

        # 3) 每次交易金额（按总资产比例）
        trade_value = total * float(self.PARAMS["trade_value_ratio"])

        # 4) 仓位约束
        min_r = float(self.PARAMS["min_pos_ratio"])
        max_r = float(self.PARAMS["max_pos_ratio"])
        cur_r = self._pos_ratio(open_px)

        # 5) 触发卖出：涨一个网格
        if open_px >= up_line and cur_r > min_r + 1e-9:
            # 允许卖出的最大金额，防止卖到低于 min_pos_ratio
            max_sell_value = max(0.0, (cur_r - min_r) * total)
            sell_value = min(trade_value, max_sell_value)

            sell_cnt = self._count_by_value(open_px, sell_value)
            sell_cnt = min(sell_cnt, self._pos_count())

            if sell_cnt > 0:
                self.sell(self.code, 0, sell_cnt, False)
                self.notify(
                    f"[SELL] {self.date_cur} open={open_px:.2f} anchor={self.grid_anchor:.2f} "
                    f"触发>= {up_line:.2f} 卖出={sell_cnt} 仓位≈{cur_r:.1%}"
                )
                if self.PARAMS["update_anchor_on_trade"]:
                    self.grid_anchor = open_px
            return

        # 6) 触发买入：跌一个网格
        if open_px <= down_line and cur_r < max_r - 1e-9:
            # 允许买入的最大金额，防止买到高于 max_pos_ratio
            max_buy_value = max(0.0, (max_r - cur_r) * total)
            buy_value = min(trade_value, max_buy_value, self.cash)

            buy_cnt = self._count_by_value(open_px, buy_value)

            if buy_cnt > 0:
                self.buy(self.code, 0, buy_cnt, False)
                self.notify(
                    f"[BUY]  {self.date_cur} open={open_px:.2f} anchor={self.grid_anchor:.2f} "
                    f"触发<= {down_line:.2f} 买入={buy_cnt} 仓位≈{cur_r:.1%}"
                )
                if self.PARAMS["update_anchor_on_trade"]:
                    self.grid_anchor = open_px
            return

        # 7) 未触发：可选择打印少量信息（默认不刷屏）
        # self.notify(f"[HOLD] {self.date_cur} open={open_px:.2f} anchor={self.grid_anchor:.2f}")

    def custom_finally(self):
        # 如需输出自定义统计可在此实现
        pass

from tools.datapath import data_path
import os
def get_TSLA(start_time:str='19900101', end_time:str='20991231'):
    """
    获取纳斯达克指数月线数据
    :param start_time:
    :param end_time:
    :param attr:
    :return:
    """

    datas = pd.DataFrame({
        'date': pd.Series(dtype='str'),
        'open': pd.Series(dtype='float'),
        'close': pd.Series(dtype='float')
    })

    file_path = data_path + 'TSLA.csv'
    if not os.path.exists(file_path):
        return None
    data = pd.read_csv(file_path).loc[:,  ['date','open','close']]
    data['date'] = pd.to_datetime(data['date'], format='%m/%d/%Y').dt.strftime('%Y%m%d')
    data = data.loc[(data['date'] >= start_time) & (data['date'] <= end_time)]

    datas = pd.concat([datas, data], ignore_index=True)
    datas['code'] = 'nsq'  # 添加date列，所有行赋值为'all'
    datas = datas.set_index(['date', 'code'])  # 将date设为索引，保持原有索引
    return datas



if __name__ == "__main__":
    # 数据接口：datas=get_nsq('20161201', '20260201')
    datas = get_TSLA("20161201", "20260201")

    print(datas)

    stg = StgNsqGrid(
        cash=10_000_000,
        datas=datas,
        save=False,
    )
    stg.run()

