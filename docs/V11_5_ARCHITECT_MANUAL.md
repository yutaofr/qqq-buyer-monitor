# 无状态云原生决策中枢：V11.5 架构设计与状态治理手册

## 1. 物理架构：JIT 模型溯源与数据闭环
V11.5 核心遵循 **"Logic follows Data"** 准则。
*   **JIT 训练架构**：生产容器不依赖任何预训练权重。
    - **Bootstrap**：启动时从 Vercel Storage 同步 `macro_historical_dump.csv`。
    - **Fitting**：在内存中实时拟合 GaussianNB。
    - **Validation**：在模型进入推断前，校验 `classes_ / theta_ / var_ / class_prior_` 的完整性与数值合法性。
    - **Inference**：执行当日推断。
    - **Feedback**：推断结果实时回填至 CSV，实现“在线进化”。
*   **理由**：在分布式无状态环境中，JIT 彻底消除了模型版本与数据版本不匹配的隐患。
*   **新约束**：生产与审计冷启动必须依赖 canonical DNA；若 `macro_historical_dump.csv` 或 regime DNA 缺失，系统直接 fail closed，不再偷偷生成 synthetic baseline。

## 2. 状态机治理：解决“频繁波动”与“冷启动滞后”的工程方案
为了避免在概率临界区出现频繁换仓（Signal Churn），架构设计了四重过滤与对齐：
1.  **Regime Stabilizer**：新制度只有在累积证据超过 `entropy_odds / regime_count` 后才允许切换。
2.  **Inertial Beta Mapper**：采用基于 Shannon 熵的 Odds-Ratio 动态屏障。只有累积证据超过当前不确定性几何壁垒时才允许 Beta 切换。
3.  **BehavioralGuard**：执行桶切换也采用同样的证据积累原则，屏障由 `entropy_odds / bucket_state_count` 结构性推导，不再使用经验调优常数。
4.  **Settlement Lock (物理结算锁)**：调仓动作后，系统状态机强制进入 `remaining_cooldown=1` 的死区。

## 2.1 不确定性定价：无阈值熵惩罚
风险定价现在采用**无阈值** Shannon 熵曲面：

`target_beta = raw_target_beta * exp(-H)`

其中 `H` 为后验分布熵。
这意味着：
- 熵越高，风险只会连续下降
- 系统不会再因为高熵把防御性 beta 拉回 `1.0x`
- 风险定价只依赖 posterior 的几何形状，不依赖人工 cutoff

## 3. 持久化层：破坏性 Schema 与审计透明度
*   **审计透明度 (AC-4)**：所有导出至 `status.json` 的信号必须强制解耦 **Intent (意志)** 与 **Action (行动)**。
    - **Raw Target Beta**：贝叶斯核的原始科学推断结果。
    - **Target Beta**：经过惯性映射与行为守卫后的实际执行目标。
    - **Raw Regime / Stable Regime**：当天后验 Top-1 与稳定状态机输出必须分离。
    - **Deployment State / Execution Bucket**：增量节奏与存量执行桶必须分离。
    - **目的**：防止审计者将“惯性观察期”误判为“引擎不响应”。

## 4. 系统的优缺点分析 (Trade-offs)
*   **优点**：
    - **确定性**：连续运行三次，结果比特级一致。
    - **自愈性**：核心记忆（Prior JSON）丢失后，可依赖 canonical DNA CSV 自动重建 deterministic prior 与执行状态。
    - **透明度**：意志与行动的分离让量化黑盒变得可解释、可审计。
*   **缺点**：
    - **惯性延迟**：非冷启动状态下，制度切换会比价格拐点延迟 1-2 天。这是为了换取系统在宏观噪声干扰下的**绝对定力**。
