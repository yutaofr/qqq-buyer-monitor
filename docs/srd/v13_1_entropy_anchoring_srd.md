# SRD-v13.1: QQQ Bayesian Orthogonal Factor Monitor - Entropy Anchoring & Cycle Weighting

**Version**: 13.1  
**Status**: Draft for Implementation  
**Architect**: Gemini CLI / Senior Systems Architect  
**Date**: 2026-04-03

---

## 1. 引言 (Introduction)

### 1.1 目的
针对 v13 架构在冷启动阶段出现的虚高熵（False High Entropy）及政权识别迟滞问题，本 SRD 定义了一套基于“历史自洽性”与“第一性原理传导权重”的修复方案。

### 1.2 背景
当前 v13 系统在无先验状态下启动时，贝叶斯大脑处于均匀分布（混沌态），且数据质量评价算法（调和平均）过于敏感，导致系统在冷启动首日往往触发过度防御。

### 1.3 核心术语
*   **Deep Hydration (深层预热)**: 通过历史回放（Historical Replay）强制注入先验知识的过程。
*   **Causal Proximity (因果近缘性)**: 因子对 QQQ/QLD 价格变动的物理传导距离。
*   **Feature Lineage (特征血统)**: 衍生特征（动量、加速度）与其父系原始因子的归属关系。

---

## 2. 架构原则 (Architectural Principles)

*   **KISS (Keep It Simple, Stupid)**: 优先采用线性加权平均，废弃复杂的非线性惩罚算法。
*   **Sequential Causality (顺序因果性)**: 严禁任何形式的偷看未来。预热过程必须模拟真实的 T+0 决策。
*   **Anti-Overfitting (零过拟合)**: 禁止通过回测寻优调整权重。权重必须基于宏观经济学物理常数预设。
*   **Layered Defense (分层防御)**: 
    *   **Regime 层**: 捕获结构性、长波周期（2022 转向）。
    *   **Overlay 层**: 捕获突发性、尾部风险（2020 熔断）。

---

## 3. 功能性需求 (Functional Requirements)

### 3.1 FR-1: 2018 锚定深度回放 (Sequential Prior Replay)
*   **需求描述**: 系统必须支持从 **2018-01-01** 起的静默回放模式，以构建自洽的贝叶斯先验计数。
*   **输入**: 2018 至今的 `macro_historical_dump.csv`。
*   **约束**: 
    *   预热过程中禁止触发执行层逻辑。
    *   **禁止更新** GaussianNB 的均值（$\theta$）与方差（$\sigma$），仅允许更新 `PriorKnowledgeBase` 中的 `counts` 与 `transition_counts`。
*   **输出**: 生成 `v13_hydrated_state.json`。

### 3.2 FR-2: 周期传导加权推理 (Cycle-Logic Weighted Inference)
*   **需求描述**: 在贝叶斯后验计算中，根据因子类别的“因果近缘性”分配权重。
*   **权重矩阵 (Static)**:
    *   **Level 1 (2.5x)**: `credit_spread` (信贷周期 - 原动机)。
    *   **Level 2 (2.0x)**: `net_liquidity`, `real_yield` (估值引力 - 直接定价)。
    *   **Level 3 (1.5x)**: `treasury_vol` (风险前瞻 - 系统压力)。
    *   **Level 4 (1.0x)**: `usdjpy`, `copper_gold` (跨市场代理 - 情绪反射)。
    *   **Level 5 (0.5x)**: `core_capex`, `breakeven` (滞后指标 - 周期现状)。
*   **血统继承**: 所有衍生特征（Moving Average, Momentum, Acceleration）必须自动继承其父系因子的权重。

### 3.3 FR-3: 稳健性质量评分 (Robust Weighted Quality Scoring)
*   **需求描述**: 废弃调和平均算法，改用**加权算术平均**。
*   **算法**: $Q_{score} = \frac{\sum (q_i \cdot w_i)}{\sum w_i}$。
*   **目标**: 确保单一非核心因子的缺失不会导致总分崩塌，同时确保核心因子的降级能显著推高有效熵。

### 3.4 物理参与度底线 (Beta Floor Protection)
*   **需求描述**: 任何由熵惩罚（Entropy Haircut）或执行层惩罚产生的最终 `target_beta` **不得低于 0.5**。
*   **理由**: 确保在极端噪音下系统仍持有基本多头底仓，防止错过结构性修复。

### 3.5 FR-5: PIT (Point-in-Time) 完整性约束
*   **需求描述**: 在 2018 深度回放中，严禁使用任何形式的“日后修正数据（Revised Data）”。
*   **约束细节**: 
    *   回放数据流必须严格模拟 T+0 时刻的市场可见性。
    *   对于具有高度修正特性的因子（如 Core Capex），若缺乏历史快照数据，必须在预热脚本中模拟 30-60 天的发布延迟。
    *   **严禁项**: 禁止使用 FRED 或其它数据源在多年后回填的修正值来训练先验。

### 3.6 FR-6: 存储效率与批量云同步策略
*   **需求描述**: 鉴于云存储 API 调用成本及频率限制，冷启动回演必须采用“本地缓冲 + 最终单次同步”模式。
*   **约束细节**: 
    *   **本地优先**: 在回演 2000+ 交易日的循环中，`PriorKnowledgeBase` 必须配置为仅读写本地磁盘（Local SSD）。
    *   **原子同步**: 只有当回演日期达到“当前日期（Today-1）”且逻辑自洽性校验通过后，系统才允许执行单次全量云同步。
    *   **严禁项**: 严禁在回演循环内部触发任何网络 IO 或云存储写操作。

---

## 7. UI/UX 与输出规范 (UI/UX & Output Specifications)

