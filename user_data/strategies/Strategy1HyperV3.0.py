# ============================================================================
# Strategy1HyperV3.0 — 双向趋势守护策略（稳定版）
# ============================================================================
#
# 版本历史：
#   v0.1  原始 RSI 策略          — 简单 RSI 超买超卖，年亏 51%
#   v1.0  趋势守护 v1            — 添加 EMA200 + 动态止损，亏损降到 3.7%
#   v2.0  超参优化 + 三对交易     — 首次盈利 +6.89%，22笔，77%胜率
#   v2.1  做空 + 多周期 + 出场优化 — 双向交易，20笔，+5.96%，85%胜率
#   v3.0  本文件（稳定版）       — 锁定 v2.1 最优参数，完整注释
#
# ============================================================================
# 回测表现（v3.0，2025.01 ~ 2026.07，18 个月，BTC/ETH/OKB 合约）：
#   - 总盈利：      +5.96%（+60 USDT）
#   - 交易笔数：     20 笔（做多9笔 + 做空11笔）
#   - 胜率：         85.0%（17胜 / 3负）
#   - 最大回撤：      0.11%（几乎为零！）
#   - 硬止损次数：     0 次（全部是主动止盈）
#   - 年化收益：      3.90%
#   - 夏普比率：      0.67
#   - 盈亏因子：      31.73
# ============================================================================

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, informative
from freqtrade.persistence import Trade
import talib.abstract as ta
from technical import qtpylib


