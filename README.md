# QQQ Long-Term Allocation Engine

一个面向长期纳指 100 ETF 资金管理的分层仓位引擎。
系统不再把输出定义成“高确定性买点标签”，而是把宏观结构、战术压力和期权结构整合成可执行的仓位动作建议。

> [!IMPORTANT]
> 当前主输出面是 `allocation_state`，包括 `BASE_DCA / SLOW_ACCUMULATE / FAST_ACCUMULATE / PAUSE_CHASING / RISK_CONTAINMENT`。
> 旧的 `signal` 字段仅保留为兼容层，不应被当作主要仓位决策接口。

## 系统定位

- 适合长期 QQQ / 纳指 100 ETF 左侧加仓与风险控制。
- 把系统用作“仓位节奏控制器”，而不是“抄底按钮”。
- 优先减少过度自信、追高和阴跌补仓的行为偏差。

## 决策框架

### Tier 0: Structural Regime
- 结合信用利差与 ERP，识别 `EUPHORIC / RICH_TIGHTENING / NEUTRAL / TRANSITION_STRESS / CRISIS`。
- 决定资金当前应偏防守、常规定投还是加速吸纳。

### Tier 1: Tactical Pressure
- 基于回撤、MA200 偏离、VIX、F&G、广度，构造 `stress / capitulation / persistence`。
- 目标不是预测最低点，而是识别是否值得加快或放慢投入速度。

### Tier 2: Options Overlay
- 期权墙不再扮演“硬开关”。
- 当前逻辑把它作为软约束层，用于降低 tranche、延长冷却和削弱置信度。

## 仓位动作输出

| `allocation_state` | 含义 | 操作语义 |
|---|---|---|
| `BASE_DCA` | 常规环境 | 维持基础定投 |
| `SLOW_ACCUMULATE` | 有压力但结构未充分出清 | 仅小幅试探 |
| `FAST_ACCUMULATE` | 中性结构下的明显超跌/恐慌 | 允许提高加仓速度 |
| `PAUSE_CHASING` | 价格显著抬升，不适合追高 | 暂停追高 |
| `RISK_CONTAINMENT` | 结构性压力或流动性风险升高 | 进入风险控制 |

兼容字段:
- `signal` 仍会输出 `NO_SIGNAL / WATCH / TRIGGERED / STRONG_BUY / GREEDY`，但不应凌驾于 `allocation_state` 之上。
- CLI、JSON 和历史输出都优先展示 `allocation_state`。

## 快速开始

### 1. 配置环境

在根目录创建 `.env`：

```bash
FRED_API_KEY=your_fred_api_key_here
```

### 2. 运行实时信号

```bash
python -m src.main
```

### 3. 输出 JSON

```bash
python -m src.main --json
```

JSON 当前会显式包含：
- `allocation_state`
- `daily_tranche_pct`
- `max_total_add_pct`
- `cooldown_days`
- `required_persistence_days`
- `confidence`
- `data_quality`
- `data_quality_summary`

### 4. 查看历史记录

```bash
python -m src.main --history 30
```

历史输出优先显示：
- `allocation_state`
- 对应动作语义
- 分数与价格

## Docker 运行

当前 Docker 基础镜像为 `python:3.13-slim`，默认镜像名为 `qqq-monitor:py313`。

构建镜像：

```bash
docker build -t qqq-monitor:py313 .
```

运行主程序：

```bash
docker run --rm --env-file .env qqq-monitor:py313 python -m src.main
```

运行完整测试：

```bash
docker run --rm -v "$(pwd)":/app -w /app --env-file .env qqq-monitor:py313 python -m pytest -q
```

使用 compose：

```bash
docker compose run --rm app
docker compose run --rm test
docker compose run --rm backtest
```

## 回测方法

当前回测是 allocator-style，而不是 signal-label replay。

- 基线始终是 weekly DCA。
- 战术状态只决定“加快 / 放慢 / 暂停追高 / 风险控制”的投入速度。
- 核心指标是：
  - `T+5 / T+20 / T+60` forward return
  - add 后最大不利波动 (`max adverse excursion`)
  - 相对 baseline DCA 的平均成本变化
  - 最终低点前的资金部署比例

参考文档：
- [docs/backtests/methodology.md](docs/backtests/methodology.md)
- [docs/backtest_report.md](docs/backtest_report.md)

## 当前约束

- 如果历史数据拿不到，就明确排除，不再伪造 fear/greed 或 short-volume 因子。
- `data_quality` 会区分 live 与 cache，并给出 `stale_days`。
- 旧版“98.1% 底部捕捉率”不再代表当前方法学，也不应用于宣传或决策。

## 验证

- Docker 构建: `docker build -t qqq-monitor:py313 .`
- Docker smoke test: `docker run --rm qqq-monitor:py313 python -V && docker run --rm -v "$(pwd)":/app -w /app qqq-monitor:py313 python -m pytest -q`
- 单元与集成测试: `python3 -m pytest -q`
- 静态编译: `python3 -m compileall src tests`
- 回测 smoke run: `python3 -m src.backtest`

## 许可证

MIT License
