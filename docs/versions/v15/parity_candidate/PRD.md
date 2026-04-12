# PRD: V15 Backtest Parity & Strict Non-Interference
> **版本**: V15.0 Parity Diagnostics | **状态**: APPROVED | **依据**: `V15_BACKTEST_PARITY_SRD.md`

---

## 1. 产品背景与核心问题

### 1.1 背景
在此前的 V15 审计合并预演中发现：Main 分支的贝叶斯推断基线指标（如 Top-1 Accuracy 为 69%）与当前合并分支（Accuracy 为 54%）发生了显著下降。
初步排查结论表明：**并非 True Kelly 的合入污染了引擎，而是回放测试使用的工作台参数组合产生了断层**（Main分支使用 `classifier_only` + var_smoothing `0.0001`；合并分支使用 `runtime_reweight` + `0.001` 且约束了 Evaluation Start）。

### 1.2 目标定义（The Proof of Innocence）
在真正的量化工程中，不能仅仅“认为”两者无关。本 PRD 的核心是**通过控制变量法的可重复实证，从数学上自证 Kelly 的代码替换属于推断无损性（Inference-Neutral）。**

---

## 2. 核心用例 (Use Cases)

### UC-01: Parity Backcast (等价回溯验证)
- **触发条件**：在集成了 `KellyDeploymentPolicy` 的现用 `feature/true-kelly-deployment` 的管道上直接运行。
- **业务动作**：执行完整的 `run_v12_audit` (采用 `runtime_reweight` 与平滑系数 `0.001`)。
- **目标输出**：仅抽离出对于推断能力的质量刻画数值（Top-1 Accuracy，Brier Score，Mean Entropy 等）。

### UC-02: Parity Report Generation
- **触发条件**：回溯产生最终 Summary 后引发。
- **业务动作**：固化输出比对基准报告记录，生成 JSON / MD 工件。必须指出 `50%~60%` 准确率恰恰是在 `runtime_reweight` 惩罚模式下的正常水准，彻底洗清对引擎代码退化的指控。

---

## 3. 非功能性需求与红线约束

*   **100% 隔离运行**：为了确保审计信度，此验证不能侵入或打补丁修补任何现有的回测库或是主引擎库程序。必须利用原本闭环的接口进行外部挂载测试。
*   **不干涉原则**：绝不准通过强行锁定随机状态或通过修改预知数据来迎合伪造指标，要的就是在现有环境运行所得出的野生精确数据。

### 禁止项（Red Lines）
| 绝对禁区 | 原因 |
|:---:|:---|
| `src/engine/v11/conductor.py` | 主网网关已经过审计锁死，不可动摇其物理状态以证清白 |
| `src/backtest.py` 及内部逻辑 | API 已经存在，审计程序如果能被篡改即失去公信力 |

---

## 4. 成功验签标准

| 验收编号 | 描述 |
|:---|:---|
| **AC-P1** | `docker-compose run kelly-parity` 返回 Exit Code 0 并生成预定期望的报告文件。 |
| **AC-P2** | `kelly_parity/parity_summary.json` 中记录的 Top-1 Accuracy 返回在理论合理区间 [0.50, 0.60] 内，证实环境切换。 |
| **AC-P3** | 全站单元测试保持 0 Regression 的清白姿态 (ALL PASS)。 |

---
© 2026 QQQ Entropy AI Governance — V15 Parity Diagnostics PRD
