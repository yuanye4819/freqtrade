# Strategy1HyperV1.1 — 三交易对优化版
import numpy as np; import pandas as pd
from pandas import DataFrame; from datetime import datetime
from typing import Optional
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade
import talib.abstract as ta; from technical import qtpylib


class Strategy1HyperV11(IStrategy):
    """Strategy1HyperV1.1 — BTC/ETH/OKB + 超参优化"""

    INTERFACE_VERSION = 3
    timeframe = "5m"; can_short: bool = False

    buy_rsi = IntParameter(15, 40, default=26, space="buy")
    buy_bb  = DecimalParameter(0.1, 0.5, default=0.17, decimals=2, space="buy")
    buy_adx = IntParameter(15, 40, default=31, space="buy")

    minimal_roi = {"120": 0.03, "60": 0.02, "30": 0.01, "0": 0.005}
    stoploss = -0.04
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    use_exit_signal = False
    startup_candle_count: int = 200
    use_custom_stoploss = True

    order_types = {"entry":"limit","exit":"limit","stoploss":"market","stoploss_on_exchange":False}
    order_time_in_force = {"entry":"GTC","exit":"GTC"}

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

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            ((dataframe["close"] > dataframe["ema200"]) &
             (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)) &
             (dataframe["bb_position"] < self.buy_bb.value) &
             (dataframe["volume"] > dataframe["volume_sma"]) &
             (dataframe["adx"] > self.buy_adx.value) &
             (dataframe["volume"] > 0)),
            "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["close"] < dataframe["ema200"]) & (dataframe["volume"] > 0), "exit_long"] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool, **kwargs) -> Optional[float]:
        if current_profit > 0.05: return current_profit - 0.02
        if current_profit > 0.03: return current_profit - 0.02
        if current_profit > 0.02: return 0.001
        if current_profit > 0.01: return -0.015
        return None
