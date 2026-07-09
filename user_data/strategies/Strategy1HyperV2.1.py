# ============================================================================
# Strategy1HyperV2.3 — 双向趋势守护（做多+做空+多周期）
# ============================================================================

import numpy as np; import pandas as pd
from pandas import DataFrame; from datetime import datetime
from typing import Optional
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, informative
from freqtrade.persistence import Trade
import talib.abstract as ta; from technical import qtpylib


class Strategy1HyperV21(IStrategy):
    """
    Strategy1HyperV2.3 — 双向 + 多周期趋势守护
    v2.3: 做空 + 1h趋势确认 + 出场优化
    """

    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short: bool = True

    # ====== 买入侧超参 ======
    buy_rsi  = IntParameter(15, 40, default=26, space="buy")
    buy_bb   = DecimalParameter(0.1, 0.5, default=0.17, decimals=2, space="buy")
    buy_adx  = IntParameter(15, 40, default=31, space="buy")

    # ====== 卖出/做空侧超参 ======
    sell_rsi = IntParameter(60, 85, default=76, space="sell")
    sell_bb  = DecimalParameter(0.5, 0.9, default=0.80, decimals=2, space="sell")

    # ====== 出场优化超参 ======
    exit_tsp = DecimalParameter(0.005, 0.03, default=0.019, decimals=3, space="sell")
    exit_tso = DecimalParameter(0.01, 0.04, default=0.033, decimals=3, space="sell")

    # ====== 固定参数 ======
    minimal_roi = {"120": 0.03, "60": 0.02, "30": 0.01, "0": 0.005}
    stoploss = -0.04
    trailing_stop = True
    trailing_only_offset_is_reached = True

    @property
    def trailing_stop_positive(self): return self.exit_tsp.value
    @property
    def trailing_stop_positive_offset(self): return self.exit_tso.value

    process_only_new_candles = True
    use_exit_signal = False
    startup_candle_count: int = 200
    use_custom_stoploss = True

    order_types = {"entry":"limit","exit":"limit","stoploss":"market","stoploss_on_exchange":False}
    order_time_in_force = {"entry":"GTC","exit":"GTC"}

    # ====== 1h 趋势指标（@informative 自动合并到 5m dataframe） ======
    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema50"]  = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    @property
    def plot_config(self):
        return {
            "main_plot": {"ema200":{"color":"#FFA500"},"bb_upperband":{"color":"grey"},"bb_lowerband":{"color":"grey"},"bb_middleband":{"color":"blue"}},
            "subplots": {"RSI":{"rsi":{"color":"#ff0066"}}}
        }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        bb = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_upperband"] = bb["upper"]; dataframe["bb_middleband"] = bb["mid"]; dataframe["bb_lowerband"] = bb["lower"]
        dataframe["bb_position"] = (dataframe["close"] - dataframe["bb_lowerband"]) / (dataframe["bb_upperband"] - dataframe["bb_lowerband"] + 1e-10)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    # ====== 辅助：安全获取 1h 趋势列 ======
    def _trend_up_1h(self, df):
        """1h 趋势向上：EMA50 > EMA200"""
        for c50, c200 in [("ema50","ema200"),("ema50_1h","ema200_1h")]:
            if c50 in df.columns and c200 in df.columns:
                return df[c50] > df[c200]
        return True  # 无1h数据时不过滤

    def _trend_down_1h(self, df):
        """1h 趋势向下：EMA50 < EMA200"""
        for c50, c200 in [("ema50","ema200"),("ema50_1h","ema200_1h")]:
            if c50 in df.columns and c200 in df.columns:
                return df[c50] < df[c200]
        return True

    # ========================================================================
    # 入场 — 做多 + 做空
    # ========================================================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # ---- 做多 ----
        dataframe.loc[
            ((dataframe["close"] > dataframe["ema200"]) &
             (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)) &
             (dataframe["bb_position"] < self.buy_bb.value) &
             (dataframe["volume"] > dataframe["volume_sma"]) &
             (dataframe["adx"] > self.buy_adx.value) &
             self._trend_up_1h(dataframe) &
             (dataframe["volume"] > 0)),
            "enter_long"
        ] = 1

        # ---- 做空 ----
        dataframe.loc[
            ((dataframe["close"] < dataframe["ema200"]) &
             (qtpylib.crossed_below(dataframe["rsi"], self.sell_rsi.value)) &
             (dataframe["bb_position"] > self.sell_bb.value) &
             (dataframe["volume"] > dataframe["volume_sma"]) &
             (dataframe["adx"] > self.buy_adx.value) &
             self._trend_down_1h(dataframe) &
             (dataframe["volume"] > 0)),
            "enter_short"
        ] = 1

        return dataframe

    # ========================================================================
    # 出场 — 趋势破位
    # ========================================================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["close"] < dataframe["ema200"]) & (dataframe["volume"] > 0), "exit_long"] = 1
        dataframe.loc[(dataframe["close"] > dataframe["ema200"]) & (dataframe["volume"] > 0), "exit_short"] = 1
        return dataframe

    # ========================================================================
    # 动态止损
    # ========================================================================
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool, **kwargs) -> Optional[float]:
        if current_profit > 0.05: return current_profit - 0.02
        if current_profit > 0.03: return current_profit - 0.02
        if current_profit > 0.02: return 0.001
        if current_profit > 0.01: return -0.015
        return None
