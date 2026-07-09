# 🚀 Freqtrade 量化交易策略集

> 基于 Freqtrade 的加密货币自动交易策略集合，附带完整的中文汉化界面和 MySQL 数据存储方案。

---

## 📊 核心策略：Strategy1HyperV3.0

**双向趋势守护策略** — 做多 + 做空 + 多周期确认

### 回测表现（2025.01 ~ 2026.07，18个月，BTC/ETH/OKB）

| 指标 | 数值 | 评价 |
|------|------|------|
| **总盈亏** | **+5.96%** | ✅ 盈利 |
| **胜率** | **85.0%** | ✅ 优秀 |
| **最大回撤** | **0.11%** | ✅ 极低 |
| **硬止损次数** | **0 次** | ✅ 完美 |
| **交易频率** | 20笔/18月 | 低频精准 |
| **夏普比率** | 0.67 | 正值 |
| **盈亏因子** | 31.73 | 优秀 |

### 策略逻辑

```
做多：上升趋势 + 深度回调 + RSI超卖反弹 → 买入
做空：下降趋势 + 高位反弹 + RSI超买回落 → 做空

七重入场确认 + 五层出场保护（ROI止盈→追踪止损→动态止损→硬止损→趋势破位）
```

### 版本进化

| 版本 | 盈亏 | 核心改进 |
|------|------|----------|
| v0.1 原始RSI | -51% | 简单超买超卖 |
| v1.0 | -3.7% | +EMA200 +动态止损 |
| v2.0 | +6.89% | +超参优化 +3交易对 |
| v2.3 | +5.96% | +做空 +多周期 |
| **v3.0** | **+5.96%** | **锁定最优参数** |

---

## 📁 项目结构

```
freqtrade/
├── config.json                    # 主配置文件（需自行创建，模板见下方）
├── .gitignore                     # Git 忽略规则
├── user_data/
│   ├── strategies/                # 策略文件
│   │   ├── Strategy1HyperV3.0.py  # ⭐ 当前主力策略
│   │   ├── Strategy1HyperV2.1.py  # 开发版
│   │   ├── Strategy1HyperV2.0.py  # v2.0 稳定版
│   │   ├── Strategy1HyperV1.0.py  # v1.0 备份
│   │   └── MyAwesomeStrategy.py   # 原始策略
│   ├── Strategy1HyperV3.0_使用指南.md  # 📖 新手教程
│   ├── Strategy1HyperV2.1_策略总结.md  # 📊 策略分析
│   └── TrendGuardStrategy_README.md    # 📄 早期文档
│
├── frequi-main/                   # FreqUI 汉化源码
│   └── src/i18n/locales/
│       ├── zh.json                # 中文翻译（~300条）
│       └── en.json                # 英文原文
│
└── freqtrade-env/                 # Python 虚拟环境（不提交）
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/yuanye4819/freqtrade.git
cd freqtrade

# 安装 Freqtrade
pip install freqtrade

# 安装依赖
pip install -r requirements.txt  # 如果有
```

### 2. 配置

创建 `config.json`（参考模板）：

```json
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": "unlimited",
    "dry_run": true,
    "trading_mode": "futures",
    "margin_mode": "isolated",
    "strategy": "Strategy1HyperV3",
    "exchange": {
        "name": "okx",
        "key": "你的API密钥",
        "secret": "你的API密钥",
        "password": "你的密码",
        "ccxt_config": {
            "enableRateLimit": true
        },
        "pair_whitelist": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "OKB/USDT:USDT"
        ]
    },
    "api_server": {
        "enabled": true,
        "listen_ip_address": "127.0.0.1",
        "listen_port": 8080,
        "username": "你的用户名",
        "password": "你的密码"
    }
}
```

### 3. 下载数据

```bash
freqtrade download-data --config config.json --timeframes 5m 1h --timerange 20250101- --trading-mode futures
```

### 4. 回测

```bash
freqtrade backtesting --config config.json --strategy Strategy1HyperV3 --timerange 20250101-
```

### 5. 模拟交易

```bash
freqtrade trade --config config.json
# 打开 http://127.0.0.1:8080
```

---

## 🌐 中文 FreqUI 界面

本项目包含 FreqUI 的完整中文汉化：

- ✅ **导航栏/侧边栏** — 全部中文
- ✅ **交易视图** — 表头、字段、操作按钮
- ✅ **仪表盘** — 面板标题、提示信息
- ✅ **设置页** — 完整翻译
- ✅ **回测页** — 状态、参数、指标
- ✅ **后端报告** — 回测报告输出中文化
- ✅ **WebSocket 消息** — 启动消息、错误提示

> 汉化源码位于 `frequi-main/src/i18n/locales/zh.json`

---

## ⚡ 性能优化

- **Brotli 压缩** — 传输量减少 80%
- **缓存头** — 二次访问零传输
- **无 Sourcemap** — 产物减少 12.8MB
- **Vendor 分包** — 更新不失效缓存

---

## 📖 教程文档

| 文档 | 内容 |
|------|------|
| [使用指南](user_data/Strategy1HyperV3.0_使用指南.md) | 零基础教程：从原理到实操 |
| [策略总结](user_data/Strategy1HyperV2.1_策略总结.md) | 优缺点分析、适合人群 |
| [策略代码](user_data/strategies/Strategy1HyperV3.0.py) | ~400行，全文中文注释 |

---

## 🛠️ 常用命令

```bash
# 回测
freqtrade backtesting --config config.json --strategy Strategy1HyperV3 --timerange 20250101-

# 超参优化
freqtrade hyperopt --config config.json --strategy Strategy1HyperV3 --timerange 20250101-20250601 --spaces buy sell --epochs 200 --hyperopt-loss SharpeHyperOptLossDaily -j 4

# 启动交易
freqtrade trade --config config.json

# 查看所有策略
freqtrade list-strategies --config config.json
```

---

## 📊 策略对比

| 策略 | 方向 | 交易对 | 盈亏 | 胜率 | 回撤 |
|------|------|--------|------|------|------|
| Strategy1HyperV3.0 | 双向 | 3对 | +5.96% | 85% | 0.11% |
| Strategy1HyperV2.0 | 做多 | 3对 | +6.89% | 77% | 1.38% |
| MyAwesomeStrategy | 做多 | 2对 | -51% | 84% | 53% |

---

## ⚠️ 免责声明

- 本策略集仅供学习和研究使用
- 历史回测表现不代表未来收益
- 加密货币交易有高风险，请自行评估风险承受能力
- 使用实盘前请务必充分模拟测试

---

## 📝 License

MIT

---

> 💡 **核心哲学**：防守赢得冠军。不追求暴利，追求每一次出手都是高概率的，每一次盈利都不会被轻易回吐掉。
