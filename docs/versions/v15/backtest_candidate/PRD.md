# PRD: True Kelly Historical PnL Backtest & ERP Fix
> Version: 1.0 (Supplementary) | Status: APPROVED | Governed by: TRUE_KELLY_BACKTEST_SRD.md

---

## 1. 产品背景与核心问题

### 1.1 现状痛点

当前的 A/B 测试报告在架构验证中暴露了两个关键缺陷：
1. **实验变体失效 (BUG-1)**：由于 `regime_process_trace.csv` 缺乏 `erp_percentile` 字段，且 `_load_trace()` 退化处理粗暴（固定为 0.5），导致 `erp_weight` 的实验变体输出结果完全相同（Value Tilt 始终为 1.0）。
2. **缺乏核心业务价值证明 (GAP-1)**：现有的策略验收缺少基石指标 —— PnL 净值曲线和风险收益量化评估（CAGR, MDD, Sharpe 等）。没有考虑由于状态切换引起的交易摩擦成本。

### 1.2 产品目标

1. **修正 ERP 数据流**：提取环境历史回测产生的 `target_beta`，建立反比例缩放代理 `erp_percentile`，激活 True Kelly 的 Value Tilt 效用。
2. **构建高可信度 PnL 模拟器**：对所有 Kelly 变体及 Pseudo-Kelly 执行带滑点/摩擦的净值模拟。
3. **提供生产并入的最终论据**：输出严格的性能指标对比表格，用数据证明 True Kelly（尤其是 `half_erp_low`）具有远优于基准的投资回报率或夏普比率。

---

## 2. 核心用例

### UC-01: ERP Surrogate (代理变量计算)
- **触发条件**：加载 Execution Trace 期间
- **输入**：`target_beta` (包含在 trace csv 中)
- **处理**：将 `target_beta` [0.5, 1.2] 的区间反向映射为 `erp_percentile` [0.0, 1.0]。高 beta 代表市场估值昂贵（低 ERP），低 beta 代表市场便宜（高 ERP）。
- **输出**：每行数据的合成 `erp_percentile`。

### UC-02: PnL 净值曲线衍生
- **输入**：带有 `close` 行情的 Trace，特定的 `deployment_multiplier` 序列，基准部署额度 `base_daily_deploy` (1%)，交易摩擦 `transaction_cost` (0.05%)。
- **处理**：
  - 迭代产生每日贡献: `daily_return * (deployment_multiplier * base_daily_deploy)`
  - 若 `deployment_multiplier` 发生变动，当前净值直接扣减摩擦成本。
  - NAV 累乘。
- **输出**：持续的资金净值时间序列。

### UC-03: Performance Metrics 计算
- **输入**：Pnl 净值曲线时序数据
- **处理**：计算金融数学量化指标。
- **输出**：CAGR, Max Drawdown, Sharpe (年化), Sortino, Calmar，Total Return。

### UC-04: 综合回测报告渲染
- **触发**：执行 `docker-compose run kelly-pnl`
- **输出**：生成 `pnl_report.md`，使用降维对比视图阐述最佳 Kelly 参数组合，并给出是否推荐接管主网（Production Merge）的最终建议。

---

## 3. 非功能性需求

### 3.1 准确性与健壮性
- **缺失数据处理**：价格 `close` 若包含 NaN 需平稳跳过，不产生收益或惩罚。
- **防止负净值溢出**：极端回撤下 NAV 取 Max(NAV, 0.0)。

### 3.2 运行隔离
- 不破坏现有 `kelly-ab`，作为完全并行的 pipeline（追加 `kelly-pnl` 到容器）。
- 生成工件独立，不覆盖之前的结构化结果。

---

## 4. 禁止事项（产品红线）

| 禁止行为 | 原因 |
|:---|:---|
| 修改 `src/engine/v11/core/kelly_criterion.py` | 第一阶段核心数学模型已锁定 |
| 修改 `src/engine/v11/signal/kelly_deployment_policy.py` | 信号状态机接口已被证明健全 |
| 修改任何由于本次外加特性导致的原项目核心测试 | 防治污染测试隔离红线 |

---

## 5. 成功标准

1. **AC-6**: `docker-compose run kelly-ab` 产出中 `erp_weight` 相关变体的状态对齐再无高度雷同。
2. **AC-7**: `docker-compose run kelly-pnl` 全解析无报错，成功写入 MD 报告和 JSON。
3. **AC-8 & 9**: Pnl TDD 单元测试 5/5 GREEN，全量回归保持完全 GREEN。

---

© 2026 QQQ Entropy AI Governance — True Kelly PnL PRD v1.0