### 7.1 Discord 通知规范 (UX-01)
*   **状态标签**: 在 Embed Footer 或显著位置增加 `Prior: v13.1 Hydrated (2018 Anchor)` 标识。
*   **Beta 底线警报**: 当触发 FR-4 (Beta Floor) 时，Beta 字段旁必须显示 `⚠️ FLOOR_ACTIVE` 标识，并显示原始未拦截 Beta 以供对比。
    *   示例：`Target Beta: 0.50x (Floor Applied | Raw: 0.12x)`。
*   **质量评分展示**: 废除单一的“数据完整度”，改为显示“加权质量评分（Weighted Quality）”，并标注是否由核心因子降级驱动。

### 7.2 Web 仪表盘可视化 (UX-02)
*   **权重雷达/列表**: 增加 Level 1-5 权重配置的静态展示或交互式 Tips，解释为何信贷周期权重（2.5x）最高。
*   **Beta 锁定态视觉反馈**: 当 `target_beta` 被 Floor 锁定在 0.5 时，Beta 数字应从 `emerald-400` 变为 `amber-400`（锁定色），并增加“Physical Protection”标签。
*   **质量得分对比**: 前端仪表盘应展示基于算术加权的新 $Q_{score}$。

### 7.3 冷启动预热状态反馈 (UX-03)
*   **状态接口**: 增加一个 API 字段 `system_status: HYDRATING | READY`。
*   **用户反馈**: 当系统处于 FR-6 的“本地缓冲回演”阶段时，前端必须显示加载遮罩或状态条：`"Synchronizing 8-Year Bayesian Prior (2018-2026)..."`，而不是展示 0.0 或旧数据。

---

## 8. 验证与测试协议 (Verification & Testing)


### 4.1 特征权重映射算法 (Feature Weight Mapping)
系统应实现正则匹配函数，从特征名中提取根因子标识（Root Identifier），并映射至对应的周期权重。
*   示例：`credit_spread_21d_accel` -> `credit_spread` -> `2.5x`。

### 4.2 似然度加权计算 (Weighted Log-Likelihood)
在 `GaussianNB` 推理中，修改后验概率计算公式：
$$P(R|X) \propto P(R) \cdot \exp\left( \frac{\sum w_i \cdot \ln P(x_i|R)}{\sum w_i} \right)$$
*   **注意**: 必须使用加权平均 Log-Likelihood，以防止因衍生特征冗余导致的权重过载。

### 4.3 显式映射注册表与传递函数 (Technical Registry)

#### 4.3.1 特征权重映射表 (Feature-to-Weight Mapping)
| Identifier | Level | Weight | Description |
| :--- | :--- | :--- | :--- |
| `credit_spread_bps` | Level 1 | 2.5x | 信贷周期核心驱动 |
| `net_liquidity_usd_bn` | Level 2 | 2.0x | 估值引力 - 核心 |
| `real_yield_10y_pct` | Level 2 | 2.0x | 估值引力 - 核心 |
| `treasury_vol_21d` | Level 3 | 1.5x | 系统性压力预警 |
| `move_21d` | Level 3 | 1.5x | 价格动能反馈 |
| `DEFAULT_FALLBACK` | Level 4 | 1.0x | 任何未识别的新特征 |
| `breakeven_10y` | Level 5 | 0.5x | 滞后性通胀预期 |

#### 4.3.2 质量得分传递函数 ($q_i$ Mapping)
*   **1.0**: `direct`
*   **0.7**: `proxy:*`
*   **0.5**: `synthetic:*`, `derived:*`
*   **0.3**: `default:*`
*   **0.0**: `missing`, `unavailable`, `nan`

### 4.4 控制流与优先级规范 (Control Flow)

#### 4.4.1 Beta 底线控制流 (FR-4 Flow)
1.  **输入**: 原始 `target_beta` (由后验概率决定)。
2.  **第一级拦截**: 应用 `Entropy Haircut` 得到 `protected_beta`。
3.  **第二级拦截 (Floor)**: 执行 `protected_beta = max(0.5, protected_beta)`。
4.  **第三级处理**: 将上述值喂入 `InertialBetaMapper` 进行时间域平滑。
*   **强制要求**: 0.5 是逻辑底线，不是跳变底线。

#### 4.4.2 预热更新范围 (Hydration Scope)
*   **更新项**: `PriorKnowledgeBase.counts`, `PriorKnowledgeBase.transition_counts`。
*   **锁定项**: `GaussianNB.theta_`, `GaussianNB.var_`, `GaussianNB.classes_`。
*   **结论**: 深度预热仅改变“先验知识”，不改变“判别模型”。

---

## 5. 验证与测试协议 (Verification & Testing)

### 5.1 验证指标 (KPIs)
*   **Cold-Start Convergence**: 冷启动首日熵值 $\Delta H < 0.05$（对比持续运行态）。
*   **Cycle Sensitivity**: 对 2022 年 1 月的宏观转向识别延迟必须 $\le 15$ 个交易日。
*   **Defense Integrity**: 在 2020 年 3 月黑天鹅期间，Regime 可维持稳定，但 Overlay 必须触发强制减仓。

### 5.2 严禁项 (Prohibited Actions)
*   禁止针对 2018-2026 任何特定年份手动微调权重。
*   禁止在预热脚本运行期间修改任何 `src/models/*.py` 中的参数。

---

## 6. 维护与追溯 (Traceability)

*   所有 Patch 必须在 `execution_trace.csv` 中记录其应用的权重快照。
*   `v13_hydrated_state.json` 必须包含 2018 锚定回放的时间戳校验。

---
**批准**: ________________ (Product Owner)  
**审核**: Gemini CLI (Architect)
