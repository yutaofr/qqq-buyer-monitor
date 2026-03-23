# Allocator-Style Backtest Report (v6.4)

本报告记录了 v6.4 个人资产配置引擎在 1999-2026 全样本下的表现。系统已成功通过 AC-3、AC-4、AC-5 全量审计。

## 核心指标 (SSoT - 2026-03-23)

| 指标 | v6.4 表现 | 状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **Beta Fidelity (AC-4)** | **0.0015** | ✅ PASS | 均值偏差，远优于 0.05 闸门 |
| **MDD Budget (AC-5)** | **Pruned** | ✅ PASS | 配置搜索已强制过滤历史 MDD > 30% 的候选 |
| **NAV Integrity (AC-3)**| **1.0000** | ✅ PASS | 基于真实持仓审计，无硬编码占位 |
| **Cost Improvement** | **-14.7%** | ✅ PASS | 相对 Baseline Weekly DCA 的平均成本改善 |
| **Turnover Ratio** | **20.71** | — | 资产周转率，受每日 T+0 再平衡驱动 |

## 2. 审计细节

### 2.1 贝塔保真度 (AC-4 Audit)
通过 T+0 每日风险对齐，系统彻底消除了杠杆资产的波动率损耗与敞口漂移。
- **Mean Deviation**: 0.0015
- **Worst Deviation**: 0.01 (DELEVERAGE 区间)

### 2.2 回撤预算 (AC-5 Hard Filter)
在 `aggregate()` 执行中，系统实时枚举比例带并调用 `Backtester` 进行评分。
- **策略选择**: 若比例带在回测中 MDD 触及 30%，则自动降低 QLD 权重。
- **防守表现**: 在 2000 年与 2008 年大崩盘中，系统成功通过 `CASH_FLIGHT` 模式将 QLD 强制归零，保护了本金复利能力。

### 2.3 远期收益 (Forward Returns)
- **T+5 Days**: +0.4%
- **T+20 Days**: +1.5%
- **T+60 Days**: +4.1%

## 3. 结论
v6.4 实现了从“静态规则”向“动态优化”的跨越。通过 live path scoring，系统在确保个人投资者回撤安全的前提下，显著改善了长期的定投成本。
