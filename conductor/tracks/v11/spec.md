# SRD: QQQ Cognitive Exoskeleton (v11.0)

> 版本: v11.0
> 状态: Final
> 日期: March 2026
> 适用范围: QQQ Monitor v11.0 架构规范
> 替换文档: QQQ Buyer Monitor v10.0 (deterministic HSM)

## 1. Purpose and Scope

本系统要求规范 (System Requirements Document, SRD) 定义了 QQQ Monitor v11.0（代号："Entropy"）的完整技术架构与行为准则。

v11.0 是一个专为散户交易者设计的**独裁式认知外骨骼 (Dictatorial Cognitive Exoskeleton)**。它基于长期的“霍华德·马克斯式 (Howard Marks)”解剖与多轮物理级 POC 验证，彻底摒弃了 v10.0 的静态阈值和高频调仓幻觉，在 QQQ（1 倍现货）、QLD（2 倍杠杆）与 Cash（现金）的受限边界内，提供抗拒人性弱点与物理摩擦的极端生存能力。

### 1.1 系统核心理念
1.  **概率防守优先**：通过外生信贷利差驱动记忆衰减，利用 PCA-KDE 模型在左侧实现动态降杠杆。
2.  **物理断网防御**：承认在极端危机（VIX > 60）中流动性的枯竭，通过引入强制结算冷却与黑洞机制（Blackout），锁定用户的致命操作。
3.  **期限结构解冻**：右侧猎杀不依赖绝对价格，仅在 VIX 期限结构（Term Structure）发生统计学显著收敛（Z-Score > 3.0）的瞬间，释放杠杆。

---

## 2. Architecture Principles (架构铁律)

这些原则是强制性约束，任何违反这些原则的代码实现均被视为架构失效。

### PRINCIPLE-01: 信号正交性 (Bayesian Orthogonality)
标定引擎（用于判断宏观环境状态）必须仅依赖信贷与流动性指标（如 Credit Spread OAS, Liquidity ROC）。推理引擎（用于捕捉市场恐慌证据）必须仅依赖价格衍生指标（如 VIX, Drawdown）。严禁两者的交叉反馈，以确保系统能敏锐捕捉“宏观恶化但市场麻木”的背离。

### PRINCIPLE-02: 外生记忆驱动 (Exogenous Memory)
计算任何滚动分位数时，严禁使用固定窗口或受价格/VIX 驱动的半衰期。所有时间衰减率 $\lambda$ 必须由外生信贷指标的变动率（如利差加速度）驱动。系统只能因真实的宏观断裂而“加速遗忘”。

### PRINCIPLE-03: 优雅降级与数据防毒 (Graceful Degradation)
第三方数据断流是常态。系统必须具备 `DataDegradationPipeline`。所有数据在输入引擎前必须通过物理常识校验和尖刺过滤。若数据质量得分低于阈值，系统必须自动拦截高级指令，强制降级至无杠杆状态或现金状态。

### PRINCIPLE-04: 迟滞状态机 (Hysteresis Exposure Mapping)
系统在 QLD、QQQ 和 Cash 之间的切换禁止呈现线性平滑。必须通过引入非对称的“死区 (Deadband)”，过滤 0.49 与 0.51 之间的概率震荡。系统宁可承受微小的趋势确认延迟，也绝不允许连续两天发出反向调仓的“洗盘”指令。

### PRINCIPLE-05: 物理结算锁与猎杀锁仓 (The Hard Lock)
系统输出的信号必须强迫用户遵循券商的物理结算规则：
1.  **结算锁**: 任何常规调仓（如 QLD $\to$ QQQ）后，强制进入 **T+1 信号静默期**，对齐散户券商资金可用性。
2.  **猎杀锁 (Resurrection Immunity)**: 一旦 Kill-Switch 触发一键满仓 QLD，系统自动进入 **30 个交易日的强制锁仓期**。期间屏蔽一切反向调仓信号（包括 $P(BUST)$ 波动），强制用户扛过底部的宽幅震荡（W 形底），防止在黎明前被洗出场。

---

## 3. Component Architecture (模块规范)

