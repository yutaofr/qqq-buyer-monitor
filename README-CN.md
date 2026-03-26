# QQQ 买入信号与战略配置监控系统（v8.1）

这是一个面向 QQQ / QLD / Cash 的生产级推荐引擎，基于 **v8.1 线性流水线架构**。

系统边界很明确：
- 只推荐 **组合级目标 beta**
- 只推荐 **增量资金入场节奏**
- **不计算金额**
- **不管理账户**
- **不自动执行交易**

## v8.1 架构

### Tier-0 宏观状态
`assess_structural_regime()` 基于信用利差和 ERP 将市场划分为：
`EUPHORIC | NEUTRAL | RICH_TIGHTENING | TRANSITION_STRESS | CRISIS`

Tier-0 是顶层约束：
- 对 **Risk Controller** 是 beta 上限硬约束
- 对 **Deployment Controller** 是节奏软约束

### Risk Controller
基于 Class A 宏观数据和 Tier-0 状态输出：
- `risk_state`
- `target_exposure_ceiling`
- `target_cash_floor`
- `tier0_applied`

关键语义：
- `EUPHORIC` 可以进入 `RISK_ON`，并允许在候选库合规时达到 `>1.0` beta
- `CRISIS` 和硬回撤触发会映射到 `RISK_EXIT`
- 如果某个风险态切片缺失，运行时会回退到全局 `0.5 beta` 地板候选，而不是静默降为 `0.0`

### Deployment Controller
用于决定新增资金的部署节奏：
`DEPLOY_SLOW | DEPLOY_BASE | DEPLOY_FAST | DEPLOY_PAUSE`

关键语义：
- `RICH_TIGHTENING` 会默认降速，但强超跌时仍可进入 `DEPLOY_BASE`
- `CRISIS` 会完全暂停增量部署

### Beta Recommendation
`build_beta_recommendation()` 取代了旧的金额执行接口。

系统只输出：
- `target_beta`
- 推荐 `QQQ / QLD / Cash`
- `should_adjust`
- `adjustment_reason`

## 关键变化
- **线性流水线**：`Tier-0 → Risk → Search → Recommend`
- **无金额输出**：移除了 `build_execution_actions()` 和全部美元计算
- **硬/软约束分离**：宏观状态同时影响存量 beta 上限和增量入场节奏
- **纯数学候选搜索**：候选选择先满足 `max_beta_ceiling` 和回撤预算，再输出推荐

## 回测与信号审计

`--mode portfolio` 的旧路径保留为研究工具，不作为生产验收门槛。

最新已验证的真实历史结果：
- `python -m src.backtest --mode portfolio`
  - Tactical Max Drawdown: `-28.2%`
  - Baseline DCA Max Drawdown: `-35.1%`
  - MDD Improvement: `6.9%`
  - Realized Beta: `0.19`
  - Turnover Ratio: `119.58`
  - `RICH_TIGHTENING` left-side windows: `647`
  - `CRISIS` deployment breaches: `0`
- `python scripts/run_signal_acceptance_report.py`
  - Target beta alignment: `MAE=0.0559`, `RMSE=0.1688`, `within_tol=88.97%`
  - Deployment alignment: `exact=99.96%`, `within_one_step=99.99%`

回测报告见：
- [回测报告](docs/backtest_report.md)
- [DCA 图表](docs/images/v8.1_dca_performance.png)

生产验收以两条信号审计为准，而不是混合 NAV 回测。

## 认证候选参考（v8.1）

v8.1 运行时不再使用旧的 `AllocationState` 默认矩阵，而是从认证注册表中选择：

- `RISK_NEUTRAL`：`neutral-base-001`（`70/10/20`, beta `0.90`）或 `neutral-low-drift`（`80/5/15`, beta `0.90`）
- `RISK_REDUCED`：`reduced-tight-001`（`80/0/20`, beta `0.80`）或 `reduced-base-001`（`50/0/50`, beta `0.50`）
- `RISK_DEFENSE`：`defense-001`（`50/0/50`, beta `0.50`）或 `defense-002`（`50/15/35`, beta `0.80`）
- `RISK_EXIT`：`exit-floor-001`（`50/0/50`, beta `0.50`）
- `RISK_ON`：`euphoric-base-001`（`60/25/15`, beta `1.10`）或 `euphoric-max-001`（`80/20/0`, beta `1.20`）

## 核心层级

1. **Tier 0（宏观指挥官）**：监控信用加速、净流动性和融资压力，定义结构性状态。
2. **Tier 1（战术情绪）**：VIX Z-Score、恐慌与贪婪指数、估值与价格背离。
3. **Tier 2（市场结构）**：实时期权墙和 Gamma Flip 探测。
4. **战略层**：加载认证候选，遵守 beta ceiling，只输出推荐结果。

## 历史附录

当前生产架构是上面的 v8.1 线性流水线。`docs/v8.0_linear_pipeline_*` 文件已标记为归档基线，仅用于追溯 v8.0 / v8.1 的设计演进。

## 快速开始

### 1. 环境准备
```bash
cp .env.example .env # 添加你的 FRED_API_KEY
docker-compose build
```

### 2. 实时信号与再平衡审计
```bash
python -m src.main
```

### 3. 信号审计与回测
```bash
python -m src.backtest
python scripts/run_signal_acceptance_report.py
python scripts/plot_dca_performance.py
```

## 相关文档
- [SRD v8.0 基线：线性流水线](docs/v8.0_linear_pipeline_srd.md)
- [ADD v8.0 基线：实现方案](docs/v8.0_linear_pipeline_add.md)
- [SDT v8.0 基线：测试设计](docs/v8.0_linear_pipeline_sdt.md)
- [架构对齐评审](docs/v8_architecture_review.md)
- [回测报告](docs/backtest_report.md)

---
*免责声明：本工具仅用于机构模拟和监控，不构成个人投资建议。*
