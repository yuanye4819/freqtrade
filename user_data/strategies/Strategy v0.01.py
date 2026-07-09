
# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# =============================================================================
# 以上三行是告诉代码检查工具（pylint、flake8、isort）不要对这个文件报错。
# 这是 Freqtrade 策略模板的标准写法，请不要删除。
# =============================================================================

# --- 以下导入是 Freqtrade 策略框架的「必要依赖」，请不要删除 ---
import numpy as np          # 用于科学计算，比如指数运算 np.exp()
import pandas as pd         # 数据处理核心库，K线数据就是用 pandas 的 DataFrame 格式存储的
from datetime import datetime, timedelta, timezone  # 处理日期和时区
from pandas import DataFrame                       # DataFrame 类型，表示一张"表格"
from typing import Dict, Optional, Union, Tuple     # Python 类型注解，让代码更清晰

from freqtrade.strategy import (
    IStrategy,              # 【核心】所有策略都必须继承的基类，你的策略类要继承它
    Trade,                  # 交易对象，记录每一笔交易的状态
    Order,                  # 订单对象，记录每一个订单的信息
    PairLocks,              # 交易对锁，用于暂时禁止某个交易对交易
    informative,            # @informative 装饰器：让你的策略能"偷看"其他交易对的数据
    # ----- 以下是用于 Hyperopt（超参优化）的参数类型 -----
    BooleanParameter,       # 布尔型参数：True 或 False，如"是否启用移动止损"
    CategoricalParameter,   # 分类型参数：从几个选项中选一个，如"使用 EMA 还是 SMA"
    DecimalParameter,       # 小数型参数：带小数点的数值
    IntParameter,           # 整数型参数：如 RSI 周期（只能是整数）
    RealParameter,          # 实数型参数：和 DecimalParameter 类似
    # ----- 时间框架（时间周期）辅助工具 -----
    timeframe_to_minutes,       # 把 "5m" 这样的字符串转成分钟数 → 5
    timeframe_to_next_date,     # 计算下一个K线的起始时间
    timeframe_to_prev_date,     # 计算上一个K线的起始时间
    # ----- 策略辅助函数 -----
    merge_informative_pair,     # 把"偷看"来的其他交易对数据合并到当前 DataFrame
    stoploss_from_absolute,     # 根据绝对价格计算止损价
    stoploss_from_open,         # 根据开盘价计算止损价
    AnnotationType,             # 注释类型
)

# --------------------------------
# 在此处导入你自己的库（技术指标计算库）
# --------------------------------
import talib.abstract as ta         # TA-Lib：最常用的技术指标库（RSI、MACD、布林带等）
from technical import qtpylib       # qtpylib：Freqtrade 配套的技术分析工具库


