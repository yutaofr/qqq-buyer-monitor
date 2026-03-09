# QQQ Buy-Signal Monitor (with Options Wall Confirmation)

一个基于五大维度市场信号（现货+情绪）并引入期权墙（Options Wall）硬否决逻辑的 QQQ 买点监控系统。

## 🌟 核心特性 (v3.0 最新架构)

- **Tier-0 (大周期与宏观防御)**: 
  - **信用利差熔断**: 实时监控 FRED 信用利差。若 >500 bps (流动性危机)，强制熔断所有买入信号。
  - **ERP 模式开关**: 基于股权风险溢价 (1/ForwardPE - US10Y) 切换模式：
    - **🛡️ 防守模式 (ERP < 1%)**: 泡沫背景下大幅收紧买入标准 (触发阈值 85)。
    - **💎 击球区模式 (ERP > 5%)**: 极端低估背景下允许提前入场 (触发阈值 65)，不放过百年一遇的大底。
- **Tier-1 (基础情绪层)**: 综合 52周回撤、MA200 偏离度、VIX 指数、CNN Fear & Greed 指数、市场广度（涨跌比）。
- **Tier-1.5 (价值与背离红利)**: 
  - **FCF Yield 绝对估值**: 当收益率 > 4.5% 时给予 +15 分基础红利，承认科技股现金流的压舱石作用。
  - **底背离引擎**: 捕捉价格与 VIX/广度/RSI 以及**盈利预测 (Earnings Revision)** 的分歧。当价格创新低但分析师上修比例 > 50% 时，提供高额红利得分。
- **Tier-2 (期权确认与否决)**: 实时计算 **Put Wall (支撑墙)**、**Call Wall (压力墙)** 与 **Gamma Flip**。
- **硬否决逻辑 (Standard Rule)**: 即使前序得分再高，若价格低于 Put Wall，做市商的对冲压力会形成螺旋式下跌，系统强制否决 `TRIGGERED`。
- **现代化技术栈**: Python 3.12, 异步数据采集, SQLite 历史持久化, Docker 容器化, **87 个单元/集成测试用例**。

## 📊 信号分级

| 状态 | 色彩 | 说明 | 行动建议 |
21: |:---:|:---:|---|---|
22: | **STRONG_BUY** | 紫色 | **强烈买入**：价格不仅超卖且伴随基本面（盈利预期）强力支撑 | 极具价值的长线击球点 |
23: | **TRIGGERED** | 绿色 | **触发买点**：各项指标进入极限值且期权墙结构支持 | 适合分批建仓底部区域 |
24: | **WATCH** | 黄色 | **观察区**：信号显现但尚未共振，或被硬否决层拦截 | 保持密切关注，不在此左侧抄底 |
25: | **NO_SIGNAL** | 红色 | **未触发**：市场处于常态波动或高位 | 耐心等待，无买入机会 |

## 🚀 快速开始 (Docker)

项目完全兼容 Docker，无需本地配置 Python 环境。

### 1. 运行实时监控
```bash
docker-compose run --rm app python -m src.main
```

### 2. 运行长线回测 (2000-2026)
```bash
docker-compose run --rm app python src/backtest.py
```

### 3. 运行自动化测试
```bash
docker-compose up --build test
```

## 🛠️ 技术细节

### 数据来源
- **价格/期权链**: Yahoo Finance (`yfinance`) - 免 API Key
- **宏观/国债**: FRED (Public CSV) & `yfinance`
- **盈利预期**: 综合分析师底背离模型 (Synthesized Revision Breadth)
- **情绪指数**: CNN Money API

### 核心亮点
- **Strong Buy 升级机制**: 仅当 Tier-1 触发、ERP 处于健康模式、且出现**重大底背离**（如市场广度、VIX 或分析师盈利预期上修）时，信号才会升级为紫色 `STRONG_BUY`。
- **四重背离模型**: 系统集成技术面 (Breadth, VIX, RSI) 与基本面 (Revision) 四个维度的背离监测，寻找价格与宏观/微观参与度的终极分歧。
- **2026 回测洞察**: 2026 年初 QQQ 的多次 5-6% 回调被系统识别为“非结构性恐慌/非深度折扣”，在保持 **NO_SIGNAL** 状态下成功规避了多次震荡，体现了极高的保守可靠性。

## 📄 开源协议
MIT License

