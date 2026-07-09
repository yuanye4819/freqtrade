"""=================================================
@PROJECT_NAME: freqtrade
@File    : MyStrategy.py
@Author  : Kepler
@Date    : 2026/5/7 下午3:17
@Function: 

@Modify History:
         
@Copyright：Copyright(c) 2024-2026. All Rights Reserved
=================================================="""
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class MyStrategy(IStrategy):
    #建议的最小时间间隔
    timeframe = '5m'

    #最大开仓数
    max_open_trades = 3

    #止损设置
    stoploss = -0.1  # %10止损

    #可选盈利目标
    minimal_roi = {
        "0": 0.10,  # 10%利润立即卖出
        "30": 0.05,  # 30分钟内5%利润
        "60": 0.02,  # 60分钟内2%利润
        "120": 0  # 120分钟后保本卖出
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
           添加技术指标到dataframe
           这个函数接收包含历史K线数据的dataframe，计算各种技术指标，
           并将结果作为新的列添加到dataframe中，最后返回处理后的dataframe。
        """
        # --- RSI (相对强弱指数) ---
        # 计算14周期的RSI指标。RSI用于衡量价格变动的速度和幅度，判断市场是否超买或超卖。
        # 默认timeperiod为14，值高于70通常被认为是超买，低于30被认为是超卖。
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=14)

        # --- MACD (指数平滑异同移动平均线) ---
        # 计算MACD指标。MACD由三部分组成：MACD线、信号线和柱状图，用于判断趋势的强度和方向。
        # ta.MACD返回一个包含这三个值的字典。
        macd = ta.MACD(dataframe)
        # 将MACD线（快线）存入新列'macd'
        dataframe['macd'] = macd['macd']
        # 将信号线（慢线）存入新列'macdsignal'
        dataframe['macdsignal'] = macd['macdsignal']
        # 将MACD柱状图（MACD线与信号线的差值）存入新列'macdhist'
        dataframe['macdhist'] = macd['macdhist']

        # --- 布林带 ---
        # 计算20周期的布林带。布林带由中轨（移动平均线）和上下轨（标准差通道）组成，用于衡量价格波动性。
        # timeperiod=20 指定了计算移动平均线和标准差的周期。
        bollinger = ta.BBANDS(dataframe, timeperiod=20)
        # 将布林带下轨存入新列'bb_lowerband'
        dataframe['bb_lowerband'] = bollinger['lowerband']
        # 将布林带中轨（通常是20周期简单移动平均线）存入新列'bb_middleband'
        dataframe['bb_middleband'] = bollinger['middleband']
        # 将布林带上轨存入新列'bb_upperband'
        dataframe['bb_upperband'] = bollinger['upperband']

        # --- 移动平均线 ---
        # 计算10周期的简单移动平均线，作为短期趋势参考。
        dataframe['sma_short'] = ta.SMA(dataframe, timeperiod=10)
        # 计算30周期的简单移动平均线，作为长期趋势参考。
        # 短期均线上穿长期均线通常被视为买入信号（金叉），反之为卖出信号（死叉）。
        dataframe['sma_long'] = ta.SMA(dataframe, timeperiod=30)

        # 返回添加了所有技术指标的dataframe，供后续的买卖信号函数使用。
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        定义买入信号（进场趋势）
        策略逻辑：寻找超卖后的反弹机会，即均线金叉且RSI处于低位时买入
        """
        dataframe.loc[
            (
                # 条件 1: 短期均线上穿长期均线（金叉）
                # 含义：短期趋势强于长期趋势，看涨信号
                    (dataframe['sma_short'] > dataframe['sma_long']) &

                    # 条件 2: RSI 低于 30
                    # 含义：市场处于“超卖”状态，价格可能被低估，有反弹需求
                    (dataframe['rsi'] < 30) &

                    # 条件 3: 收盘价高于布林带下轨
                    # 含义：价格没有极端跌破统计学的“地板”，避免接飞刀
                    (dataframe['close'] > dataframe['bb_lowerband'])
            ),
            'enter_long'] = 1  # 目标列：'enter_long'（做多进场），标记为 1 代表“买入”

        return dataframe
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        定义卖出信号（出场趋势）
        策略逻辑：寻找超买机会，即价格涨过头了，卖出止盈
        """
        dataframe.loc[
            (
                # 条件 1: RSI 高于 70
                # 含义：相对强弱指数高于70，市场处于“超买”状态，情绪可能过热
                    (dataframe['rsi'] > 70) &

                    # 条件 2: 收盘价高于布林带上轨
                    # 含义：价格突破了统计学的“天花板”，属于极端高估，随时可能回调
                    (dataframe['close'] > dataframe['bb_upperband'])
            ),
            'exit_long'] = 1  # 目标列：'exit_long'（做多出场），标记为 1 代表“卖出”

        return dataframe


