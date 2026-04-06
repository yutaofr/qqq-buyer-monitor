# QQQ Bayesian Orthogonal Factor Monitor (v13.7-ULTIMA)

> **工业级贝叶斯决策引擎：历史锚定、实体增强、全息透明**

本系统是一个基于**贝叶斯全概率推断**的 QQQ/QLD 资产配置决策中枢。v13.7-ULTIMA 版本标志着系统已完全具备跨越 8 年周期的宏观感知能力与物理级风险拦截机制。

---

## 1. 核心架构演进 (v13.7-ULTIMA)

### 1.1 实体经济重力注入 (Real-Economy Gravity)
系统已从单纯的金融因子监控进化为 **12 因子正交矩阵**。通过引入 PMI 动量与劳动力市场松弛度特征，彻底消除了周期后期的“金融盲视”。

### 1.2 优雅冷启动 (Hydrated Cold Start)
生产默认加载已经校准好的 `hydrated prior` 种子，并在缺少运行态 state 时原地物化为可写 prior，而不是每次都从头推倒 8 年历史。

- **Canonical Seed**: `src/engine/v11/resources/v13_6_cold_start_seed.json`
- **运行态 Prior**: `data/v13_6_ex_hydrated_prior.json`，缺失时由 canonical seed 自动恢复
- **回测路径**: 为每次 walk-forward 窗口生成本地 prior state，不污染生产状态
- **重建记忆**: 仅当特征契约或先验结构发生变化时，才重新跑历史 hydration

### 1.3 理性防御算法 (Damped Gaussian Defense)
- **非对称似然锐化**: 针对宏观因子应用 $\tau=0.35$，实现对边际恶化的“尖锐感知”。
- **二阶熵值阻尼**: 应用 $exp(-0.6 \cdot H^2)$ 非线性惩罚，在认知冲突区果断减速。
- **ULTIMA 熔断**: 认知死锁超过 21 天自动降维至信贷核心（Level 1），确保生存。

### 1.4 QQQ 价格拓扑对齐 (Price Topology Alignment)
- **Worldview Benchmark**: 系统新增一个基于 `QQQ` 价格 / 成交量 trailing 结构的 4 阶段软基准，用于审计连续概率、动能与 beta 是否符合新的宏观周期世界观。
- **Topology Likelihood Coupling**: price topology 已从单纯后处理升级为 **likelihood penalty / veto**，在价格拓扑崩坏时直接压制 `MID_CYCLE` 粘性。
- **执行面锚定**: price topology 仍不替代贝叶斯主引擎，但会在高置信结构出现时，继续作为 PIT-safe 的 beta anchor。
- **灰犀牛治理**: 2018Q4 这类“流动性收缩 + 波动率加速”场景，优先由价格拓扑与执行层物理约束共同处理，而不是靠 event-picked overfit。

---

## 2. 核心红线 (The User Redline)

- **物理仓位保护**: 最终推荐 `target_beta` **物理锁定不低于 0.5**。业务生存逻辑具有覆盖所有算法判定的最高优先级。
- **PIT 严谨性**: 严禁使用日后修正数据（Revised Data）。所有历史回演严格遵循 T+0 决策可见性。

---

## 3. 12 因子正交矩阵 (Factor Matrix)

| 维度 | 核心因子 | 传导权重 | 物理意义 |
| :--- | :--- | :--- | :--- |
| **金融核心** | `Credit Spread`, `ERP` | **2.5x** | 周期的原动机与估值杠杆 |
| **定价引力** | `Real Yield`, `Net Liquidity` | **2.0x** | 贴现率重力与货币总量 |
| **实体信号** | `PMI Momentum`, `Labor Slack` | **1.5x** | 经济景气度与劳动力拐点 |
| **系统压力** | `MOVE Index`, `Price Momentum` | **1.5x** | 固收波动与正交化动能 |

---

## 4. 快速开始 (Operational Guide)

### 4.1 生产启动 (Go-Live)
系统启动前必须确保已加载最新的运行态 prior；若缺失，入口会自动从 canonical seed 恢复：
```bash
# 可选：显式指定运行态 prior
export PRIOR_STATE_PATH="data/v13_6_ex_hydrated_prior.json"

# 可选：覆盖默认 cold-start seed
export PRIOR_SEED_PATH="src/engine/v11/resources/v13_6_cold_start_seed.json"
```

### 4.2 深度回演 (Re-Hydration)
若特征契约发生变更，需重新构建 8 年记忆：
```bash
docker run --rm -v $(pwd):/app -w /app qqq-monitor:v13.4 \
python scripts/v13_sequential_replay.py --output data/v13_new_prior.json
```

### 4.3 世界观回测审计 (Worldview Audit)
对齐新的宏观周期世界观时，建议按以下顺序执行：
```bash
python -m src.backtest \
  --evaluation-start 2018-09-01 \
  --artifact-dir artifacts/v11_black_box_audit_2026-04-06 \
  --price-cache-path data/qqq_history_cache.csv \
  --price-end-date 2026-04-04 \
  --no-price-download

python scripts/run_v14_panorama_matrix.py --price-cache-path data/qqq_history_cache.csv
python scripts/run_worldview_backtest_audit.py \
  --mainline-artifact-dir artifacts/v14_panorama/mainline \
  --baseline-trace-path artifacts/v14_panorama/baseline_oos_trace.csv \
  --price-cache-path data/qqq_history_cache.csv
```

输出工件：
- `artifacts/v11_black_box_audit_2026-04-06/`
- `docs/research/v14_panorama_strategy_matrix.md`
- `docs/research/v14_macro_cycle_worldview_audit.md`
- `artifacts/v14_worldview_audit*/`

回测治理红线：
- 回测只允许重放生产 `V11Conductor`
- 禁止在回测侧偷偷修改 `var_smoothing / posterior_mode / feature subset`
- 缺失价格缓存时默认 fail closed
- 每日运行必须保存法医快照，供回测工件反向引用

---

## 5. 全息监控与透明度 (UX)

- **Discord (#FFA500)**: 触发 0.5 底线拦截时发出橙色警报，展示 `Raw Beta` 对比。
- **Web Dashboard**: 物理锁定态视觉反馈（Amber-400），实时透传 `Prior Anchor: 2018-01-01`。
- **Posterior Dynamics**: 终端与 Web 同步展示 4 阶段后验分布，并输出每个阶段的 `delta_1d` / `acceleration_1d`，用于观察周期切换动能，而不再只盯单一 Top-1。
- **Panorama Fail-Closed**: 当 `Mud Tractor` 或 `QQQ Sidecar` 任一探针处于 degraded / missing 状态时，系统禁止把该日判定为 `AGGRESSIVE`，仅保留标准轨道或保护轨道建议。

---

## 6. 治理与审计 (Governance)

本存储库遵循 **多重代理审计协议**：
- **Architect**: 维护因果严谨性与 KISS 原则。
- **ML Expert**: 负责数值稳定性与似然度锐化。
- **UI/UX Auditor**: 维护数据契约与透明度。

---
© 2026 QQQ Entropy AI Governance. 基于贝叶斯原理，服从生存红线。
