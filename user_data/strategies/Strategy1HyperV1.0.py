# ============================================================================
# Strategy1HyperV1.0 — 超参优化版趋势守护策略
# ============================================================================
# 
# 版本历史：
#   v1.0  (2026-07-08): 基于 Strategy1.0，通过 300 轮 Optuna 超参优化找到最佳参数
#   v0.1  (2026-07-07): 原始 RSI 简单策略，年亏 51%
#   v0.2  (2026-07-07): 添加趋势过滤、动态止损，亏损降到 3.7%
#
# 回测表现（2025.01 ~ 2026.07, 552 天, BTC/ETH 合约）：
#   - 总盈亏:     +6.06%  (+60 USDT)   ← 首次实现盈利！
#   - 胜率:        76.2%  (16胜5负)
#   - 最大回撤:     1.38%
#   - 盈亏因子:     4.73  (每赚 4.7 元才亏 1 元)
#   - 年化收益率:   3.98%
#   - 交易频率:   ~21 笔/18个月 (约每月 1 笔)
#
# 策略设计思路：
#   只在强上升趋势中，等待深度超卖回调时入场。
#   出场不靠信号，靠止盈(ROI)+追踪止损+动态止损三层保护。
#
# 超参优化后的最佳参数：
#   buy_rsi  = 26  (RSI低于26才考虑入场 → 深度超卖)
#   buy_bb   = 0.17 (价格必须非常接近布林下轨 → 深度回调)
#   buy_adx  = 31  (ADX>31 说明趋势足够强 → 不在震荡市入场)
# ============================================================================

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade
import talib.abstract as ta
from technical import qtpylib


