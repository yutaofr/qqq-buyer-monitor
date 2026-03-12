# QQQ Buy-Signal Monitor (v4.2 Evolution)

一个基于五大维度市场信号（现货+情绪）并引入 **宏观引力因子** 与 **动态环境自适应** 逻辑的 QQQ 买点监控系统。

> [!IMPORTANT]
> **v4.2 核心突破**: 系统已从单纯的“恐慌计”进化为具有“环境感知”能力的综合监控器，对历史重大底部的捕捉率已提升至 **92.6%**。

---

## 🌟 核心特性 (v4.2 架构)

### 1. Tier-0 (宏观防御与 ERP)
- **信用利差熔断**: 实时监控 FRED 高收益债利差 (BAMLH0A0HYM2)。若 >500 bps (流动性危机)，强制熔断。
- **ERP 模式开关**: 基于股权风险溢价 (1/FwdPE - TIPS) 切换：
  - **🛡️ 防守模式 (ERP < 1%)**: 估值过高时收紧触发门槛。
  - **💎 击球区模式 (ERP > 5%)**: 极端低估时允许左侧提前入场。

### 2. Tier-1 (动态情绪层 - Phase 1)
- **Market Regime Filter**: 自动识别 **QUIET / NORMAL / STORM** 三种波动模式。
- **Adaptive Z-Scores**: 52周回撤与 VIX 均基于 120D 滚动窗口进行标准化，在低波动环境下也能灵敏探测相对极值。
- **Regime Weighting**: 在 QUIET 模式下自动调高“市场广度”权重，捕捉无量阴跌底。

### 3. Tier-1.5 (环境因子与背离 - Phase 2 & 3)
- **Macro Gravity**: 
  - **Fed Net Liquidity**: 接入美联储负债表、TGA 及 RRP 数据，捕捉流动性拐点得分。
  - **MOVE Index**: 引入债市波动率，识别债市恐慌见顶带来的权益类机会。
- **Smart Momentum**:
  - **MFI (Money Flow Index)**: 结合价格与成交量，识别资金在缩量下跌中的提前进场（底背离）。
  - **Sector Rotation**: 监控 **XLP/QQQ (防御/成长比)**。当资金从防御板块回流成长股时触发红利。

### 4. Tier-2 (期权墙确认 - Hard Veto)
- **VPVR & Options Chain**: 计算 **Put Wall** (支撑)、**Call Wall** (阻力) 与 **Gamma Flip**。
- **螺旋否决**: 若价格低于 Put Wall 或处于 **负 Gamma** 区域，系统将自动否决 `TRIGGERED` 信号，防止陷入 Delta 螺旋。

---

## 📊 信号分级

| 状态 | 说明 |
|:---:|---|
| **STRONG_BUY** | **强烈买入**：Tier-1 触发且伴随强力基本面（盈利预期、MFI）底背离。 |
| **TRIGGERED** | **触发买点**：各项指标进入极限值且期权墙结构提供支撑。 |
| **WATCH** | **观察期**：信号显现但尚未共振，或被硬否决层拦截。 |
| **NO_SIGNAL** | **未触发**：市场处于常态或高位，耐心等待。 |

---

## 🚀 快速开始 (Docker)

### 1. 配置 API Key
在根目录创建 `.env` 文件，填入您的 FRED API Key：
```bash
FRED_API_KEY=your_fred_api_key_here
```

### 2. 启动监控
```bash
# 获取实时信号报告
docker-compose run --rm app python -m src.main

# 以 JSON 格式输出 (适合自动化集成)
docker-compose run --rm app python -m src.main --json
```

### 3. 运行回测
```bash
# 运行 1999-2026 全量回测并生成可视化图表
docker-compose run --rm app python -m src.backtest
```

---

## 🛠️ 核心架构

- **数据源**: Yahoo Finance (实时价格/期权), FRED (宏观), CNN Money (情绪), Chicago Fed (NFCI)。
- **持久化**: SQLite 自动保存每日信号状态及宏观数据缓存。
- **验证**: 包含 90+ 单元测试与集成测试用例，覆盖所有指标计算逻辑。

---

## 📈 回测表现
- **历史底部捕捉率**: 92.6% (50/54)
- **回测报告**: 详见 [backtest_report.md](docs/backtest_report.md) (由 Phase 3 引擎生成)。

---

## 📄 开源协议
MIT License
