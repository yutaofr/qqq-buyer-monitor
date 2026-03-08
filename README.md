# QQQ Buy-Signal Monitor (with Options Wall Confirmation)

一个基于五大维度市场信号（现货+情绪）并引入期权墙（Options Wall）硬否决逻辑的 QQQ 买点监控系统。

## 🌟 核心特性

- **双层分析架构 (Tier-1 & Tier-2)**:
  - **Tier-1 (梯度打分)**: 综合 52周回撤、MA200 偏离度、VIX 恐慌指数、CNN Fear & Greed 指数、市场广度（涨跌比）。
  - **Tier-2 (期权确认)**: 实时计算 **Put Wall (支撑墙)**、**Call Wall (压力墙)** 与 **Gamma Flip (多空分界点)**。
- **硬否决逻辑 (Standard Rule)**: 即使 Tier-1 得分再高，若价格跌破 Put Wall，系统将强制否决 `TRIGGERED` 信号，转为 `WATCH`，有效规避流动性崩塌。
- **智能降级**: 任意单一数据源（如 CNN 或某个 Index）失效时，系统自动切换至代理逻辑（Proxy），确保核心监控不中断。
- **现代化技术栈**: Python 3.12, 异步数据采集 (yfinance/Black-Scholes), SQLite 历史持久化, Docker 容器化部署。

## 📊 信号分级

| 状态 | 说明 | 行动建议 |
|:---:|---|---|
| **TRIGGERED** | 现货极端超卖 + 情绪极度恐慌 + 期权墙支撑稳固 | 极高胜率买点，适合底仓入场 |
| **WATCH** | 部分信号达标，或处于跌破支撑后的观察期 | 关注市场企稳，等待期权墙收复 |
| **NO_SIGNAL** | 市场处于常规波动或上涨趋势中 | 继续持有，无需操作 |

## 🚀 快速开始 (Docker)

项目完全兼容 Docker，无需本地配置 Python 环境。

### 1. 运行实时监控
每天收盘后运行，获取当前买点建议：
```bash
docker-compose run --rm app python -m src.main
```

### 2. 运行历史回测 (2022-2025)
验证信号在过去三年大熊市中的表现：
```bash
docker-compose run --rm app python src/backtest.py
```

### 3. 运行测试套件
```bash
docker-compose up --build test
```

## 🛠️ 技术细节

### 数据来源
- **价格/均线**: Yahoo Finance (`yfinance`)
- **情绪指数**: CNN Fear & Greed (内部 API)
- **期权链数据**: yfinance (实时数据)
- **市场广度**: NYSE Net Advances (`^ADD`)

### 核心算法
- **Gamma Flip**: 通过期权链各行权价的 Gamma 分布进行零点插值计算，定位市场波动性由收缩转为放大的临界点。
- **Support Veto**: 基于做市商 Delta 对冲压力。当价格低于 Put Wall 时，做市商不得不随着下跌卖出更多期货以对冲，形成螺旋下行压力，此时买入风险极大。

## 📈 后台回测表现 (M4 阶段)

回测结果显示，引入 **Tier-2 期权确认层** 后，系统成功拦截了 2022 年阴跌过程中 **53% 的假底部信号**，将买点精确锁定在 2022 年 5月、6月和 10月的绝对底部区域。

## 📄 开源协议
MIT License