### 3.1 数据降级管道 (`src/engine/v11/signal/data_degradation_pipeline.py`)
*   **职责**:
    1.  执行绝对物理阈值校验（如 $9.0 < VIX < 150.0$）。
    2.  清洗 5 日中位数偏离 >30% 的尖刺错单。
    3.  **影子代理 (Shadow Proxy)**: 
        *   若 VIX3M 缺失，使用 `VIX * 0.9` 补全（Backwardation 假设）。
        *   若 VIX 缺失，使用 `QQQ 20d Realized Volatility * 100` 代理。
    4.  生成当日数据质量得分（Quality Score）。
*   **约束**: 如果质量得分 $<0.5$，触发强制黑洞模式（Forced Blackout）。

### 3.2 认知中枢 (`src/engine/v11/core/adaptive_memory.py`)
*   **职责**: 接收清洗后的数据，生成带半衰期的 EWMA 分位数特征。
*   **衰减逻辑**: $\lambda_t = \lambda_{base} \times \exp(-\kappa \cdot \max(0, \Delta Spread_t))$，其中基准 $\lambda_{base} = 10$ 年。
*   **输出**: 高质量、无滞后的宏观标定标签（$BUST$ 等）。

### 3.3 猎杀解冻算子 (`src/engine/v11/core/kill_switch.py`)
*   **职责**: 独立于贝叶斯主引擎运行，专门负责在极寒环境中寻找复苏的微秒。
*   **触发条件**: 双重 Z-Score 校验。计算 $VIX3M - VIX$ 期限利差的 3 日修复动量，必须同时满足：
    *   短期激变：$Z_{fast\_20d} > 2.0$
    *   长期尾部：$Z_{slow\_252d} > 3.0$
    *   恐慌见顶：$VIX_{momentum} < 0$
*   **输出**: `kill_switch_active` (Bool)，具备最高覆写权。

### 3.4 独裁映射状态机 (`src/engine/v11/signal/hysteresis_exposure_mapper.py`)
*   **职责**: 将 $P(BUST)$ 转换为散户绝对执行指令。
*   **状态跃迁**:
    *   `QLD` $\to$ `QQQ`: 当 $P(BUST) > 0.40$
    *   `QQQ` $\to$ `CASH`: 当 $P(BUST) > 0.75$
    *   `CASH/QQQ` $\to$ `QLD`: 仅当 $P(BUST) < 0.20$ 或 `kill_switch` 被激活。
*   **制约**: 受结算物理锁（Cooldown Timer）和降级审计（Overrider）的双重拦截。

---

## 4. UI/Dashboard 规范 (Behavioral Containment)

仪表盘是控制人性的核心刑具，必须按五种绝对隔离的模式展示：

1.  **[🟢 CRUISE MODE / 巡航模式]**: $P(BUST) < 0.2$。100% QLD。隐藏短期波动率噪音。
2.  **[🟡 SHIELD DEPLOYED / 装甲模式]**: $P(BUST) > 0.4$。100% QQQ。展示宏观引力恶化警告。
3.  **[🔴 BLACKOUT / 物理断网]**: $P(BUST) > 0.75$。100% CASH。隐藏买入功能，展示绝对防守立场。
4.  **[🔒 SETTLEMENT LOCK / 结算冻结]**: T+1 锁定期内。全屏置灰，显示强制冷却倒计时。
5.  **[🔥 RESURRECTION / 猎杀复苏]**: Kill-Switch 触发。红色闪烁转绿，要求全量回归 QLD。

---

## 5. 验收标准 (Acceptance Criteria)
1.  **数据鲁棒性**: 在注入至少 5 个随机 `NaN` 和极限尖刺的 2020 年模拟中，系统不得崩溃，必须正确触发优雅降级。
2.  **左侧逃顶**: 在 2020 年 3 月 9 日之前，状态机必须至少已成功降级至 `QQQ`。
3.  **右侧猎杀**: Kill-Switch 必须在 2020 年 3 月下旬精准触发，且后续无高频洗盘震荡。
4.  **纪律强制性**: 所有调仓指令必须在随后触发不少于 1 个交易日的信号静默期。
