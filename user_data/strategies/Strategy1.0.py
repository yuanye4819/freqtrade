# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
from freqtrade.strategy import IStrategy, IntParameter
from freqtrade.persistence import Trade
import talib.abstract as ta
from technical import qtpylib


class Strategy1(IStrategy):
    """
    TrendGuard 趋势守护策略 v2.0

    核心理念：在上升趋势中，于深度回调处入场，多重止损保护利润。

    五大改进（对比原始 RSI 策略）：
    1. EMA200 趋势过滤 — 只在价格高于200EMA时做多
    2. 六重入场确认 — 趋势+RSI+布林带+成交量+ADX
    3. 动态保护止损 — 盈利后自动提升止损
    4. 追踪止损 — 盈利达标后追踪回撤
    5. 关闭出场信号 — 由ROI+止损接管，避免过早退出
    """

    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short: bool = False

    # ---- 止盈 (ROI) ----
    minimal_roi = {"120": 0.03, "60": 0.02, "30": 0.01, "0": 0.005}

    # ---- 止损 ----
    stoploss = -0.04
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    # ---- 超参优化 ----
    buy_rsi = IntParameter(20, 40, default=28, space="buy")
    exit_rsi = IntParameter(65, 85, default=75, space="sell")

    # ---- 运行设置 ----
    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 200
    use_custom_stoploss = True

    order_types = {
        "entry": "limit", "exit": "limit",
        "stoploss": "market", "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    @property
    def plot_config(self):
        return {
            "main_plot": {
                "ema200": {"color": "#FFA500"},
                "bb_upperband": {"color": "grey"},
                "bb_lowerband": {"color": "grey"},
                "bb_middleband": {"color": "blue"},
            },
            "subplots": {
                "RSI": {"rsi": {"color": "#ff0066"}},
                "MACD": {
                    "macd": {"color": "blue"},
                    "macdsignal": {"color": "orange"},
                },
                "Volume": {"volume": {"color": "#00ccff"}},
            }
        }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]
        bb = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_upperband"] = bb["upper"]
        dataframe["bb_middleband"] = bb["mid"]
        dataframe["bb_lowerband"] = bb["lower"]
        dataframe["bb_position"] = (
            (dataframe["close"] - dataframe["bb_lowerband"])
            / (dataframe["bb_upperband"] - dataframe["bb_lowerband"] + 1e-10)
        )
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["ema200"]) &
                (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)) &
                (dataframe["bb_position"] < 0.3) &
                (dataframe["volume"] > dataframe["volume_sma"]) &
                (dataframe["adx"] > 20) &
                (dataframe["volume"] > 0)
            ),
            "enter_long"
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 出场由 ROI + 追踪止损 + 动态止损管理，此处仅做趋势破位保护
        dataframe.loc[
            (dataframe["close"] < dataframe["ema200"]) & (dataframe["volume"] > 0),
            "exit_long"
        ] = 1
        return dataframe

    def custom_stoploss(
        self, pair: str, trade: Trade, current_time: datetime,
        current_rate: float, current_profit: float, after_fill: bool, **kwargs,
    ) -> Optional[float]:
        if current_profit > 0.05:
            return current_profit - 0.02
        if current_profit > 0.03:
            return current_profit - 0.02
        if current_profit > 0.02:
            return 0.001
        if current_profit > 0.01:
            return -0.015
        return None
