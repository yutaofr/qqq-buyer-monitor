# ADD: QQQ Cognitive Exoskeleton (v11.0)

> 版本: v11.0
> 状态: Final Design
> 关联 SRD: `conductor/tracks/v11/spec.md`
> 核心代号: "Entropy"

## 1. 系统概览 (High-Level Design)

v11 系统被设计为一个**严格单向的数据处理流水线**。数据流从“物理层”输入，经过“毒素过滤”，注入“认知中枢”进行概率坍缩，最后由“独裁映射器”输出离散指令。

### 1.1 拓扑结构
`Raw Data` -> `Degradation Pipeline` -> `Adaptive Memory` -> `PCA-KDE Engine` -> `Kill-Switch Audit` -> `Hysteresis Mapper` -> `Final Signal`

---

## 2. 组件详细设计 (Component Specifications)

### 2.1 贝叶斯核心推断引擎 (`BayesianInferenceEngine`)
该组件是系统的决策心脏，负责将正交的信号组坍缩为后验概率。

*   **正交信号拓扑**:
    *   **先验层 (Prior)**: $Credit\_Spread, Liquidity\_ROC$ (决定宏观重力)。
    *   **证据层 (Likelihood)**: $VIX, Drawdown, Breadth$ (决定市场反应)。
*   **后验合成公式**:
    $$P(Regime_i | Evidence) = \frac{L(Evidence | Regime_i) \times [P(Regime_i)_{base} + \Delta Prior_{sensor}]}{Z}$$
    *   $\Delta Prior_{sensor}$: 物理传感器产生的偏移量（如利差绝对值突破 800bps 时强制提升 BUST 先验）。
*   **PCA-KDE 推理协议**:
    1.  **标准化**: 证据特征必须通过 `AdaptiveMemory` 生成 25 年滚动 EWMA 分位数。
    2.  **降维**: 执行 PCA，提取解释度最高的**前 2 个主成分**。
    3.  **似然估计**: 使用预训练的 **KDE 核密度分布** 计算当前 PCA 坐标在各 Regime 下的似然得分。

### 2.2 特征库与增量维护 (`FeatureLibraryManager`)
*   **数据一致性**: 系统必须维护一个回溯至 1995 年的每日特征库（约 7500+ 行）。
*   **增量注入**: 每日收盘后，将 T+0 数据追加至库末，并重新计算**指数加权分位数 (EWMA-P)**。
*   **窗口锁死**: 所有的统计排名（Rank）必须基于此时序库，禁止在推断时使用截面快照。

### 2.3 认知中枢：外生记忆算子 (`ExogenousMemoryOperator`)
... (保持之前半衰期衰减设计) ...

### 2.3 猎杀扳机：双锚定 Z-Score (`DualAnchorKillSwitch`)
*   **信号源**: $TS_t = VIX3M_t - VIX_t$。
*   **Z-Score 计算**:
    *   $Z_{fast}$: 基于 20 日动量均值与标准差。
    *   $Z_{slow}$: 基于 252 日动量均值与标准差。
*   **逻辑门**: `Resurrect = (Z_fast > 2.0) AND (Z_slow > 3.0) AND (dVIX/dt < 0)`。

### 2.4 独裁映射器 (`HysteresisExposureMapper`)
基于状态机的离散控制，内置结算物理锁。

*   **状态转移矩阵**:
    | 当前状态 | 触发条件 (Event) | 目标状态 | 后续锁定 |
    | :--- | :--- | :--- | :--- |
    | QLD | $P(BUST) > 0.40$ | QQQ | T+1 |
    | QQQ | $P(BUST) > 0.75$ | CASH | T+1 |
    | QQQ | $P(BUST) < 0.20$ | QLD | T+1 |
    | CASH | `Resurrect == True` | QLD | T+30 |
    | ANY | $Q_t < 0.5$ | SAFE_BLACKOUT | 永久直至 $Q_t$ 恢复 |

---

## 3. 物理数据口径 (SSoT Data Schema)

| 字段 | 类型 | 正交分类 | 来源 |
| :--- | :--- | :--- | :--- |
| `credit_spread_bps` | Float | 标定层 (Labeling) | FRED |
| `liquidity_roc` | Float | 标定层 (Labeling) | Fed H.4.1 |
| `vix` | Float | 推理层 (Evidence) | YFinance |
| `vix3m` | Float | 推理层 (Evidence) | YFinance |
| `drawdown_pct` | Float | 推理层 (Evidence) | Calculated |

---

## 4. 异常处理与生存模式 (Error Handling)

### 4.1 结算锁冲突 (Settlement Conflict)
如果在 T+1 冷却期内发生剧烈波动，系统将强制维持原状。设计原则是：**宁可错过第二波反弹，也不触碰结算合规红线。**

### 4.2 记忆坍塌保护
若信贷利差发生 100bps 以上的单日异动，系统自动将所有 $\lambda$ 设为最小值 0.5，清除所有平稳期记忆，强制执行最高级别防御。

---
*Architect Sign-off: The technical blueprint is convergent. This ADD serves as the source of truth for implementation.*
