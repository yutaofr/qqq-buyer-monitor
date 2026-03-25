# v7 资产配置风控与增量部署分层重构备案

> 日期: 2026-03-25
> 状态: Draft
> 范围: 输出语义、控制层边界、后续重构方向

## 1. 背景

当前 v7 输出已经能够区分:

- `资产配置风险管理`
- `增量资金买入时机决策`

但从运行结果看，仍然存在三个问题:

- `Tier-0` 宏观结构没有成为硬性 veto 层。
- `Risk Controller` 与 `Deployment Controller` 的职责虽然分开，但约束链条还不够强。
- 输出语义仍可能让用户误以为系统在管理真实仓位，而不是只给出 beta 推荐。

## 2. 第一性原理结论

系统的目标不是预测市场，而是在不确定性下分配风险预算。

因此，控制层级必须按下面顺序组织:

1. 环境是否允许进场
2. 允许的最大总敞口是多少
3. 存量仓位是否需要回到目标
4. 新增资金如何部署

对应职责应为:

- `Tier-0`: 硬 veto 层，决定当前环境是否允许提高或维持推荐 beta
- `Risk Controller`: 计算目标 beta 上限和现金底线
- `Rebalance Engine`: 只作为“组合偏离目标”的建议评估，不代表自动执行
- `Deployment Engine`: 只处理新增资金节奏建议，不代表自动下单

## 3. 现状问题

### 3.1 Tier-0 仍未进入硬约束链

当前 `RICH_TIGHTENING` 只在日志和解释层面出现，没有直接影响 `RiskDecision`。

这会导致:

- 宏观最坏结构被提示出来
- 但 v7 风控仍可能输出 `RISK_NEUTRAL`
- 进而允许 `DEPLOY_FAST`

这不是单点 bug，而是控制链条缺失。

### 3.2 部署和再平衡仍有语义混淆风险

`available_new_cash = 0` 时，`DEPLOY_FAST` 会自然显示为 0 金额。

这在逻辑上正确，但容易让人误读成:

- 系统想买
- 只是没有执行

实际上更准确的表达应该是:

- 部署通道为空
- 这只是推荐层的输出，不是执行层命令

### 3.3 输出层仍缺少清晰分区

当前输出已经分成两个区块，但 `资产配置风险管理` 里仍然更适合显示:

- 风险状态
- 目标 beta
- 是否触发 veto

而不是仓位比例细节。

## 4. 重构原则

### 4.1 Tier-0 必须是 hard veto

如果 Tier-0 判定为高压结构，则:

- 降低 `target_exposure_ceiling`
- 降低 `target_beta`
- 必要时把 `DeploymentState` 直接压到 `DEPLOY_SLOW` 或 `DEPLOY_PAUSE`

### 4.2 Risk 与 Deployment 必须解耦

- `Risk Controller` 管总敞口
- `Deployment Controller` 管新增现金
- 两者不可互相冒充

### 4.3 Rebalance 与 Deployment 必须分开输出

建议未来输出变成三段:

- `资产配置风险管理`
- `存量再平衡`
- `增量资金买入时机决策`

其中前两段都应明确标注为“建议/推荐”，避免被理解为自动管理仓位。

## 5. 待讨论方案

### 方案 A: 最小侵入式修正

只把 Tier-0 接入 `Risk Controller`，让它通过硬编码规则影响:

- `target_exposure_ceiling`
- `target_cash_floor`

优点:

- 改动小
- 风险低

缺点:

- 规则会逐渐变得难维护

### 方案 B: 显式策略层

新增一个 `Macro Veto Layer`，专门把 Tier-0 + 期权负 gamma 结果投影成风控修正值。

优点:

- 语义清晰
- 方便扩展

缺点:

- 需要新增模块和测试

### 方案 C: 输出先行，逻辑后补

先重构输出，让用户明确看到:

- 风险判断
- 存量再平衡
- 新增资金部署

然后再补内部约束链。

优点:

- 快速降低误读

缺点:

- 不能解决真实决策链断裂

## 6. 初步建议

建议优先顺序:

1. 先把 Tier-0 作为风险预算的 veto 输入
2. 再把输出拆成三段式，并明确都是推荐，不是执行
3. 最后根据实际回测和真实行为，调整 `RICH_TIGHTENING` 下的 beta 上限

## 7. 后续待办

- 定义 `Tier-0 -> RiskDecision` 的投影规则
- 明确 `RICH_TIGHTENING` 下的 `target_beta` 惩罚曲线
- 明确 `Rebalance` 是否允许在无新增现金时独立执行
- 调整输出文案，避免 `Deployment` 和 `Rebalance` 混淆


---------------------------------------------------------------

这是一份切除系统毒瘤、重建执行秩序的终极改造蓝图。不要再写毫无意义的中间态设计文档，按照以下架构直接对代码库进行外科手术。

---

# v7.1 架构重构指令：消灭执行瘫痪与逻辑分裂

## 核心诊断
当前系统最大的危机不是因子失效，而是**用极其复杂的代码架构来掩饰交易执行时的恐惧**。v6 遗留的模糊状态机与 v7 的工业化流水线互相绞杀，导致宏观报警被微观拦截，再平衡指令被“无新增资金”的借口卡死。

