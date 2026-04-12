# SRD: V15 True Kelly Production Integration (Mainline Merge)
> **版本**: V15.0
> **状态**: DRAFT (Pending TDD Implementation)
> **依据**: `docs/audit/kelly-audit.md` (Shadow Audit 决议)

---

## 1. 架构目标与前置条件

根据 `kelly-audit.md` 第 6 节的审计决议，True Kelly 模块已在 Shadow 模式下被证明在恢复期能提供卓越的跟进能力（Fast Deploy 率提升），但由于 PnL 回测中发现 2倍的 MDD 放大，**必须实施降权缓解方案（Quarter-Kelly）后方可切入主网执行引擎 (`conductor.py`)**。

本次 SRD 的目标是**打破原有的修改隔离红线**，正式将 `KellyDeploymentPolicy` 取代原本的 `ProbabilisticDeploymentPolicy` 接入 `src/engine/v11/conductor.py`。

### 1.1 必须满足的融合条件
1. **参数固化**: 必须强制使用 Quarter-Kelly 缩放 (`kelly_scale=0.25`) 抑制高频切换带来的滑点与回撤风险。
2. **测试重写**: `conductor.py` 的测试用例以及所有依赖于旧版部署反馈状态的桩测试都需要调整。
3. **性能衰退验证**: 修改后，必须运行全量历史回测，确保整体系统的 CAGR / MDD 不劣于基线要求。
4. **PIT 泄露防御**：保证 True Kelly 内部所依赖的 `erp_percentile` 以及其它相关代理在 `conductor` runtime 调用时，绝不穿透未来数据。

---

## 2. 实施范围 (Scope)

### 2.1 允许修改的文件
- ✅ `src/engine/v11/conductor.py` (主网集成注入点)
- ✅ `tests/unit/engine/v11/test_conductor.py` (修改针对 Conductor 的单元验证)
- ✅ `tests/unit/engine/v11/test_conductor_overlay_integration.py` (若受波及需同步更新)

### 2.2 维持禁区
- ❌ `src/engine/v11/core/kelly_criterion.py` (数学核心，严禁二次修改)
- ❌ `src/engine/v11/signal/kelly_deployment_policy.py` (策略逻辑已固化)
- ❌ `src/engine/v11/resources/regime_audit.json` (禁止调整基础夏普期望)

---

## 3. 集成改造规格

### 3.1 `conductor.py` 改造
**位置**: `src/engine/v11/conductor.py` -> `V11Conductor.__init__`

需将以下初始化代码：
```python
# 旧版 (即将被替换)
from src.engine.v11.signal.deployment_policy import ProbabilisticDeploymentPolicy

self.deployment_policy = ProbabilisticDeploymentPolicy(
    initial_state=str(
        execution_state.get("deployment_state", "DEPLOY_BASE") or "DEPLOY_BASE"
    ),
    evidence=float(execution_state.get("deployment_evidence", 0.0) or 0.0),
)
```
**更改为**：
```python
# V15 新版 (True Kelly 接入)
from src.engine.v11.signal.kelly_deployment_policy import KellyDeploymentPolicy

self.deployment_policy = KellyDeploymentPolicy(
    initial_state=str(
        execution_state.get("deployment_state", "DEPLOY_BASE") or "DEPLOY_BASE"
    ),
    evidence=float(execution_state.get("deployment_evidence", 0.0) or 0.0),
    kelly_scale=0.25,          # 审计硬性要求：Quarter Kelly 控制回撤
    erp_weight=0.2,            # 审计最佳配置：Low ERP Weight
    regime_sharpes=self.regime_sharpes # 从 audit_data 中加载的实证数据
)
```

**位置**: `src/engine/v11/conductor.py` -> `V11Conductor.daily_run`
因为两者输入字典完全一致，且 `decide` 参数高度兼容，**`daily_run`的逻辑应当极少甚或不需要更改**。唯一需要检查的地方是在日志抓取或监控结构体传递时，是否需要补集 `kelly_fraction` 到指标追踪中去。

```python
# 确保诊断中携带 kelly 溯源日志
pipeline_result["kelly_fraction"] = deployment_decision.get("kelly_fraction", 0.0)
```

---

## 4. TDD 测试修正规格

由于依赖注入变更，`tests/unit/engine/v11/test_conductor.py` 中所有的断言必须重新进行标定：

### 4.1 Mock / Spy 改动
原先针对 `ProbabilisticDeploymentPolicy` 的 `patch` 需修改为 `patch("src.engine.v11.conductor.KellyDeploymentPolicy")`。

### 4.2 预期行为变更验证
编写一个新的隔离化集成测试：
```python
def test_v15_integration_kelly_scale_constraint():
    """V15 架构要求 Conductor 初始化时，必须将 KellyDeploymentPolicy 的 kelly_scale 限制为 0.25"""
    conductor = V11Conductor(...)
    # 验证强转型的防护栏
    assert conductor.deployment_policy.kelly_scale == 0.25, "Failure: Safety mechanism missing - must be quarter Kelly"
    assert conductor.deployment_policy.erp_weight == 0.2
```

---

## 5. 开发审计流程轨与最终放行要求

在正式实施时，系统开发代理 (Proxy) 必须遵照以下验证序列：

### T-01: TDD 修复
执行 `docker-compose run test -k test_conductor`，根据 Mock 失败信息实施 `conductor.py` 的重构，直到全数通过。

### T-02: 全栈单元回归
执行 `docker-compose run test`，确保 `V11Conductor` 的底层换心手术未波及 `panorama` 及 `backtest` 外围容器逻辑（0 failures, 0 errors）。

### T-03: 全量历史回测 (The Ultimate Truth)
执行：
```bash
docker-compose run backtest
```
检查生成的 `artifacts/macro_backtest/` 报告结果：
1. **防退化保护**: CAGR / Brier 指数不能引发断崖。
2. **MDD 目标**: 最大回撤相比之前必须不能显著膨胀，应观察是否已被 Quarter-Kelly 成功锁死在旧基准的幅度范围内。

### T-04: PIT 穿越审计
执行：
```bash
docker-compose run forensic
```
杜绝在参数传输（特别是 `erp_percentile` 实时反演）期间产生未来信息渗透。需全部全绿 PASS。

---

## 6. 合规签字放行
只要完成 T-01 ~ T-04 所有节点全绿执行：
**架构层面直接宣告 V15 完备并准许合并发版！**

© 2026 QQQ Entropy AI Governance — V15 Production Integration SRD