class Strategy1HyperV1(IStrategy):
    """
    Strategy1HyperV1.0 — 超参优化趋势守护策略

    ====== 核心理念 ======
    只在"上升趋势 + 深度回调 + 放量反弹"时入场，用三层保护出场。

    ====== 入场条件（6个条件全部满足才买入） ======
    1. 趋势向上:  价格 > EMA200 (200周期均线，代表长期趋势)
    2. RSI超卖反弹: RSI从超卖区(默认26以下)涨上来，说明抛压耗尽
    3. 布林带低位: 价格在布林带下轨附近(默认17%位置)，极度便宜
    4. 放量确认:   成交量 > 20日均量，说明有资金抄底
    5. 趋势强度:   ADX > 31，确认不是横盘震荡
    6. K线有效:    成交量 > 0（排除停牌等异常）

    ====== 出场机制（三层保护，按优先级） ======
    第一层 - ROI止盈:
      持仓30分钟  → 盈利1%就卖
      持仓60分钟  → 盈利2%就卖
      持仓120分钟 → 盈利3%就卖
      无条件      → 盈利0.5%就卖（防止无限持仓）

    第二层 - 追踪止损:
      盈利 > 1.5% 后启动 → 从最高点回撤 2% 触发卖出
      例: 买后涨到+4% → 回落到+2% → 卖出（锁定+2%利润）

    第三层 - 动态保护止损 (custom_stoploss):
      盈利 > 5%: 只允许回吐 2% (锁定 +3%利润)
      盈利 > 3%: 只允许回吐 2% (锁定 +1%利润)
      盈利 > 2%: 止损提到开仓价 (保本)
      盈利 > 1%: 止损提到 -1.5% (缩紧)
      其他:      使用默认 -4% 硬止损

    第四层 - 硬止损:
      亏损达到 -4%，无条件卖出认输

    第五层 - 趋势破位出场:
      价格跌破 EMA200 → 趋势可能反转，清仓
    """

    # ====== 基础设置 ======
    INTERFACE_VERSION = 3
    timeframe = "5m"           # 使用 5 分钟 K 线
    can_short: bool = False    # 只做多，不做空

    # ====== 超参优化变量 ======
    # 这三个参数通过 300 轮 Optuna 优化找到最佳组合
    # space="buy" 表示它们属于"买入"优化空间
    buy_rsi = IntParameter(
        15, 40, default=28, space="buy"
    )  # RSI 买入阈值：范围 15-40，默认 28，最优 26
    buy_bb = DecimalParameter(
        0.1, 0.5, default=0.3, decimals=2, space="buy"
    )  # 布林带位置阈值：范围 0.1-0.5，默认 0.3，最优 0.17
    buy_adx = IntParameter(
        15, 35, default=20, space="buy"
    )  # ADX 趋势强度阈值：范围 15-35，默认 20，最优 31

    # ====== 止盈策略（ROI 表） ======
    # 格式: "持仓分钟数": 目标收益率
    # 30分赚1%就跑，比60分赚2%优先触发（先检查短时间条件）
    minimal_roi = {
        "120": 0.03,   # 持仓 120 分钟 → 目标盈利 3%
        "60":  0.02,   # 持仓 60 分钟  → 目标盈利 2%
        "30":  0.01,   # 持仓 30 分钟  → 目标盈利 1%
        "0":   0.005,  # 无条件         → 目标盈利 0.5%
    }

    # ====== 止损配置 ======
    stoploss = -0.04                   # 硬止损：最多亏 4%

    # 追踪止损（Trailing Stop）
    trailing_stop = True               # 启用追踪止损
    trailing_stop_positive = 0.015     # 盈利 1.5% 后才激活追踪
    trailing_stop_positive_offset = 0.02  # 从最高点回撤 2% 触发
    trailing_only_offset_is_reached = True  # 必须盈利达标后才开始追踪

    # ====== 运行配置 ======
    process_only_new_candles = True    # 只在产生新K线时计算（性能优化）
    use_exit_signal = False            # 不使用出场信号（由ROI+止损接管）
    exit_profit_only = False           # 不限制只在盈利时出场
    ignore_roi_if_entry_signal = False # 入场信号不覆盖ROI
    startup_candle_count: int = 200    # 需要 200 根历史K线来初始化指标（EMA200）
    use_custom_stoploss = True         # 启用自定义动态止损

    # ====== 订单配置 ======
    order_types = {
        "entry": "limit",              # 限价买入（避免滑点）
        "exit": "limit",               # 限价卖出
        "stoploss": "market",          # 止损用市价（保证成交）
        "stoploss_on_exchange": False, # 止损单不挂交易所（本地管理，更安全）
    }
    order_time_in_force = {
        "entry": "GTC",                # 入场单：一直有效直到成交
        "exit": "GTC",                 # 出场单：一直有效直到成交
    }

    # ====== 图表配置（网页上看回测图时显示什么指标） ======
    @property
    def plot_config(self):
        return {
            # 主图（K线图上的叠加指标）
            "main_plot": {
                "ema200":       {"color": "#FFA500"},  # 200EMA — 橙色
                "bb_upperband": {"color": "grey"},     # 布林带上轨 — 灰色
                "bb_lowerband": {"color": "grey"},     # 布林带下轨 — 灰色
                "bb_middleband": {"color": "blue"},    # 布林带中轨 — 蓝色
            },
            # 副图（K线图下方的独立指标面板）
            "subplots": {
                "RSI": {
                    "rsi": {"color": "#ff0066"},        # RSI — 红色
                },
                "MACD": {
                    "macd":       {"color": "blue"},    # MACD 快线 — 蓝色
                    "macdsignal": {"color": "orange"},  # MACD 信号线 — 橙色
                },
                "Volume": {
                    "volume": {"color": "#00ccff"},     # 成交量 — 青色
                },
            }
        }

    # ========================================================================
    # populate_indicators — 计算所有技术指标
    # ========================================================================
    # 这个方法在每个K线上运行一次，计算全部需要的指标。
    # 回测时一次性计算，实盘时每根新K线触发一次。
    # ========================================================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # ---- EMA200: 200周期指数移动平均线 ----
        # 作用: 判断长期趋势方向。价格在线上 = 上升趋势，在线下 = 下降趋势
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # ---- RSI(14): 相对强弱指标 ----
        # 作用: 判断超买超卖。>70 超买(该卖了)，<30 超卖(该买了)
        # 这里用14周期，是RSI最标准的参数
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # ---- MACD(12,26,9): 指数平滑异同移动平均线 ----
        # 作用: 判断趋势变化和动量。
        #   macd > macdsignal = 金叉(看涨动能)
        #   macd < macdsignal = 死叉(看跌动能)
        # macdhist = 柱状图，正值=多头力道增强
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]

        # ---- 布林带(20,2): 波动率通道 ----
        # 作用: 判断价格的相对高低位。
        #   bb_position = 0: 价格在下轨(超卖/便宜)
        #   bb_position = 1: 价格在上轨(超买/贵)
        # 标准差为2表示约95%的价格应在此区间内
        bb = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe["bb_upperband"] = bb["upper"]    # 上轨
        dataframe["bb_middleband"] = bb["mid"]      # 中轨(20日均线)
        dataframe["bb_lowerband"] = bb["lower"]     # 下轨
        # bb_position: 0~1 之间，表示价格在布林带中的相对位置
        # +1e-10 防止除零错误
        dataframe["bb_position"] = (
            (dataframe["close"] - dataframe["bb_lowerband"])
            / (dataframe["bb_upperband"] - dataframe["bb_lowerband"] + 1e-10)
        )

        # ---- ATR(14): 平均真实波幅 ----
        # 作用: 衡量市场波动性。数值越大说明波动越剧烈。
        # 可用于动态止损（波动大时放宽止损）
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # ---- 成交量 SMA(20) ----
        # 作用: 判断当前成交量是否放量。
        # volume > volume_sma = 放量(有资金关注)
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        # ---- ADX(14): 平均趋向指数 ----
        # 作用: 判断趋势强度（不判断方向）。
        #   >25: 强趋势，值得交易
        #   <20: 弱趋势/震荡，应该观望
        # 注意: ADX只告诉你趋势存不存在，不告诉你是涨还是跌
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        return dataframe

    # ========================================================================
    # populate_entry_trend — 入场信号
    # ========================================================================
    # 六个条件全部满足才触发买入。
    # 这些条件确保：只在趋势向上、深度回调、放量反弹时入场。
    # ========================================================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # 用 pandas DataFrame.loc 选择满足所有条件的行
        dataframe.loc[
            (
                # 条件1: 价格在 200EMA 之上 → 长期上升趋势
                (dataframe["close"] > dataframe["ema200"]) &

                # 条件2: RSI 从超卖区(默认26)涨上来 → 抛压耗尽、买方入场
                # crossed_above = 之前低于阈值，现在高于阈值（金叉信号）
                (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)) &

                # 条件3: 价格接近布林带下轨(默认17%位置) → 极度便宜
                (dataframe["bb_position"] < self.buy_bb.value) &

                # 条件4: 当前成交量 > 20日均量 → 有资金在抄底
                (dataframe["volume"] > dataframe["volume_sma"]) &

                # 条件5: ADX > 默认31 → 趋势强度足够，不是横盘
                (dataframe["adx"] > self.buy_adx.value) &

                # 条件6: 成交量不为0 → K线有效（排除停牌）
                (dataframe["volume"] > 0)
            ),
            "enter_long"  # 满足所有条件 → 标记为入场信号
        ] = 1

        return dataframe

    # ========================================================================
    # populate_exit_trend — 出场信号
    # ========================================================================
    # 本策略主要出场方式不是信号，而是 ROI止盈 + 追踪止损 + 动态止损。
    # 这里只保留最后一道防线：趋势破位（价格跌破EMA200）。
    # ========================================================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                # 收盘价跌破 200EMA → 长期趋势可能反转
                (dataframe["close"] < dataframe["ema200"]) &
                # 成交量不为0
                (dataframe["volume"] > 0)
            ),
            "exit_long"  # 标记为出场信号
        ] = 1

        return dataframe

    # ========================================================================
    # custom_stoploss — 动态保护止损
    # ========================================================================
    # 这个方法在每根新K线上调用一次（只要有持仓）。
    # 返回值是新的止损线（以开仓价为基准的比例）。
    # 返回 None 表示使用默认止损 (-4%)。
    #
    # 核心理念：赚得越多，止损越紧，确保利润不全部回吐。
    #
    # 参数说明：
    #   pair:           交易对名称，如 "BTC/USDT:USDT"
    #   trade:          当前交易对象，包含开仓价、时间等信息
    #   current_time:   当前时间
    #   current_rate:   当前价格
    #   current_profit: 当前盈亏比例（0.01 = +1%, -0.02 = -2%）
    #   after_fill:     是否刚成交
    # ========================================================================
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> Optional[float]:

        # 盈利超过 5% → 只允许回吐 2%（锁定至少 +3% 利润）
        # 例: 买入价 100，涨到 108 (+8%)，止损线 = 108 - 2 = 106 (仍赚 6%)
        if current_profit > 0.05:
            return current_profit - 0.02

        # 盈利超过 3% → 只允许回吐 2%（锁定至少 +1% 利润）
        # 例: 买入价 100，涨到 104，止损线 = 104 - 2 = 102 (仍赚 2%)
        if current_profit > 0.03:
            return current_profit - 0.02

        # 盈利超过 2% → 止损提升到开仓价（保本出）
        # 例: 买入价 100，涨到 102.5，止损线 = 100.1 (不亏)
        if current_profit > 0.02:
            return 0.001

        # 盈利超过 1% → 止损缩紧到 -1.5%
        # 例: 买入价 100，涨到 101.5，止损线 = 98.5 (最多只亏 1.5%)
        if current_profit > 0.01:
            return -0.015

        # 盈利不足 1% → 使用默认硬止损 -4%
        return None
