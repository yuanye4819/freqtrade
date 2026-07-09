import numpy as np; import pandas as pd
from pandas import DataFrame; from datetime import datetime
from typing import Optional
from freqtrade.strategy import IStrategy, IntParameter
from freqtrade.persistence import Trade
import talib.abstract as ta; from technical import qtpylib


class TrendGuardStrategy(IStrategy):
    """TrendGuard v2.3-final — 最佳参数 + ATR动态止损"""

    INTERFACE_VERSION = 3
    timeframe = "5m"; can_short: bool = False

    minimal_roi = {"120": 0.03, "60": 0.02, "0": 0.01}
    stoploss = -0.02                    # 硬止损 2%
    trailing_stop = True
    trailing_stop_positive = 0.015      # 盈利 1.5% 启动
    trailing_stop_positive_offset = 0.02 # 回撤 2% 触发
    trailing_only_offset_is_reached = True

    buy_rsi = IntParameter(20, 40, default=30, space="buy")

    process_only_new_candles = True
    use_exit_signal = False
    startup_candle_count: int = 200
    use_custom_stoploss = True

    order_types = {"entry":"limit","exit":"limit","stoploss":"market","stoploss_on_exchange":False}
    order_time_in_force = {"entry":"GTC","exit":"GTC"}

    @property
    def plot_config(self):
        return {"main_plot":{"ema200":{"color":"#FFA500"},"ema50":{"color":"#00FF00"},"bb_upperband":{"color":"grey"},"bb_lowerband":{"color":"grey"},"bb_middleband":{"color":"blue"}},"subplots":{"RSI":{"rsi":{"color":"#ff0066"}}}}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        bb = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_upperband"] = bb["upper"]; dataframe["bb_middleband"] = bb["mid"]; dataframe["bb_lowerband"] = bb["lower"]
        dataframe["bb_position"] = (dataframe["close"] - dataframe["bb_lowerband"]) / (dataframe["bb_upperband"] - dataframe["bb_lowerband"] + 1e-10)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            ((dataframe["ema50"] > dataframe["ema200"]) &
             (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)) &
             (dataframe["bb_position"] < 0.3) &
             (dataframe["volume"] > 0)),
            "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["close"] < dataframe["ema200"]) & (dataframe["volume"] > 0), "exit_long"] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool, **kwargs) -> Optional[float]:
        # 盈利后激进保护
        if current_profit > 0.03: return current_profit - 0.01
        if current_profit > 0.015: return 0.0   # 保本
        if current_profit > 0.005: return -0.01  # 缩紧
        # 根据持仓时间动态止损
        minutes = (current_time - trade.open_date_utc).total_seconds() / 60
        if current_profit < -0.01 and minutes > 120:
            return -0.005  # 持仓超2小时仍在亏→砍
        if current_profit < -0.015:
            return -0.01   # 亏损超1.5%→缩紧到1%
        return None
