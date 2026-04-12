# Architecture: V15 True Kelly Mainline Integration
> 支撑文档: `TRUE_KELLY_V15_INTEGRATION_SRD.md` | 关联 PRD: `PRD.md`

---

## 1. 模块划分与角色修正

```
src/engine/v11/
├── conductor.py                  # ✅ [核心枢纽/Modified] 主导全局推导流，替换 Policy
└── signal/
    ├── kelly_deployment_policy.py    # 🔓 [Provider] 状态计算接盘者
    └── deployment_policy.py          # 🔒 [Deprecated] 保留仅做留存追踪，剥离业务
    
tests/
└── unit/engine/v11/
    └── test_conductor.py         # ✅ [Validate/Modified] 修改 Mock 断言，确保正确执行 Quarter Kelly 指令
```

---

## 2. 接口契约（API Contracts）更改点

### 2.1 `V11Conductor.__init__` 
- **依赖倒置替换**: 将内部的依赖项 `self.deployment_policy` 设定为 `KellyDeploymentPolicy` 的实例。
- **强制输入契约参数**:
  - `kelly_scale`: `0.25` (float) -> Quarter-Kelly 阻断降温
  - `erp_weight`: `0.2` (float) -> 低 ERP 容忍偏好
  - `regime_sharpes`: `self.regime_sharpes` (Mapping[str, float]) -> 引入全局 Audit 环境验证。

### 2.2 `V11Conductor.daily_run()` (执行层推演)
- **数据流闭环**:
  - `deployment_decision` (Dict): 保证包含原先有的所有键 + `kelly_fraction` (float) 
  - 外界提取 `pipeline_result` 字段能够获取真实的部署比例缩放 `norm_h` 等因素不受影响。

---

## 3. 依赖关系图（重塑后）

```
 [Macro Features]      [Regime Prior Book]
         └─────────────┬────────────┘
                       ▼
             [V11 Conductor Engine]
             (调用)          (审计诊断注入)
               │                 │
    (移除原Probabilistic)        │
               │                 ▼
        [KellyDeploymentPolicy] ----> (产生 kelly_fraction 及 Deployment Multiplier)
               │
               ▼
   [Pipeline Result Evaluator]
               │
               ▼
[Execution / Risk Management Engine]
```

---

## 4. 绝对禁区（Red Lines）

| 禁区模块 | 控制级别 | 核心约束原则 |
|:---|:---:|:---|
| `src/engine/v11/core/kelly_criterion.py` | 🔴 绝对禁止 | “祖宗之法不可变”。凯利核心公式已锁闭，更改即破坏数学收敛平衡线。 |
| `src/engine/v11/signal/kelly_deployment_policy.py` | 🔴 绝对禁止 | “各司其职”。策略模块只解决算量，不应为外部系统妥协输出接口结构。 |
| `src/engine/v11/resources/regime_audit.json` | 🔴 绝对禁止 | “严禁重写宇宙常量”。基础锚定参数不得篡改，确保历史后验检验的数据基准线一致。 |

---

© 2026 QQQ Entropy AI Governance — V15 Integration Architecture
