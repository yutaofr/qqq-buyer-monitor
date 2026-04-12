# PRD: V15 True Kelly Production Mainline Merge
> **版本**: V15.0 Integrator | **状态**: APPROVED | **依据**: `TRUE_KELLY_V15_INTEGRATION_SRD.md`

---

## 1. 产品背景与核心问题

### 1.1 决议背景
`feature/true-kelly-deployment` 已经在测试区和部分全量回溯中经过检验，取得了在复苏早期的明显加速效果（Recovery => Fast Deploy 概率达到 ~42%）。为了正式让业务侧享受到这一技术红利，系统架构委员会决议取消当前的 `Shadow` 并行孤岛状态，正式切入核心运行引擎。

### 1.2 核心痛点防范
之前的审计揭示，全负荷运转凯利（Half-Kelly）导致了相对较高的交易摩擦与 2倍放大的回撤（MDD）。这在量化产品上是无法容忍的系统性破壁行为。此合入要求必须进行参数控制。

## 2. 核心用例 (Use Cases)

### UC-01: 生产级策略接管
- **触发条件**：V11Conductor 初始化
- **业务动作**：将底层风控策略引擎强行更换为 `KellyDeploymentPolicy`。原本启发式打分的 `ProbabilisticDeploymentPolicy` 进入冻结回收状态。

### UC-02: 回撤硬隔离防火墙
- **触发条件**：业务部署比例演算
- **业务动作**：系统强行应用降权的 `Quarter-Kelly (参数为 0.25)` 进行资金暴露度限制，对极端的高杠杆押注设限，以缩小与原有基线的 MDD 幅度差。`erp_weight` 强制锁定为 `0.2` 进行低偏好倾向控制。

### UC-03: 诊断日志穿透
- **触发条件**：策略的每一次单步执行 (daily_run)
- **业务动作**：确保凯利计算的中间体 `kelly_fraction` 能随着决策包输出给系统的调用者以保持后期的遥测洞察能力。

---

## 3. 非功能性需求

*   **100% API 隔离无感**：原系统外部调用者将不能感知到内部引擎类的更换，`KellyDeploymentPolicy` 契约应完全承担起所有的输入和调用责任。
*   **审计抗干涉机制**：不允许在进行引擎更替过程时引入可能暴露“未来点数据”以影响当期算式的 `lookahead` 数据。执行 PIT (Point-In-Time) 强制监控防线。

## 4. 交付成功验收标准

| 验收代码 | 描述 |
|:---|:---|
| **AC-1 API 无损接管** | `test_conductor.py` 对于内部行为模拟的集成检测全数 GREEN。 |
| **AC-2 参数强校验** | Quarter Kelly 初始化约束参数在组件测试中不可打破。 |
| **AC-3 实盘仿真成功** | 完成一次端到端无异常退出的 `backtest` 回放。 |
| **AC-4 安全审查** | Docker 环境内的 Forensic 测试 `test_pit_leakage.py` 通过。 |

---

© 2026 QQQ Entropy AI Governance — V15 Production Merge PRD