# =============================================================================
# 策略类定义
# =============================================================================
class MyAwesomeStrategy(IStrategy):
    """
    ============================================================================
    策略名称：MyAwesomeStrategy（你可以重命名，记得同步修改 config.json 中的 strategy 字段）
    
    这是一个 Freqtrade 策略模板，帮助你快速开始编写自己的量化交易策略。
    更多信息请参考官方文档：https://www.freqtrade.io/en/stable/strategy-customization/
    
    【你可以做的事情】：
    - 重命名类名（别忘了更新 config.json 中的 "strategy" 字段）
    - 添加任意方法来实现你的交易逻辑
    - 添加任意第三方库来辅助策略开发
    
    【你必须保留的】：
    - "Do not remove these imports" 下方的所有导入
    - 三个方法：populate_indicators（计算指标）、
               populate_entry_trend（定义买入信号）、
               populate_exit_trend（定义卖出信号）
    
    【你应该保留的】：
    - timeframe（时间周期）、minimal_roi（最小收益率）、
      stoploss（止损）、trailing_*（移动止损相关）
    
    【策略运行流程简述】（初学者必读）：
    1. Freqtrade 从交易所获取K线数据（OHLCV：开、高、低、收、量）
    2. 调用 populate_indicators() → 在K线数据基础上计算技术指标
    3. 调用 populate_entry_trend()  → 根据指标判断是否买入
    4. 调用 populate_exit_trend()   → 根据指标判断是否卖出
    5. 如果信号触发，Freqtrade 自动下单，并持续监控持仓
    ============================================================================
    """

    # =========================================================================
    # 策略接口版本号
    # INTERFACE_VERSION 告诉 Freqtrade 这个策略使用的是哪个版本的接口规范。
    # 当前最新版本是 3。不同版本之间策略的写法有细微差别，
    # 如果你从旧版迁移，请参考官方文档中的升级指南。
    # =========================================================================
    INTERFACE_VERSION = 3

    # =========================================================================
    # 时间周期（Timeframe）
    # 这是策略使用的K线周期。"5m" 表示每根K线代表 5 分钟的价格变化。
    # 常见选项："1m"（1分钟）、"5m"、"15m"、"30m"、"1h"（1小时）、
    #           "4h"、"1d"（1天）等。
    # 周期越短 → 交易信号越多 → 交易越频繁（手续费也越多）
    # 周期越长 → 信号越少但可能更可靠 → 更适合趋势跟踪
    # =========================================================================
    timeframe = "5m"

    # =========================================================================
    # 是否允许做空（can_short）
    # False：只能做多（低价买 → 高价卖，这是现货交易的模式）
    # True ：可以做空（高价借币卖出 → 低价买回还币，赚差价）
    # ⚠️ 做空功能仅在「期货模式」或「保证金模式」下可用，现货模式无效。
    # =========================================================================
    can_short: bool = False

    # =========================================================================
    # 最小投资回报率（minimal_roi）
    # 这是一个「时间-收益率」对照表，告诉 Freqtrade 持有多久后，
    # 达到多少利润就应该卖出。
    #
    # 格式：{ "持仓分钟数": 目标收益率 }
    # 例如下面的配置含义是：
    #   "60": 0.01  →  持仓超过 60 分钟后，只要盈利 ≥ 1% 就卖出
    #   "30": 0.02  →  持仓超过 30 分钟后，只要盈利 ≥ 2% 就卖出
    #   "0":  0.04  →  从买入那一刻起，只要盈利 ≥ 4% 就立刻卖出
    #
    # 💡 这里的 "0" 是最高优先级，意思是"不管持有多久，盈利 4% 就卖"。
    #    如果到了 30 分钟还没到 4%，就降到 "盈利 2% 就卖"。
    #    如果到了 60 分钟还没到 2%，就降到 "盈利 1% 就卖"。
    #
    # ⚠️ 如果 config.json 中也有 "minimal_roi" 字段，那个会覆盖这里的设置。
    # =========================================================================
    minimal_roi = {
        "60": 0.01,   # 60分钟后 → 1% 利润就卖
        "30": 0.02,   # 30分钟后 → 2% 利润就卖
        "0": 0.04     # 立即 → 4% 利润就卖
    }

    # =========================================================================
    # 止损比例（stoploss）
    # 这是"硬止损"——当亏损达到这个比例时，无条件卖出。
    # -0.10 表示亏损 10% 时止损。
    #
    # 举例：你在 100 USDT 买入，价格跌到 90 USDT 时，系统会自动卖出止损。
    #
    # ⚠️ 止损是风险控制的核心！不设止损 = 可能亏光全部本金。
    # ⚠️ 如果 config.json 中有 "stoploss" 字段，那个会覆盖这里的设置。
    # =========================================================================
    stoploss = -0.05

    # =========================================================================
    # 移动止损（Trailing Stop）
    # 
    # 【什么是移动止损？】
    # 普通止损是固定的（如 -10%），移动止损会随着价格上涨而"上移"止损线。
    # 举例：你 100 买入，止损线在 90。当价格涨到 120 时，移动止损会把止损线
    # 也上移到 108（仍然保持 10% 的距离），这样即使价格回落也能锁定利润。
    #
    # trailing_stop = True/False：是否启用移动止损
    # trailing_stop_positive = 0.01：当盈利超过 1% 后，开始启用移动止损
    # trailing_stop_positive_offset = 0.0：触发移动止损需要的起始偏移量
    # trailing_only_offset_is_reached = False：
    #   False → 止损线一旦盈利就开始上移
    #   True  → 只有盈利超过 trailing_stop_positive_offset 后才开始上移
    # =========================================================================
    trailing_stop = False                      # 当前关闭移动止损
    # trailing_only_offset_is_reached = False  # （已注释）仅达到偏移后才启用
    # trailing_stop_positive = 0.01           # （已注释）盈利1%后启用移动止损
    # trailing_stop_positive_offset = 0.0     # （已注释）偏移量为0

    # =========================================================================
    # 仅在新K线出现时计算指标（process_only_new_candles）
    # True  → 每根K线只计算一次指标（性能更好，推荐）
    # False → 每次循环都重新计算（浪费CPU，除非有特殊需求）
    # =========================================================================
    process_only_new_candles = True

    # =========================================================================
    # 以下三个参数控制「出场」行为，可在 config.json 中覆盖：
    #
    # use_exit_signal = True
    #   → 是否使用 populate_exit_trend() 中定义的卖出信号
    #   → 如果设为 False，则不根据指标卖出，仅靠 minimal_roi 和 stoploss 出场
    #
    # exit_profit_only = False
    #   → False：即使是亏损状态，卖出信号触发也会执行（允许"割肉"）
    #   → True ：只有在盈利状态下，卖出信号才会执行（亏损时只靠止损退出）
    #
    # ignore_roi_if_entry_signal = False
    #   → False：ROI（收益率目标）和入场信号各自独立运作
    #   → True ：当入场信号触发时，即使 ROI 条件也满足，也优先买入而非卖出
    # =========================================================================
    use_exit_signal = True             # 启用指标卖出信号
    exit_profit_only = False           # 允许亏损时卖出
    ignore_roi_if_entry_signal = False # 入场信号不覆盖 ROI

    # =========================================================================
    # 启动所需的最少K线数量（startup_candle_count）
    # 策略需要至少这么多根历史K线才能计算出有效的技术指标。
    # 例如：计算 30 周期均线需要至少 30 根K线，否则结果不准确。
    # 在实际交易开始前，Freqtrade 会先"预热"这么多根K线。
    # =========================================================================
    startup_candle_count: int = 30

    # =========================================================================
    # 策略可优化参数（Hyperopt 超参搜索用）
    # 
    # IntParameter(最小值, 最大值, default=默认值, space="类别")
    # space="buy"  → 这个参数属于"买入"优化空间
    # space="sell" → 这个参数属于"卖出"优化空间
    #
    # 运行时用 self.buy_rsi.value 来获取当前参数值。
    # 做 Hyperopt 时，Freqtrade 会在 10~40 之间自动搜索最优的 buy_rsi 值。
    # =========================================================================
    buy_rsi = IntParameter(10, 40, default=30, space="buy")
    # → 买入RSI阈值：在 10~40 之间搜索，默认值 30（超卖区域）

    sell_rsi = IntParameter(60, 90, default=70, space="sell")
    # → 卖出RSI阈值：在 60~90 之间搜索，默认值 70（超买区域）

    # =========================================================================
    # 订单类型映射（order_types）
    # 定义每种操作使用什么类型的订单：
    #
    # "limit"  → 限价单：指定价格买卖，可能不会立即成交但手续费低
    # "market" → 市价单：按当前最优价格立即成交，但手续费高且有滑点
    #
    # stoploss_on_exchange = False：
    #   → False：止损由 Freqtrade 本地监控，到价时发市价单
    #   → True ：止损单直接挂在交易所（交易所宕机也能触发止损，更安全）
    # =========================================================================
    order_types = {
        "entry": "limit",                # 入场用限价单（挂低价等成交，省手续费）
        "exit": "limit",                 # 出场用限价单
        "stoploss": "market",            # 止损用市价单（紧急情况必须立即成交！）
        "stoploss_on_exchange": False    # 不在交易所端挂止损单（由 Freqtrade 本地管理）
    }

    # =========================================================================
    # 订单有效期（order_time_in_force）
    # GTC = Good Till Cancel（取消前一直有效）
    # 其他选项：IOC（立即成交或取消）、FOK（全部成交或取消）
    # GTC 是最常用的选择：挂单后一直等着，直到成交或你主动取消。
    # =========================================================================
    order_time_in_force = {
        "entry": "GTC",   # 入场单：一直挂着等成交
        "exit": "GTC"     # 出场单：一直挂着等成交
    }

    # =========================================================================
    # 图表配置（plot_config）
    # 
    # 这个属性定义了回测结果图表中显示哪些指标，以及它们的颜色。
    # Freqtrade 回测完成后会自动生成 HTML 图表，这个配置决定图表长什么样。
    #
    # main_plot：叠加在K线主图上的指标（和价格共享同一个Y轴）
    # subplots：显示在独立子图中的指标（有自己的Y轴）
    # =========================================================================
    @property
    def plot_config(self):
        return {
            # ---- 主图（叠加在K线图上）----
            "main_plot": {
                "tema": {},                        # TEMA 三重指数移动平均线（用默认颜色）
                "sar": {"color": "white"},         # SAR 抛物线指标（用白色显示）
            },
            # ---- 子图（独立显示在K线下方）----
            "subplots": {
                # MACD 子图：包含 MACD 线和信号线
                "MACD": {
                    "macd": {"color": "blue"},         # MACD 快线 → 蓝色
                    "macdsignal": {"color": "orange"}, # MACD 信号线 → 橙色
                },
                # RSI 子图
                "RSI": {
                    "rsi": {"color": "red"},           # RSI 线 → 红色
                }
            }
        }

    # =========================================================================
    # 信息型交易对（informative_pairs）
    # 
    # 这个方法让你可以"偷看"其他交易对的数据，即使你的策略不交易它们。
    # 比如你的策略只交易 ETH/USDT，但你想参考 BTC/USDT 的走势做决策。
    #
    # 返回格式：交易对和K线周期的元组列表
    # 示例：return [("ETH/USDT", "5m"), ("BTC/USDT", "15m")]
    #
    # 当前返回空列表，表示不需要额外的参考数据。
    # =========================================================================
    def informative_pairs(self):
        return []

    # =========================================================================
    # ====================== 核心方法一：计算技术指标 ==========================
    # =========================================================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        向 DataFrame 中添加各种技术分析指标。
        
        【什么是 DataFrame？】
        把它想象成一个 Excel 表格，每一行是一根K线（时间从远到近），
        每一列是某种数据（开盘价、收盘价、成交量、RSI、MACD……）。
        
        这个方法做的事情就是：拿到只有 OHLCV 的"空表格"，
        往里面一列一列地添加计算好的指标数据，然后返回这张"填满了"的表格。

        参数说明：
        :param dataframe: 交易所返回的原始 OHLCV 数据
                          （包含 open开盘、high最高、low最低、close收盘、volume成交量 五列）
        :param metadata:  附加信息字典，比如 metadata["pair"] 是当前交易对名称（如 "BTC/USDT"）
        :return: 添加了所有技术指标列的 DataFrame
        
        性能提示：只启用你实际使用的指标！注释掉的指标不会消耗 CPU。
        """

        # =====================================================================
        # 第一大类：动量指标（Momentum Indicators）
        # 动量指标用于衡量价格变动的「速度和幅度」，
        # 帮助判断趋势是加速还是减速，市场是否超买或超卖。
        # =====================================================================

        # --- ADX（平均趋向指数）---
        # ADX 衡量的是「趋势的强度」，而不是方向。
        # ADX > 25：趋势较强（无论涨跌）
        # ADX < 20：横盘震荡，趋势不明显
        # 💡 常与 +DI/-DI 配合使用来判断趋势方向
        dataframe["adx"] = ta.ADX(dataframe)

        # --- +DI（正向趋向指标，已注释）---
        # 表示上涨方向的动能。如果 +DI > -DI，说明多头占优。
        # dataframe["plus_dm"] = ta.PLUS_DM(dataframe)
        # dataframe["plus_di"] = ta.PLUS_DI(dataframe)

        # --- -DI（负向趋向指标，已注释）---
        # 表示下跌方向的动能。如果 -DI > +DI，说明空头占优。
        # dataframe["minus_dm"] = ta.MINUS_DM(dataframe)
        # dataframe["minus_di"] = ta.MINUS_DI(dataframe)

        # --- Aroon 指标（已注释）---
        # Aroon Up: 反映最近一次最高价出现的时间
        # Aroon Down: 反映最近一次最低价出现的时间
        # aroon = ta.AROON(dataframe)
        # dataframe["aroonup"] = aroon["aroonup"]
        # dataframe["aroondown"] = aroon["aroondown"]
        # dataframe["aroonosc"] = ta.AROONOSC(dataframe)  # Aroon 振荡器

        # --- AO（Awesome Oscillator，超级振荡器，已注释）---
        # dataframe["ao"] = qtpylib.awesome_oscillator(dataframe)

        # --- Keltner 通道（已注释）---
        # 类似布林带，但使用 ATR（平均真实波幅）而不是标准差来计算带宽。
        # keltner = qtpylib.keltner_channel(dataframe)
        # dataframe["kc_upperband"] = keltner["upper"]    # 上轨
        # dataframe["kc_lowerband"] = keltner["lower"]    # 下轨
        # dataframe["kc_middleband"] = keltner["mid"]     # 中轨
        # dataframe["kc_percent"] = (                      # 价格在通道中的位置（%）
        #     (dataframe["close"] - dataframe["kc_lowerband"]) /
        #     (dataframe["kc_upperband"] - dataframe["kc_lowerband"])
        # )
        # dataframe["kc_width"] = (                        # 通道宽度（波动性）
        #     (dataframe["kc_upperband"] - dataframe["kc_lowerband"]) / dataframe["kc_middleband"]
        # )

        # --- UO（Ultimate Oscillator，终极振荡器，已注释）---
        # dataframe["uo"] = ta.ULTOSC(dataframe)

        # --- CCI（Commodity Channel Index，商品通道指数，已注释）---
        # 取值范围：超卖 < -100，超买 > 100
        # dataframe["cci"] = ta.CCI(dataframe)

        # --- RSI（Relative Strength Index，相对强弱指数）---
        # 【当前策略启用的核心指标】
        # RSI 是最经典的技术指标之一，取值范围 0~100：
        #   RSI > 70 → "超买"：价格可能涨过头了，有回调风险
        #   RSI < 30 → "超卖"：价格可能跌过头了，有反弹机会
        #   RSI = 50 → 中性，没有明显倾向
        # 默认使用 14 根K线的周期计算。
        dataframe["rsi"] = ta.RSI(dataframe)

        # --- Fisher Transform on RSI（RSI的费雪变换，已注释）---
        # 把 RSI 值映射到 [-1, 1] 范围，让极值更明显，更容易识别转折点。
        # rsi = 0.1 * (dataframe["rsi"] - 50)
        # dataframe["fisher_rsi"] = (np.exp(2 * rsi) - 1) / (np.exp(2 * rsi) + 1)
        # dataframe["fisher_rsi_norma"] = 50 * (dataframe["fisher_rsi"] + 1)  # 归一化到 0~100

        # --- Slow Stochastic（慢速随机指标，已注释）---
        # stoch = ta.STOCH(dataframe)
        # dataframe["slowd"] = stoch["slowd"]  # 慢速 %D 线（更平滑）
        # dataframe["slowk"] = stoch["slowk"]  # 慢速 %K 线

        # --- Fast Stochastic（快速随机指标）---
        # Stochastic 衡量收盘价在最近一段时间的价格范围中的位置。
        # fastk：快速 %K 线，反应灵敏但波动大
        # fastd：快速 %D 线，是 %K 的移动平均，稍微平滑一些
        # 用法：%K 上穿 %D → 买入信号；%K 下穿 %D → 卖出信号
        stoch_fast = ta.STOCHF(dataframe)
        dataframe["fastd"] = stoch_fast["fastd"]   # 快速随机指标 %D 线
        dataframe["fastk"] = stoch_fast["fastk"]   # 快速随机指标 %K 线

        # --- Stochastic RSI（已注释）---
        # ⚠️ 重要：TA-Lib 的 STOCHRSI 和 TradingView 的计算方式不同，
        #    直接使用可能导致信号不一致。建议验证后再使用。
        # stoch_rsi = ta.STOCHRSI(dataframe)
        # dataframe["fastd_rsi"] = stoch_rsi["fastd"]
        # dataframe["fastk_rsi"] = stoch_rsi["fastk"]

        # --- MACD（Moving Average Convergence Divergence，指数平滑异同移动平均线）---
        # MACD 是最常用的趋势指标，由三部分组成：
        #   macd       = 快线（12周期EMA - 26周期EMA）→ 反映短期趋势
        #   macdsignal = 信号线（macd 的 9周期EMA）   → 反映长期趋势
        #   macdhist   = 柱状图（macd - macdsignal）  → 反映两条线的距离
        #
        # 经典用法：
        #   快线上穿信号线（macdhist 由负变正）→ 金叉，买入信号
        #   快线下穿信号线（macdhist 由正变负）→ 死叉，卖出信号
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]              # MACD 快线
        dataframe["macdsignal"] = macd["macdsignal"]  # MACD 信号线（慢线）
        dataframe["macdhist"] = macd["macdhist"]      # MACD 柱状图 = 快线 - 信号线

        # --- MFI（Money Flow Index，资金流量指数）---
        # MFI 是"带成交量的 RSI"，取值范围也是 0~100。
        # 它不仅考虑价格变化，还考虑成交量：
        #   价格涨 + 成交量大 → 真正强势，MFI 偏高
        #   价格涨 + 成交量小 → 虚涨，MFI 不会太高
        # MFI > 80 → 超买；MFI < 20 → 超卖
        dataframe["mfi"] = ta.MFI(dataframe)

        # --- ROC（Rate of Change，变动率，已注释）---
        # 衡量价格相对于 N 周期前的百分比变化。
        # dataframe["roc"] = ta.ROC(dataframe)

        # =====================================================================
        # 第二大类：重叠指标（Overlap Studies）
        # 重叠指标的特点是它们的数值范围和价格差不多，
        # 通常直接画在K线图上和价格"重叠"显示。
        # =====================================================================

        # --- Bollinger Bands（布林带）---
        # 【当前策略启用的核心指标】
        # 布林带由三条线组成：
        #   中轨 = 20周期简单移动平均线（SMA）
        #   上轨 = 中轨 + 2倍标准差
        #   下轨 = 中轨 - 2倍标准差
        #
        # 统计学含义：在正态分布假设下，约95%的价格应该落在布林带内。
        # 价格触及上轨 → 可能超买，有回调压力
        # 价格触及下轨 → 可能超卖，有反弹动力
        # 带宽收窄     → " squeezing"，通常预示大行情即将来临
        #
        # 参数说明：
        #   qtpylib.typical_price(dataframe) = (high + low + close) / 3
        #   window=20：用20根K线计算
        #   stds=2：上下轨距离中轨 2 个标准差
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe["bb_lowerband"] = bollinger["lower"]    # 布林带下轨
        dataframe["bb_middleband"] = bollinger["mid"]     # 布林带中轨（20周期均线）
        dataframe["bb_upperband"] = bollinger["upper"]    # 布林带上轨

        # bb_percent：价格在布林带中的相对位置（百分比表示）
        # 0%  = 正好在下轨上    → 极低位
        # 50% = 正好在中轨上    → 正常位置
        # 100% = 正好在上轨上   → 极高位
        dataframe["bb_percent"] = (
            (dataframe["close"] - dataframe["bb_lowerband"]) /
            (dataframe["bb_upperband"] - dataframe["bb_lowerband"])
        )

        # bb_width：布林带宽度（上下轨距离 ÷ 中轨值）
        # 宽度越大 → 市场波动越大
        # 宽度越小 → 市场越平静（可能即将突破）
        dataframe["bb_width"] = (
            (dataframe["bb_upperband"] - dataframe["bb_lowerband"]) / dataframe["bb_middleband"]
        )

        # --- 加权布林带（基于EMA而非SMA，已注释）---
        # weighted_bollinger = qtpylib.weighted_bollinger_bands(
        #     qtpylib.typical_price(dataframe), window=20, stds=2
        # )
        # dataframe["wbb_upperband"] = weighted_bollinger["upper"]
        # dataframe["wbb_lowerband"] = weighted_bollinger["lower"]
        # dataframe["wbb_middleband"] = weighted_bollinger["mid"]
        # dataframe["wbb_percent"] = (
        #     (dataframe["close"] - dataframe["wbb_lowerband"]) /
        #     (dataframe["wbb_upperband"] - dataframe["wbb_lowerband"])
        # )
        # dataframe["wbb_width"] = (
        #     (dataframe["wbb_upperband"] - dataframe["wbb_lowerband"]) / dataframe["wbb_middleband"]
        # )

        # --- EMA（Exponential Moving Average，指数移动平均线，已注释）---
        # EMA 比 SMA 更灵敏，因为给最近的价格更高权重。
        # 数字 = 计算周期（用多少根K线）
        # dataframe["ema3"] = ta.EMA(dataframe, timeperiod=3)    # 3周期EMA（超短线）
        # dataframe["ema5"] = ta.EMA(dataframe, timeperiod=5)    # 5周期EMA
        # dataframe["ema10"] = ta.EMA(dataframe, timeperiod=10)  # 10周期EMA（短线）
        # dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)  # 21周期EMA（中线）
        # dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)  # 50周期EMA（长线）
        # dataframe["ema100"] = ta.EMA(dataframe, timeperiod=100) # 100周期EMA（超长线）

        # --- SMA（Simple Moving Average，简单移动平均线，已注释）---
        # SMA 是纯粹的算术平均，每根K线权重相同。
        # dataframe["sma3"] = ta.SMA(dataframe, timeperiod=3)
        # dataframe["sma5"] = ta.SMA(dataframe, timeperiod=5)
        # dataframe["sma10"] = ta.SMA(dataframe, timeperiod=10)
        # dataframe["sma21"] = ta.SMA(dataframe, timeperiod=21)
        # dataframe["sma50"] = ta.SMA(dataframe, timeperiod=50)
        # dataframe["sma100"] = ta.SMA(dataframe, timeperiod=100)

        # --- SAR（Parabolic SAR，抛物线转向指标）---
        # SAR 是一个很直观的指标，直接在K线图上显示为小圆点：
        #   圆点在价格下方 → 上涨趋势，持有多头
        #   圆点在价格上方 → 下跌趋势，应空仓或做空
        # 圆点"翻转"（从下方跳到上方或反之）是趋势反转信号。
        dataframe["sar"] = ta.SAR(dataframe)

        # --- TEMA（Triple Exponential Moving Average，三重指数移动平均线）---
        # 【当前策略启用的核心指标】
        # TEMA 是对 EMA 的再平滑：先算EMA，再对EMA算EMA，再对结果算EMA。
        # 优点：比普通EMA更平滑，同时滞后更小，能更快捕捉趋势变化。
        # timeperiod=9：使用 9 根K线作为基础周期。
        dataframe["tema"] = ta.TEMA(dataframe, timeperiod=9)

        # =====================================================================
        # 第三大类：周期指标（Cycle Indicators）
        # 周期指标试图识别市场的"节律"——上涨和下跌交替的周期。
        # =====================================================================

        # --- Hilbert 变换 - 正弦波指标 ---
        # HT_SINE 是一种基于 Hilbert 变换的周期分析工具。
        #   sine：正弦波值，在 -1 到 1 之间波动
        #   leadsine：领先正弦波，比 sine 提前变化，可能提供预警信号
        # 当 sine 和 leadsine 交叉时，可能预示趋势转折。
        hilbert = ta.HT_SINE(dataframe)
        dataframe["htsine"] = hilbert["sine"]          # 正弦波值
        dataframe["htleadsine"] = hilbert["leadsine"]  # 领先正弦波值

        # =====================================================================
        # 第四大类：K线形态识别（Pattern Recognition）—— 以下均已注释
        # TA-Lib 可以自动识别几百种经典的日本蜡烛图形态。
        # 返回值含义：100 = 看涨形态出现，-100 = 看跌形态出现，0 = 没有形态
        # =====================================================================

        # --- 看涨K线形态（Bullish Patterns，已注释）---
        # # Hammer（锤子线）：下影线很长，实体很小，在底部出现 → 看涨反转
        # dataframe["CDLHAMMER"] = ta.CDLHAMMER(dataframe)
        # # Inverted Hammer（倒锤子线）：上影线很长，底部出现 → 看涨反转
        # dataframe["CDLINVERTEDHAMMER"] = ta.CDLINVERTEDHAMMER(dataframe)
        # # Dragonfly Doji（蜻蜓十字星）：开盘=收盘=最高，长下影 → 看涨反转
        # dataframe["CDLDRAGONFLYDOJI"] = ta.CDLDRAGONFLYDOJI(dataframe)
        # # Piercing Line（穿刺线）：阴线后大阳线，收盘超过前阴线中点 → 看涨
        # dataframe["CDLPIERCING"] = ta.CDLPIERCING(dataframe)
        # # Morning Star（晨星）：三根K线组成的底部反转形态 → 强看涨
        # dataframe["CDLMORNINGSTAR"] = ta.CDLMORNINGSTAR(dataframe)
        # # Three White Soldiers（三白兵）：三根连续大阳线 → 强看涨趋势确立
        # dataframe["CDL3WHITESOLDIERS"] = ta.CDL3WHITESOLDIERS(dataframe)

        # --- 看跌K线形态（Bearish Patterns，已注释）---
        # # Hanging Man（上吊线）：和锤子线一样但出现在顶部 → 看跌反转
        # dataframe["CDLHANGINGMAN"] = ta.CDLHANGINGMAN(dataframe)
        # # Shooting Star（射击之星）：长上影，小实体，顶部出现 → 看跌反转
        # dataframe["CDLSHOOTINGSTAR"] = ta.CDLSHOOTINGSTAR(dataframe)
        # # Gravestone Doji（墓碑十字星）：开盘=收盘=最低，长上影 → 看跌反转
        # dataframe["CDLGRAVESTONEDOJI"] = ta.CDLGRAVESTONEDOJI(dataframe)
        # # Dark Cloud Cover（乌云盖顶）：阳线后大阴线，收盘低于前阳线中点 → 看跌
        # dataframe["CDLDARKCLOUDCOVER"] = ta.CDLDARKCLOUDCOVER(dataframe)
        # # Evening Doji Star（黄昏十字星）：顶部十字星反转 → 强看跌
        # dataframe["CDLEVENINGDOJISTAR"] = ta.CDLEVENINGDOJISTAR(dataframe)
        # # Evening Star（黄昏之星）：三根K线组成的顶部反转 → 强看跌
        # dataframe["CDLEVENINGSTAR"] = ta.CDLEVENINGSTAR(dataframe)

        # --- 双向K线形态（Bullish/Bearish，已注释）---
        # 这些形态的返回值：正数 = 看涨，负数 = 看跌，0 = 没有
        # # Three Line Strike（三线反击）
        # dataframe["CDL3LINESTRIKE"] = ta.CDL3LINESTRIKE(dataframe)
        # # Spinning Top（纺锤线）：小实体、长上下影 → 方向不明确
        # dataframe["CDLSPINNINGTOP"] = ta.CDLSPINNINGTOP(dataframe)
        # # Engulfing（吞没形态）：后一根完全包住前一根 → 强反转信号
        # dataframe["CDLENGULFING"] = ta.CDLENGULFING(dataframe)
        # # Harami（孕线）：后一根被前一根完全包住 → 趋势可能反转
        # dataframe["CDLHARAMI"] = ta.CDLHARAMI(dataframe)
        # # Three Outside Up/Down（外侧三K线）
        # dataframe["CDL3OUTSIDE"] = ta.CDL3OUTSIDE(dataframe)
        # # Three Inside Up/Down（内侧三K线）
        # dataframe["CDL3INSIDE"] = ta.CDL3INSIDE(dataframe)

        # --- Heikin Ashi（平均K线图，已注释）---
        # Heikin Ashi 是一种"平滑化"的K线，公式重新计算开高低收，
        # 使趋势更明显，减少噪音。常用于趋势跟踪策略。
        # heikinashi = qtpylib.heikinashi(dataframe)
        # dataframe["ha_open"] = heikinashi["open"]
        # dataframe["ha_close"] = heikinashi["close"]
        # dataframe["ha_high"] = heikinashi["high"]
        # dataframe["ha_low"] = heikinashi["low"]

        # --- 从订单簿获取最优买卖价（已注释）---
        # 这段代码仅在实盘或模拟盘（live / dry_run）运行时有效，
        # 用于获取当前订单簿中的最高买价和最低卖价。
        # ⚠️ 回测模式下 self.dp 不可用，所以需要先判断。
        """
        if self.dp:
            if self.dp.runmode.value in ("live", "dry_run"):
                ob = self.dp.orderbook(metadata["pair"], 1)
                dataframe["best_bid"] = ob["bids"][0][0]  # 最高买价
                dataframe["best_ask"] = ob["asks"][0][0]  # 最低卖价
        """

        # 返回添加了所有技术指标的 DataFrame，供后续信号判断使用
        return dataframe

    # =========================================================================
    # ====================== 核心方法二：定义买入信号 ==========================
    # =========================================================================
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        根据技术指标，在 DataFrame 中标记买入（做多入场）信号。
        
        当条件满足时，在 'enter_long' 列写入 1（表示"买入"），
        不满足时该位置为 NaN（Freqtrade 会忽略）。
        
        参数说明：
        :param dataframe: 已经通过 populate_indicators() 添加了所有指标的 DataFrame
        :param metadata:  附加信息，metadata["pair"] 是当前交易对名称
        :return: 标记了买入信号的 DataFrame
        """

        # -----------------------------------------------------------------
        # dataframe.loc[条件, 目标列] = 值
        # 这是 pandas 的语法：在满足"条件"的那些行中，把"目标列"设为指定的"值"。
        #
        # & 符号表示"并且"（AND），所有条件必须同时满足。
        # -----------------------------------------------------------------

        dataframe.loc[
            (
                # =============================================================
                # 条件1（信号）：RSI 从下方向上穿越 buy_rsi 阈值
                # crossed_above(序列A, 阈值) → 当序列A从低于阈值变成高于阈值时返回 True。
                # 通俗理解：RSI 之前一直低于 buy_rsi（如30），现在涨上去了，
                #          说明市场从"超卖"状态开始反弹。
                # self.buy_rsi.value 是策略参数中定义的买入RSI阈值（默认30）。
                # =============================================================
                (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)) &

                # =============================================================
                # 条件2（过滤器）：TEMA 在布林带中轨之下
                # 含义：趋势指标确认价格仍在相对低位，不是追高买入。
                # 如果 TEMA 已经高于中轨，说明价格已经涨了一段，不再追入。
                # =============================================================
                (dataframe["tema"] <= dataframe["bb_middleband"]) &

                # =============================================================
                # 条件3（过滤器）：TEMA 正在上升
                # dataframe["tema"].shift(1) 是上一根K线的 TEMA 值。
                # 当前TEMA > 上一根TEMA → TEMA 在向上走 → 趋势在好转。
                # 这确保我们不在下跌趋势中接飞刀。
                # =============================================================
                (dataframe["tema"] > dataframe["tema"].shift(1)) &

                # =============================================================
                # 条件4（保护条件）：成交量大于零
                # 确保当前K线有实际交易发生，避免在停盘或无交易时段产生虚假信号。
                # =============================================================
                (dataframe["volume"] > 0)
            ),
            "enter_long"] = 1  # 在满足以上所有条件的行，标记为 1 → "做多入场"

        # -----------------------------------------------------------------
        # 做空入场信号（已注释，仅在期货/保证金模式下使用）
        # 做空的逻辑和做多刚好相反：RSI 超买时开空单。
        # -----------------------------------------------------------------
        """
        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi.value)) &
                (dataframe["tema"] > dataframe["bb_middleband"]) &    # TEMA在布林带上轨之上
                (dataframe["tema"] < dataframe["tema"].shift(1)) &   # TEMA正在下跌
                (dataframe['volume'] > 0)
            ),
            'enter_short'] = 1  # 标记为做空入场
        """

        return dataframe

    # =========================================================================
    # ====================== 核心方法三：定义卖出信号 ==========================
    # =========================================================================
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        根据技术指标，在 DataFrame 中标记卖出（做多出场）信号。
        
        当条件满足时，在 'exit_long' 列写入 1（表示"卖出"），
        不满足时该位置为 NaN（Freqtrade 会忽略）。
        
        参数说明：
        :param dataframe: 包含所有指标的 DataFrame
        :param metadata:  附加信息字典
        :return: 标记了卖出信号的 DataFrame
        """

        dataframe.loc[
            (
                # =============================================================
                # 条件1（信号）：RSI 从下方向上穿越 sell_rsi 阈值
                # 和买入逻辑类似，但阈值更高（如70）。
                # RSI 突破 sell_rsi → 市场进入"超买"状态 → 考虑卖出止盈。
                # =============================================================
                (qtpylib.crossed_above(dataframe["rsi"], self.sell_rsi.value)) &

                # =============================================================
                # 条件2（过滤器）：TEMA 在布林带中轨之上
                # 含义：确认价格确实处于相对高位，不是在底部误判。
                # =============================================================
                (dataframe["tema"] > dataframe["bb_middleband"]) &

                # =============================================================
                # 条件3（过滤器）：TEMA 正在下跌
                # 当前TEMA < 上一根TEMA → 趋势开始转头向下。
                # 这是"上涨乏力"的信号，趁还有利润时获利了结。
                # =============================================================
                (dataframe["tema"] < dataframe["tema"].shift(1)) &

                # =============================================================
                # 条件4（保护条件）：成交量大于零
                # =============================================================
                (dataframe["volume"] > 0)
            ),
            "exit_long"] = 1  # 在满足条件的行，标记为 1 → "做多出场（卖出）"

        # -----------------------------------------------------------------
        # 做空出场信号（已注释，仅在期货/保证金模式下使用）
        # 做空出场 = 平空单，逻辑是 RSI 回到低位时买回。
        # -----------------------------------------------------------------
        """
        dataframe.loc[
            (
                (qtpylib.crossed_above(dataframe["rsi"], self.buy_rsi.value)) &
                (dataframe["tema"] <= dataframe["bb_middleband"]) &
                (dataframe["tema"] > dataframe["tema"].shift(1)) &
                (dataframe['volume'] > 0)
            ),
            'exit_short'] = 1
        """

        return dataframe