# tracks.md — V15 Production Merge 实施轨道
> 全局实施计划 | 架构: architecture.md | SRD: TRUE_KELLY_V15_INTEGRATION_SRD.md

所有节点需服从强次序执行限制。遵循 “测试失败证明有效 -> 代码实现 -> 测试变绿闭环” 的严格 TDD 法则。

---

## 节点依赖图谱 (Execution DAG)

```
M-01 (TDD 更新 test_conductor)
  └─> M-02 (代码融合: conductor.py 强袭替换)
        └─> M-03 (隔离集成测试放行 AC-1, AC-2)
              └─> M-04 (全栈测试集防御网 AC-2)
                    └─> M-05 (实境回测验证 - Backtest AC-3)
                          └─> M-06 (法务级渗透测试 - Forensic AC-4)
                                └─> M-07 (最终版本快照审计 & 发推)
```

---

## 节点执行规范

### M-01 — 更新 `test_conductor.py`（TDD 测试修改）
- **状态**: `[DONE]`
- **锁定文件**: `tests/unit/engine/v11/test_conductor.py`
- **操作原则**:
  - 更换 Mock 目标自 `ProbabilisticDeploymentPolicy` 至 `KellyDeploymentPolicy`。
  - 新增函数校验策略类：实例化时传入参数必然是 `kelly_scale=0.25` 且 `erp_weight=0.2`。
- **验收**: 运行 `docker-compose run test -k test_conductor` 获得 **明确 FAIL**。

---

### M-02 — 实施 `conductor.py` 主体并流
- **状态**: `[DONE]`
- **锁定文件**: `src/engine/v11/conductor.py`
- **操作原则**:
  - 剔除对旧版类的引入。
  - 在 `__init__` 中用 `KellyDeploymentPolicy` 替换 `self.deployment_policy`，按架构硬编码 `kelly_scale=0.25`, `erp_weight=0.2`, `regime_sharpes=self.regime_sharpes`。
  - 补齐 `kelly_fraction` 日志暴露（如需）。

---

### M-03 — 跨域验证点隔离消除 (AC-1, 2)
- **状态**: `[DONE]`
- **操作原则**: 回收跑 M-01 的单元命令。
- **验收**: 
  ```bash
  docker-compose run test -k test_conductor
  ```
  全数 PASS GREEN。

---

### M-04 — 基本功能护城河 (全栈回归测验)
- **状态**: `[TODO]`
- **目标**: 清除牵连受损隐患（例如部分其他 overlay 强依赖对象模型变质等）。
- **验收**:
  ```bash
  docker-compose run test
  ```
  407+ Tests 全量 GREEN。

---

### M-05 — 实境回测宏实验 (AC-3)
- **状态**: `[TODO]`
- **操作**: 
  ```bash
  docker-compose run backtest
  ```
- **验收**: 无抛出执行异常，`macro_backtest` 目录最新生成的回测数据指标可接受。确保 PnL 跑赢极值崩溃，系统不出现 NaN。

---

### M-06 — 法务与物理隔离穿越封锁检验 (AC-4)
- **状态**: `[TODO]`
- **目标**: `forensic` 工具用于探测系统运行中潜在产生的高延迟及先知式 `lookahead` 数据穿越 Bug (Time Traversal 漏洞)。确保没有泄漏。
- **验收**:
  ```bash
  docker-compose run forensic
  ```
  执行完成且无警告抛出。

---

### M-07 — 收官审计与最终代码核准
- **状态**: `[TODO]`
- **操作**:
  - `git diff --stat HEAD` 保证只触动了 `conductor.py` 以及相关 `tests/` 内件。
  - 为分支添加稳定快照。
  - 合规进入 Ready-To-Merge 主主态（Master/Main Deploy State）。

---
© 2026 QQQ Entropy AI Governance — V15 Track Schedule