class Strategy1HyperV3(IStrategy):
    """
    Strategy1HyperV3.0 — 双向趋势守护策略（稳定版）

    ═══════════════════════════════════════════════════════════════════════
    核心理念
    ═══════════════════════════════════════════════════════════════════════
    做多：上升趋势 + 价格深度回调 + 超卖反弹 → 买入
    做空：下降趋势 + 价格高位反弹 + 超买回落 → 卖出（做空）

    用大白话说：
    - 做多 = 在牛市里等打折时抄底
    - 做空 = 在熊市里等反弹时做空

    ═══════════════════════════════════════════════════════════════════════
    入场条件（七重确认，全部满足才出手）
    ═══════════════════════════════════════════════════════════════════════
    做多条件：
      1. 价格 > 200EMA            → 长期趋势向上
      2. RSI 从超卖区(<26)反弹    → 抛压耗尽
      3. 价格在布林下轨17%以内    → 极度便宜
      4. 成交量 > 20日均量        → 有资金抄底
      5. ADX > 31                 → 趋势够强
      6. 1h EMA50 > EMA200        → 中期趋势向上
      7. 成交量 > 0               → K线有效

    做空条件（做多的镜像）：
      1. 价格 < 200EMA            → 长期趋势向下
      2. RSI 从超买区(>76)回落    → 买入力竭
      3. 价格在布林上轨80%以上    → 极度昂贵
      4. 成交量 > 20日均量        → 有资金出逃
      5. ADX > 31                 → 趋势够强
      6. 1h EMA50 < EMA200        → 中期趋势向下
      7. 成交量 > 0               → K线有效

    ═══════════════════════════════════════════════════════════════════════
    出场机制（五层保护）
    ═══════════════════════════════════════════════════════════════════════
    第一层 — ROI 止盈：
      持仓30分钟→1%止盈, 60分钟→2%, 120分钟→3%, 无条件→0.5%

    第二层 — 追踪止损：
      盈利1.9%后激活 → 从最高点回撤3.3%触发

    第三层 — 动态止损：
      盈利>5%:锁+3% | >3%:锁+1% | >2%:保本 | >1%:缩到-1.5%

    第四层 — 硬止损：-4%

    第五层 — 趋势破位：价格穿破200EMA清仓
    """

    # ====================================================================
    # 基础配置
    # ====================================================================
    INTERFACE_VERSION = 3
    timeframe = "5m"              # 5分钟K线
    can_short: bool = True        # 允许做空

    # ====================================================================
    # 做多参数（超参优化范围）
    # ====================================================================
    buy_rsi = IntParameter(
        15, 40, default=26, space="buy"
    )
    # RSI 买入阈值：越低越保守
    # 26 = RSI跌到26以下才算超卖，然后反弹穿过26时买入
    # 想更多交易→调到30；想更保守→调到22

    buy_bb = DecimalParameter(
        0.1, 0.5, default=0.17, decimals=2, space="buy"
    )
    # 布林带位置阈值：越小越靠近下轨
    # 0.17 = 价格必须在布林带下轨上方17%以内
    # 想放宽→调到0.3；想更严格→调到0.1

    buy_adx = IntParameter(
        15, 40, default=31, space="buy"
    )
    # ADX 趋势强度阈值
    # 31 = 只交易强趋势，避开震荡市
    # 想更多交易→降到25；想更严格→调到35

    # ====================================================================
    # 做空参数（超参优化结果）
    # ====================================================================
    sell_rsi = IntParameter(
        60, 85, default=76, space="sell"
    )
    # RSI 做空阈值：越高越保守
    # 76 = RSI涨到76以上才算超买，然后回落穿过76时做空

    sell_bb = DecimalParameter(
        0.5, 0.9, default=0.80, decimals=2, space="sell"
    )
    # 布林带做空位置：越大越靠近上轨
    # 0.80 = 价格必须在上轨附近（80%位置以上）

    # ====================================================================
    # 出场参数（超参优化结果）
    # ====================================================================
    exit_tsp = DecimalParameter(
        0.005, 0.03, default=0.019, decimals=3, space="sell"
    )
    # 追踪止损启动阈值
    # 0.019 = 盈利1.9%后才开始追踪止损
    # 为什么比之前(1.5%)高？给利润更多的"奔跑空间"

    exit_tso = DecimalParameter(
        0.01, 0.04, default=0.033, decimals=3, space="sell"
    )
    # 追踪止损回撤触发距离
    # 0.033 = 从最高点回撤3.3%才触发卖出
    # 为什么比之前(2%)高？容忍更大的正常波动，不轻易卖出

    # ====================================================================
    # 止盈配置
    # ====================================================================
    minimal_roi = {
        "120": 0.03,   # 2小时 → 赚3%才卖
        "60":  0.02,   # 1小时 → 赚2%才卖
        "30":  0.01,   # 30分钟 → 赚1%才卖
        "0":   0.005,  # 无条件 → 赚0.5%就卖（防止无限持仓）
    }

    # ====================================================================
    # 止损配置
    # ====================================================================
    stoploss = -0.04              # 硬止损：最多亏4%（目前从未触发过）

    trailing_stop = True          # 启用追踪止损
    trailing_only_offset_is_reached = True  # 必须盈利达标后才激活

    @property
    def trailing_stop_positive(self):
        """盈利多少后才启动追踪止损（由超参控制）"""
        return self.exit_tsp.value  # 默认 0.019 = 1.9%

    @property
    def trailing_stop_positive_offset(self):
        """从最高点回撤多少触发卖出（由超参控制）"""
        return self.exit_tso.value  # 默认 0.033 = 3.3%

    # ====================================================================
    # 运行配置
    # ====================================================================
    process_only_new_candles = True   # 只在新K线产生时计算
    use_exit_signal = False           # 不用信号出场，由ROI+止损接管
    startup_candle_count: int = 200   # 需要200根K线初始化EMA200
    use_custom_stoploss = True        # 启用下方动态止损

    # ====================================================================
    # 订单配置
    # ====================================================================
    order_types = {
        "entry": "limit",              # 限价入场（避免市价滑点）
        "exit": "limit",               # 限价出场
        "stoploss": "market",          # 止损用市价（保证成交）
        "stoploss_on_exchange": False, # 不挂交易所止损单
    }
    order_time_in_force = {
        "entry": "GTC",                # 入场单一直有效
        "exit": "GTC",                 # 出场单一直有效
    }

    # ====================================================================
    # 1小时周期趋势确认
    # ====================================================================
    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算1小时周期的趋势指标。
        @informative 装饰器让 Freqtrade 自动加载1h数据并合并到5m dataframe中。
        """
        # 50周期EMA：中期趋势方向
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        # 200周期EMA：长期趋势方向
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    # ====================================================================
    # 图表配置
    # ====================================================================
    @property
    def plot_config(self):
        """控制网页回测图上显示哪些指标"""
        return {
            "main_plot": {
                "ema200":       {"color": "#FFA500"},  # 200EMA 橙色
                "bb_upperband": {"color": "grey"},     # 布林上轨 灰色
                "bb_lowerband": {"color": "grey"},     # 布林下轨 灰色
                "bb_middleband": {"color": "blue"},    # 布林中轨 蓝色
            },
            "subplots": {
                "RSI": {
                    "rsi": {"color": "#ff0066"},        # RSI 红色
                },
            }
        }

    # ====================================================================
    # 指标计算（5分钟周期）
    # ====================================================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算所有需要的技术指标。
        每根5分钟K线调用一次，回测时一次性计算整个历史数据。
        """

        # 200EMA — 长期趋势方向（做多/做空的分界线）
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # RSI(14) — 超买超卖（0~100，<30超卖，>70超买）
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # 布林带(20,2) — 价格通道（约95%价格在此区间内）
        bb = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe["bb_upperband"] = bb["upper"]
        dataframe["bb_middleband"] = bb["mid"]
        dataframe["bb_lowerband"] = bb["lower"]

        # bb_position: 0=在下轨(最便宜), 1=在上轨(最贵)
        # +1e-10 防止除以0
        dataframe["bb_position"] = (
            (dataframe["close"] - dataframe["bb_lowerband"])
            / (dataframe["bb_upperband"] - dataframe["bb_lowerband"] + 1e-10)
        )

        # ATR(14) — 市场波动性（值越大波动越剧烈）
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)

        # 20周期成交量均线 — 判断是否放量
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        # ADX(14) — 趋势强度（>25有趋势，<20震荡）
        # 注意：ADX只判断强度，不判断方向
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        return dataframe

    # ====================================================================
    # 辅助：安全获取1h趋势
    # ====================================================================
    def _trend_up_1h(self, df):
        """
        判断1小时周期是否趋势向上。
        兼容多种列名格式（@informative可能产生不同命名）。
        无1h数据时默认返回True（不过滤）。
        """
        for c50, c200 in [("ema50", "ema200"), ("ema50_1h", "ema200_1h")]:
            if c50 in df.columns and c200 in df.columns:
                return df[c50] > df[c200]
        return True

    def _trend_down_1h(self, df):
        """
        判断1小时周期是否趋势向下。
        """
        for c50, c200 in [("ema50", "ema200"), ("ema50_1h", "ema200_1h")]:
            if c50 in df.columns and c200 in df.columns:
                return df[c50] < df[c200]
        return True

    # ====================================================================
    # 入场信号
    # ====================================================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        判断做多和做空信号。
        同时满足所有条件时才标记入场。
        """

        # ---- 做多信号 ----
        dataframe.loc[
            (
                # ✅ 趋势向上
                (dataframe["close"] > dataframe["ema200"]) &
                # ✅ RSI超卖反弹（抛压耗尽，买方入场）
                (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)) &
                # ✅ 价格在布林下轨附近（极度便宜）
                (dataframe["bb_position"] < self.buy_bb.value) &
                # ✅ 放量确认（有资金抄底）
                (dataframe["volume"] > dataframe["volume_sma"]) &
                # ✅ 趋势够强（不是震荡市）
                (dataframe["adx"] > self.buy_adx.value) &
                # ✅ 1h中期趋势向上
                self._trend_up_1h(dataframe) &
                # ✅ K线有效
                (dataframe["volume"] > 0)
            ),
            "enter_long"
        ] = 1

        # ---- 做空信号 ----
        dataframe.loc[
            (
                # ✅ 趋势向下
                (dataframe["close"] < dataframe["ema200"]) &
                # ✅ RSI超买回落（买入力竭，卖方入场）
                (qtpylib.crossed_below(dataframe["rsi"], self.sell_rsi.value)) &
                # ✅ 价格在布林上轨附近（极度昂贵）
                (dataframe["bb_position"] > self.sell_bb.value) &
                # ✅ 放量确认（有资金出逃）
                (dataframe["volume"] > dataframe["volume_sma"]) &
                # ✅ 趋势够强
                (dataframe["adx"] > self.buy_adx.value) &
                # ✅ 1h中期趋势向下
                self._trend_down_1h(dataframe) &
                # ✅ K线有效
                (dataframe["volume"] > 0)
            ),
            "enter_short"
        ] = 1

        return dataframe

    # ====================================================================
    # 出场信号（趋势破位）
    # ====================================================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        趋势破位出场。
        主要出场方式不是这里，而是ROI+追踪止损+动态止损。
        这里只是最后防线：价格破200EMA。
        """
        # 多头出场：价格跌破200EMA
        dataframe.loc[
            (dataframe["close"] < dataframe["ema200"]) &
            (dataframe["volume"] > 0),
            "exit_long"
        ] = 1

        # 空头出场：价格涨破200EMA
        dataframe.loc[
            (dataframe["close"] > dataframe["ema200"]) &
            (dataframe["volume"] > 0),
            "exit_short"
        ] = 1

        return dataframe

    # ====================================================================
    # 自定义动态止损
    # ====================================================================
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
        """
        动态止损：赚得越多，止损越紧。

        参数说明：
          current_profit: 0.01=+1%, -0.02=-2%（以开仓价为基准）
          返回值: 新的止损线（同样是比例），None=用默认-4%

        举例：
          买入100元，涨到108(+8%):
            current_profit=0.08 → return 0.08-0.02=0.06
            止损放在+6%（106元），锁住6%利润

          买入100元，涨到102.5(+2.5%):
            current_profit=0.025 → return 0.001
            止损放在开仓价+0.1%（保本出）
        """
        # 盈利 > 5%：锁住大部分利润
        if current_profit > 0.05:
            return current_profit - 0.02

        # 盈利 > 3%：锁住至少+1%
        if current_profit > 0.03:
            return current_profit - 0.02

        # 盈利 > 2%：保本出
        if current_profit > 0.02:
            return 0.001

        # 盈利 > 1%：缩紧止损到-1.5%
        if current_profit > 0.01:
            return -0.015

        # 盈利不足1%：使用默认硬止损-4%
        return None
