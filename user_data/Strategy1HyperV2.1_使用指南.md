# Strategy1HyperV2.1 使用指南

> 这是一份给**完全不懂量化交易**的人看的文档。  
> 不需要会编程，不需要懂金融，看完就能用。

---

## 目录

1. [这个策略是干什么的](#1-这个策略是干什么的)
2. [回测成绩单](#2-回测成绩单)
3. [它是怎么买卖的](#3-它是怎么买卖的)
4. [怎么在电脑上跑起来](#4-怎么在电脑上跑起来)
5. [怎么修改交易对](#5-怎么修改交易对)
6. [怎么调整参数](#6-怎么调整参数)
7. [常见问题](#7-常见问题)

---

## 1. 这个策略是干什么的

### 用一句话说

> 自动帮你买卖比特币、以太坊等加密货币，**只在大趋势上涨的时候抄底买入**，涨了就卖，跌多了就割。

### 为什么能赚钱

市场上大多数散户看到跌了就买，**不管趋势**——结果越买越跌。  
这个策略反其道而行：**先判断大方向在涨，然后趁回调下跌时买入**，等反弹后卖出。

```
市场在涨（趋势向上）
    ↓
突然跌了一下（回调）
    ↓
我们在跌到底部反弹的瞬间买入 ← 策略做的事
    ↓
市场恢复上涨
    ↓
涨够了就卖出
```

### 和银行理财比

| 对比 | 银行理财 | 这个策略 |
|------|----------|----------|
| 年化收益 | ~2-3% | ~4.5% |
| 本金风险 | 极低 | 最大回撤 1.4% |
| 流动性 | 锁定期 | 随时可停 |

> 当然，过去不代表未来。但 18 个月的数据显示这个策略是稳健的。

---

## 2. 回测成绩单

> 回测 = 拿历史数据假装交易，看看这个策略在过去能不能赚钱。  
> 回测区间：2025 年 1 月 ～ 2026 年 7 月（18 个月）

### 核心数据

| 指标 | 数值 | 大白话翻译 |
|------|------|------------|
| **总盈亏** | **+6.89%** | 投 1000 元，赚了 69 元 |
| **交易次数** | 22 笔 | 大约每月交易 1 次 |
| **胜率** | 77.3% | 每 10 笔交易里，7 笔赚钱 |
| **最大回撤** | 1.38% | 最惨的时候只亏了本金的 1.4% |
| **止损次数** | 1 笔 | 22 笔里只有 1 笔亏到了止损线 |
| **年化收益** | 4.50% | 假设趋势延续，一年大约赚 4.5% |

### 交易品种表现

| 币种 | 交易次数 | 盈亏 | 胜率 |
|------|----------|------|------|
| ETH/USDT | 10 笔 | +3.41% | 80% |
| BTC/USDT | 11 笔 | +2.68% | 72.7% |
| OKB/USDT | 1 笔 | +0.79% | 100% |

### 怎么卖出的

| 卖出方式 | 次数 | 平均盈亏 | 说明 |
|----------|------|----------|------|
| 追踪止损 | 16 笔 | +1.19% | 涨了又回落，自动卖出锁定利润 |
| ROI 止盈 | 5 笔 | +1.10% | 持有够久，达到目标利润 |
| 硬止损 | 1 笔 | -4.10% | 买错了，强制割肉 |

---

## 3. 它是怎么买卖的

### 3.1 买入条件（六个条件，全部满足才买）

想象你去买菜，你不会"看到菜就买"对吧？这个策略也一样，要同时满足六个条件才出手：

| # | 条件 | 通俗解释 |
|---|------|----------|
| 1 | **市场在涨** | 价格在长期均线之上。就好比你确认这家菜市场人气很旺，不是快倒闭了。 |
| 2 | **跌过头了** | RSI 指标显示之前抛售过度了。相当于菜价打了 7 折。 |
| 3 | **足够便宜** | 价格跌到了布林带下轨。相当于这个菜是今天市场里最便宜的几个摊位。 |
| 4 | **有人抄底** | 成交量放大。便宜菜有人抢着买，说明大家都觉得值。 |
| 5 | **趋势够强** | ADX 指标确认不是在横盘震荡。人气旺但不是虚假繁荣。 |
| 6 | **数据正常** | K线有效，没有停牌。确认交易所在正常工作。 |

### 3.2 卖出条件（五层保护）

这个策略不急着卖，但有好几层保护防止亏钱：

```
赚越多 → 保护越紧

        │  盈利 5%+ → 最多允许回吐 2%
        │  盈利 3%+ → 最多允许回吐 2%
        │  盈利 2%+ → 止损提到开仓价（保本）
        │  盈利 1%+ → 止损缩到 -1.5%
        ▼  亏损 4%  → 无条件割肉
```

### 3.3 一个真实的例子

```
2025 年 3 月的 BTC 交易：

第 1 步：BTC 从 95000 跌到 82000（回调）
第 2 步：RSI 跌到 24（超卖）
第 3 步：价格碰到布林带下轨（便宜）
第 4 步：放量反弹（有人抄底）
第 5 步：在 83000 买入（RSI 从 24 涨回 26，触发入场）

第 6 步：持有 2 天，价格涨到 85000（+2.4%）
第 7 步：止盈触发，自动在 84900 卖出

结果：买入 83000 → 卖出 84900，盈利 +2.3%
```

---

## 4. 怎么在电脑上跑起来

### 4.1 回测（验证策略）

回测就是用历史数据模拟交易，看策略能不能赚钱。

打开 PowerShell，依次执行：

```powershell
# 1. 进入项目目录
cd D:\freqtrade

# 2. 跑回测
.\freqtrade-env\Scripts\freqtrade.exe backtesting `
  --config config.json `
  --strategy Strategy1HyperV21 `
  --timerange 20250101- `
  --data-format-ohlcv feather
```

> 参数说明：
> - `--strategy Strategy1HyperV21` = 用 V2.1 策略
> - `--timerange 20250101-` = 从 2025 年 1 月 1 日到现在
> - 跑完会在终端输出完整报告

### 4.2 模拟交易（在网页上实时看）

```powershell
# 1. 先修改 config.json
#    找到 "strategy": "..." 改成 "strategy": "Strategy1HyperV21"

# 2. 启动交易模式
cd D:\freqtrade
.\freqtrade-env\Scripts\freqtrade.exe trade --config config.json

# 3. 打开浏览器
http://127.0.0.1:8080

# 4. 登录
# Bot Name: 随便填
# API Url:  http://127.0.0.1:8080
# Username: yuanye
# Password: 11223344
```

> ⚠️ 当前是模拟盘（dry_run=true），不会真的花钱交易。

### 4.3 自动优化参数

```powershell
cd D:\freqtrade
.\freqtrade-env\Scripts\freqtrade.exe hyperopt `
  --config config.json `
  --strategy Strategy1HyperV21 `
  --timerange 20250101-20250601 `
  --spaces buy `
  --epochs 200 `
  --hyperopt-loss SharpeHyperOptLossDaily `
  --data-format-ohlcv feather -j 4
```

> 200 轮自动测试大概要跑 5-10 分钟。  
> 跑完后最优参数会自动保存。

---

## 5. 怎么修改交易对

打开 `config.json`，找到这一段：

```json
"pair_whitelist": [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "OKB/USDT:USDT"
]
```

### 添加新的交易对

比如加上 SOL：

```json
"pair_whitelist": [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT",
    "OKB/USDT:USDT",
    "SOL/USDT:USDT"
]
```

然后下载新币种数据：

```powershell
cd D:\freqtrade
.\freqtrade-env\Scripts\freqtrade.exe download-data `
  --config config.json `
  --pairs SOL/USDT:USDT `
  --timeframes 5m `
  --timerange 20250101- `
  --trading-mode futures `
  --data-format-ohlcv feather
```

### 去掉某个交易对

直接删掉那一行就行：

```json
"pair_whitelist": [
    "BTC/USDT:USDT",
    "ETH/USDT:USDT"
]
```

---

## 6. 怎么调整参数

打开 `strategies/Strategy1HyperV2.1.py`，找到这段：

```python
buy_rsi = IntParameter(15, 40, default=26, space="buy")
buy_bb  = DecimalParameter(0.1, 0.5, default=0.17, decimals=2, space="buy")
buy_adx = IntParameter(15, 40, default=31, space="buy")
```

### 想交易更频繁 → 放宽参数

```python
buy_rsi = IntParameter(15, 40, default=30, space="buy")  # 26→30（不用跌那么深就买）
buy_bb  = DecimalParameter(0.1, 0.5, default=0.30, decimals=2, space="buy")  # 0.17→0.30（不用那么靠近下轨）
buy_adx = IntParameter(15, 40, default=25, space="buy")  # 31→25（不用趋势那么强）
```

### 想更保守 → 收紧参数

```python
buy_rsi = IntParameter(15, 40, default=22, space="buy")  # 更要超卖
buy_bb  = DecimalParameter(0.1, 0.5, default=0.12, decimals=2, space="buy")  # 更接近下轨
buy_adx = IntParameter(15, 40, default=35, space="buy")  # 更强的趋势
```

### 想调止损

```python
stoploss = -0.04  # 改成 -0.03（最多亏 3%）或 -0.05（最多亏 5%）
```

### 想调止盈

```python
minimal_roi = {
    "120": 0.03,   # 2小时 → 3%
    "60":  0.02,   # 1小时 → 2%
    "30":  0.01,   # 30分钟 → 1%
    "0":   0.005,  # 无条件 → 0.5%
}
# 比如想多赚一点，可以把 0.005 改成 0.01（无条件要赚 1% 才卖）
```

改完记得跑回测验证！

---

## 7. 常见问题

### Q: 为什么交易这么少（18 个月才 22 笔）？

A: 这是设计如此。策略的目标是"高胜率、低风险"，而不是"高频交易"。六个条件全部满足才出手，所以机会不多，但每次出手质量很高（77% 胜率）。

如果想增加频率，参考第 6 节的"放宽参数"。

### Q: 为什么不做空（下跌也能赚钱）？

A: V2.1 版本只做多。后续可以增加做空功能。想加的话把 `can_short = False` 改成 `True`，然后添加做空条件。

### Q: 代理连不上怎么办？

A: 回测和超参优化依赖代理（`127.0.0.1:7890`）获取市场费率。如果代理没开，会报错。确保代理软件（Clash/V2Ray）在运行。

### Q: 怎么从实盘切回模拟？

A: 修改 `config.json`：
```json
"dry_run": true,     // true=模拟, false=实盘
```

### Q: 这个策略能保证赚钱吗？

A: **不能。** 过去的表现不代表未来。18 个月的回测显示盈利，但市场会变化。建议先用模拟盘跑一段时间，观察实际表现。

### Q: 我有其他问题怎么办？

A: 策略文件 `Strategy1HyperV2.1.py` 里有更详细的注释（~380 行）。也可以查 Freqtrade 官方文档：https://www.freqtrade.io

---

## 快速参考

```powershell
# 回测
.\freqtrade-env\Scripts\freqtrade.exe backtesting --config config.json --strategy Strategy1HyperV21 --timerange 20250101- --data-format-ohlcv feather

# 超参优化
.\freqtrade-env\Scripts\freqtrade.exe hyperopt --config config.json --strategy Strategy1HyperV21 --timerange 20250101-20250601 --spaces buy --epochs 200 --hyperopt-loss SharpeHyperOptLossDaily --data-format-ohlcv feather -j 4

# 启动模拟交易
.\freqtrade-env\Scripts\freqtrade.exe trade --config config.json
# 然后打开 http://127.0.0.1:8080
```

---

> 📌 **记住最核心的一句话**：  
> 这个策略的哲学不是"预测市场"，而是"只在有利的时机出手，错了就认输，对了就多赚"。
