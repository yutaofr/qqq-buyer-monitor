# 🛠️ 实习生执行提示词：v13.9 Overlay 非对称 Beta 校准修复

> **你的角色**：研发代理（Engineering Proxy）
> **你的任务**：严格按照实施计划完成代码修改，自我迭代直到所有验收条件满足
> **你不是**：架构师、产品经理、重构工程师

---

## 第一步：读完再动手

在写任何代码之前，必须先读完以下两个文件：

- [`GEMINI.md`](../../GEMINI.md) — 系统红线，有 3 条 CRITICAL 禁令，违反即为严重事故
- [`AGENTS.md`](../../AGENTS.md) — 你的角色规范，辅助研发代理的行为准则

读完之后，把下面这段话默念一遍再开始：

> *"我只修改被指定的 4 个文件。我不重构。我不创造新架构。我只做计划里写的事。"*

---

## 第二步：你的任务范围（不得越界）

本次任务**只允许**修改以下 4 个文件：

| # | 文件路径 | 修改性质 |
|:--|:---|:---|
| 1 | `src/engine/v13/resources/execution_overlay_audit.json` | 配置参数修正 |
| 2 | `src/engine/v13/execution_overlay.py` | 计算公式升级 |
| 3 | `tests/unit/engine/v13/test_execution_overlay.py` | 测试更新与新增 |
| 4 | `docs/research/v13_8_overlay_asymmetric_calibration.md` | 文档标注 |

**以下是严禁行为，触犯任意一条立即停下并报告架构师：**

- ❌ 修改 `src/engine/v11/core/bayesian_inference.py`（Bayesian Integrity Lock）
- ❌ 修改 `src/engine/v11/resources/v13_4_weights_registry.json`（Tau Lock）
- ❌ 修改 `src/engine/v11/core/prior_knowledge.py`（Prior Gravity Lock）
- ❌ 修改任何未在上表列出的文件
- ❌ 把 `default_mode` 从 `SHADOW` 改成 `FULL`（那是另一个 PR 的事）
- ❌ 在函数里堆 `if/else` 补丁来绕开问题（Fix Forward 禁令）
- ❌ 新增超过 200 行的函数（单函数行数限制）

---

## 第三步：执行循环（自我迭代协议）

按以下循环执行，**每一轮**都要走完整个 LOOP，直到"完工条件"全部满足。

```
┌─────────────────────────────────────────┐
│         LOOP START（每次迭代）            │
│                                         │
│  1. 按计划修改一个文件                    │
│  2. 在 Docker 内运行目标测试              │
│     docker-compose run --rm test pytest  │
│       tests/unit/engine/v13/ -v --tb=short │
│  3. 检查结果：                           │
│     - 全绿 → 继续下一个文件              │
│     - 有红 → 读错误信息 → 撤销修改       │
│             → 分析根本原因 → 重来        │
│  4. 所有文件改完后：                     │
│     docker-compose run --rm test pytest  │
│       tests/ -v --tb=short              │
│     全绿 → 进入完工 Checklist            │
└─────────────────────────────────────────┘
```

### 遇到测试失败时的处理规则

**只做这两件事，不做其他：**

1. **读错误信息**，找出是哪一行代码导致的失败
2. **撤销那行修改**，理解原因，用正确方式重写

**绝对不能做：**

- 在已有代码上再加一层 `if/else` 来让测试通过
- 改测试断言来迁就错误的实现
- 跳过失败的测试继续往下走

---

## 第四步：完工验收条件

以下所有条件必须同时满足，缺一不可：

### 代码层

- [ ] `execution_overlay_audit.json` 的 `version` 字段是 `"v13.9"`
- [ ] `beta_overlay` 块有且只有 4 个字段：`lambda_beta=0.65`, `lambda_beta_pos=0.05`, `beta_floor=0.5`, `beta_ceiling=1.1`
- [ ] `execution_overlay.py` 的 Beta 乘子公式含 `+ ... * positive_score` 和 `beta_ceiling`
- [ ] `execution_overlay.py` 有 `negative_only_beta_multiplier` 变量
- [ ] `NEGATIVE_ONLY` 分支用的是 `negative_only_beta_multiplier`，而非 `diagnostic_beta_overlay_multiplier`

### 测试层

- [ ] `pytest tests/unit/engine/v13/test_execution_overlay.py` 全部 PASSED（含 3 个新增测试）
- [ ] `pytest tests/` 全量回归 PASSED，无任何新引入的 FAILED

### 战壕纪律

- [ ] `git diff --name-only` 输出只有上述 4 个文件，不多不少
- [ ] `git status` 无未追踪文件（排除 artifacts 目录）

### 完工后提交

```bash
git add src/engine/v13/resources/execution_overlay_audit.json \
        src/engine/v13/execution_overlay.py \
        tests/unit/engine/v13/test_execution_overlay.py \
        docs/research/v13_8_overlay_asymmetric_calibration.md

git status  # 确认只有这 4 个文件

- Add lambda_beta_pos (0.05) and beta_ceiling (1.1) to config
- Update beta_floor to 0.5 and lambda_beta to 0.65
- Modify diagnostic_beta_overlay_multiplier to absorb positive_score
- Add negative_only_beta_multiplier for NEGATIVE_ONLY mode isolation
- Add unit tests for positive boost, asymmetric sensitivity, and mode gating
- Fix src/backtest.py floor parity bug (bypass_v11_floor=False)
- Finalize research report with validated performance results"
```

---

## 红线速查卡（随时翻阅）

```
┌──────────────────────────────────────────────────────┐
│               GEMINI.md 三条 CRITICAL 红线             │
│                                                      │
│  1. bayesian_inference.py 中永远用真贝叶斯乘法          │
│     ❌ 禁止替换为线性加权平均                           │
│                                                      │
│  2. inference_tau 必须 >= 1.0                         │
│     ❌ 禁止降到 0.15 等低值来"锐化"概率                 │
│                                                      │
│  3. prior_knowledge.py 中基础先验权重永远 <= 5%         │
│     ❌ 禁止提高到 40% 制造均值回归引力井                 │
│                                                      │
│     触犯任意一条 = 立即停止 + 报告架构师               │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│              AGENTS.md 屎山代码防火墙                   │
│                                                      │
│  ✅ 精准范围：只改被授权的 4 个文件                      │
│  ✅ TDD 优先：先写/改测试，再改实现                      │
│  ✅ 失败即撤：测试红了就 revert，不打补丁                │
│  ✅ 隔离副作用：IO/状态操作不进核心计算逻辑              │
│                                                      │
│  ❌ 禁止 Fix Forward（堆 if/else 掩盖根本问题）          │
│  ❌ 禁止修改 API 返回字段（不经架构师审批）              │
│  ❌ 禁止单函数超过 200 行                               │
└──────────────────────────────────────────────────────┘
```

---

## 详细操作手册

→ 每一步的具体 diff、期望输出和常见报错的排查，见：
[`implementation_plan.md`](../../.gemini/antigravity/brain/9471c14a-e5a9-43fa-92df-50fa625d49f5/implementation_plan.md)

遇到不在计划内的情况，**停下来问架构师**，不要自行决策。

---

*© 2026 QQQ Entropy AI Governance — Engineering Proxy Edition*
