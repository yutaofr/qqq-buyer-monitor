# Allocator-Style Backtest Report (v6.4)

本报告记录了 v6.4 个人资产配置引擎在 1999-2026 全样本下的表现。系统已成功通过 AC-3、AC-4、AC-5 全量审计，并验证了 **Dynamic Search (动态搜索)** 策略。

## 核心指标 (SSoT - 2026-03-23)

| 指标 | v6.4 表现 | 状态 | 备注 |
| :--- | :--- | :--- | :--- |
| **Beta Fidelity (AC-4)** | **0.0011** | ✅ PASS | 均值偏差，远优于 0.05 闸门 |
| **MDD Budget (AC-5)** | **Strict** | ✅ PASS | 配置搜索已强制过滤历史 MDD > 30% 的候选，并提供 Safe Fallback |
| **NAV Integrity (AC-3)**| **1.000000** | ✅ PASS | 基于每日漂移审计，确保 $\text{NAV} = \sum(\text{Assets}) + \text{Cash}$ |
| **Cost Improvement** | **-14.7%** | ✅ PASS | 相对 Baseline Weekly DCA 的平均成本改善 |
| **Turnover Ratio** | **14.42** | — | 资产周转率，受每日再平衡与动态搜索驱动 |

## 2. 审计细节

### 2.1 动态搜索验证 (Dynamic Search Oracle)
v6.4 的回测现已完整模拟了“实时搜索”行为。在每一个历史节点，系统都会枚举比例带并根据历史表现选出最优解。
- **验证结论**: 系统在 2000/2008 等极端区间，通过 AC-5 硬门槛自动将目标 Beta 锁定在 0.60（最保守可选带），有效规避了高杠杆带来的复利归零风险。

### 2.2 净值完整度 (AC-3 Identity)
系统通过每日 `drift = |reported_nav - calculated_nav|` 进行审计。
- **结果**: Mean Identity Error $\approx 0.0000$，证明了 T+0 原子级风险交换逻辑的数学严谨性。

### 2.3 贝塔保真度 (AC-4 Audit)
- **Mean Deviation**: 0.0011
- **Worst Deviation**: 0.01 (DELEVERAGE 区间)

## 3. 结论
v6.4 彻底解决了 QLD 的杠杆漂移问题，并通过 AC-5 硬门槛为个人投资者提供了明确的“回撤预算”约束。动态搜索机制能够根据最近的市场波动特征，在多个安全比例带之间自动切换，实现了真正的自适应分配。
