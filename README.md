# QQQ Bayesian Orthogonal Factor Monitor (v13.7-ULTIMA)

> **工业级贝叶斯决策引擎：历史锚定、实体增强、全息透明**

本系统是一个基于**贝叶斯全概率推断**的 QQQ/QLD 资产配置决策中枢。v13.7-ULTIMA 版本标志着系统已完全具备跨越 8 年周期的宏观感知能力与物理级风险拦截机制。

---

## 1. 核心架构演进 (v13.7-ULTIMA)

### 1.1 实体经济重力注入 (Real-Economy Gravity)
系统已从单纯的金融因子监控进化为 **12 因子正交矩阵**。通过引入 PMI 动量与劳动力市场松弛度特征，彻底消除了周期后期的“金融盲视”。

### 1.2 8 年深度锚定预热 (Deep Hydration)
拒绝冷启动混沌。系统强制执行从 **2018-01-01** 起的 Point-in-Time (PIT) 深度回演，构建了包含 2000+ 样本的历史自洽先验分布。

### 1.3 理性防御算法 (Damped Gaussian Defense)
- **非对称似然锐化**: 针对宏观因子应用 $\tau=0.35$，实现对边际恶化的“尖锐感知”。
- **二阶熵值阻尼**: 应用 $exp(-0.6 \cdot H^2)$ 非线性惩罚，在认知冲突区果断减速。
- **ULTIMA 熔断**: 认知死锁超过 21 天自动降维至信贷核心（Level 1），确保生存。

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
系统启动前必须确保已加载最新的注水先验状态：
```bash
# 引用 v13.7-ULTIMA 黄金先验库
export PRIOR_STATE_PATH="data/v13_6_ex_hydrated_prior.json"
```

### 4.2 深度回演 (Re-Hydration)
若特征契约发生变更，需重新构建 8 年记忆：
```bash
docker run --rm -v $(pwd):/app -w /app qqq-monitor:v13.4 \
python scripts/v13_sequential_replay.py --output data/v13_new_prior.json
```

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