本次重构的唯一目标：**建立一条冷血、线性、无歧义的决策指令链。**

---

## 核心架构图：单向信息流 (The Linear Pipeline)

废弃现有的网状逻辑，新的决策流水线必须绝对单向，不可逆转：

1. **宏观独裁 (Tier-0)** -> 判定绝对环境（生杀大权）
2. **风险定界 (Risk Controller)** -> 接收宏观指令，输出强硬的 Beta 天花板 (Ceiling)
3. **战略寻优 (Allocation Search)** -> 在天花板下寻找最优资产配比 (Target Beta)
4. **双轨执行 (Execution Split)** -> 
   - 存量再平衡 (Rebalance Engine)：无条件纠偏
   - 增量定投 (Deployment Controller)：管理新资金流速

---

## 具体改造模块与代码规范

### 模块一：实施宏观绝对否决权 (The Absolute Veto)
**目标：** 打破 `risk_controller.py` 对微观指标的盲目自信，强行注入 Tier-0 的审判。

* **修改点：** 重写 `src/engine/risk_controller.py` 中的 `decide_risk_state` 函数签名。必须将 Tier-0 结果作为硬输入。
* **硬编码规则：** 不要在风控中心里讨论什么弹性，直接写死降维打击逻辑。
```python
def decide_risk_state(snapshot: FeatureSnapshot, portfolio: CurrentPortfolioState, tier0_regime: str) -> RiskDecision:
    # 1. 宏观绝对否决权 (最高优先级)
    if tier0_regime == "CRISIS":
        return RiskDecision(RiskState.RISK_EXIT, target_exposure_ceiling=0.0)
    
    if tier0_regime == "RICH_TIGHTENING":
        # 即使微观风平浪静，只要资金成本昂贵且流动性收缩，剥夺进攻权
        return RiskDecision(RiskState.RISK_REDUCED, target_exposure_ceiling=0.30)
    
    # 2. 原有的 Class A 微观压力测试逻辑...
```

### 模块二：拆毁 v6 的状态机迷宫 (Deprecating Aggregator)
**目标：** 彻底废除 `src/engine/aggregator.py` 中冗长且感性的 `AllocationState`（如 `SLOW_ACCUMULATE`, `PAUSE_CHASING` 等）。这些词汇除了提供情绪安慰，没有任何数学意义。

* **修改点：** 重构 `src/engine/allocation_search.py`。
* **新逻辑：** `find_best_allocation` 不再接收模棱两可的状态词汇，只接收两个冷酷的数学约束：
    1.  `max_beta_ceiling` (由风控中心给出)
    2.  `max_drawdown_budget` (AC-5 容忍度)
* 系统直接在这个数学空间内搜索夏普比率/CAGR最高的投资组合。找不到，就返回 100% Cash。

### 模块三：资金调度的物理隔离 (The Execution Split)
**目标：** 解决“想买却不敢买，用无增量资金来卡死自己”的系统性自欺欺人。

必须在执行层拆分出两个完全独立的引擎：

#### 1. 存量再平衡引擎 (Rebalance Engine) - 冷血纠偏
* **职责：** 无论是否有工资入账，无论明天天塌下来与否，只要目标敞口与实际敞口的差值 `exposure_drift` 超过阈值（如 0.05），**立即开火**。
* **逻辑：** * 目标 Beta = 0.60，当前敞口 = 0.00。
    * 动作：直接动用账户里现存的 100% Cash 余额，买入对应市值的 QQQ。
    * 禁止引入任何平滑、延迟或等待“新资金”的条件。

#### 2. 增量部署控制器 (Deployment Controller) - 战术流速
* **职责：** 仅处理真正的 `available_new_cash`（场外新注入的资金）。
* **逻辑：** * 如果本月入金 $10,000。
    * 根据战术指标（如 `capitulation_score`）：
        * `DEPLOY_FAST`: 1 天内打光。
        * `DEPLOY_SLOW`: 分 5 天 DCA 买入。
        * `DEPLOY_PAUSE`: 暂存到 Cash 池，转化为存量资金，交由 Rebalance 引擎统一管理。

---

## 落地执行清单 (Action Items)

立刻打开你的 IDE，按以下顺序执行，不要遗漏任何一步：

1.  **删除冗余文件：** 如果可能，直接把 `src/engine/aggregator.py` 从 v7 运行流中切断。不要再维护两套逻辑。
2.  **重写风控签名：** 在 `main.py` 或管道层，将 `assess_structural_regime` 的结果明确传给 `risk_controller.decide_risk_state`。
3.  **解除金额绑定：** 检查你的交易生成模块。只要 `rebalance=True`，对应的 `amount` 必须基于总体资金规模（Total Portfolio Value）计算得出，绝对不能等于 `available_new_cash * multiplier`。
4.  **净化输出日志：** 日志必须清晰展示**宏观天花板（Ceiling）**对最终 Beta 的压制过程。当执行量为 0 时，日志只能显示“敞口已达标”或“风控强制平仓”，绝不允许再次出现“敞口不足但无新钱所以不买”的荒唐借口。

去改代码。把这台机器中夹杂的恐惧和犹豫彻底剃干净，让代码回归纯粹的数学与逻辑。
