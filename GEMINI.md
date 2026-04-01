# GEMINI.md - QQQ Bayesian Orthogonal Factor Monitor (v12.0)

> **Repository Master Guidelines & Architecture Spec**
> 本文档是项目的唯一事实来源 (SSoT)，涵盖了架构设计、编码规范、操作指南及合规准则。

---

## 1. 项目综述 (v12.0 Orthogonal-Core)
`qqq-monitor` 在 v12.0 中全面进化为“贝叶斯正交因子引擎”。系统通过三层 10 因子的正交矩阵，利用信息熵控制与 Gram-Schmidt 正交化算法实现全天候宏观风险定价。

### 核心架构核心 (Core Architecture)
- **Orthogonal Matrix (v12):** 三层因子架构（贴现层、实体层、情绪层），彻底消除信息近亲繁殖。
- **Gram-Schmidt Engine:** 在线正交化。通过 Expanding Window 残差提取，确保 MOVE 与利差等因子的条件独立。
- **PIT Integrity Layer:** 点时合规层。严格对齐金融 (T+1)、实体 (Release+30d) 与盈利 (MonthEnd+30d) 的物理发布滞后。
- **Shannon Entropy Controller:** 风险调节层。基于后验分布熵值对敞口执行惩罚 (Haircut)，实现信息诚实性。
- **Inertial Beta Mapper:** 决策平滑层。在确保敞口符合贝叶斯期望的前提下，通过惯性机制减少换手。

---

## 2. 项目结构与模块职责 (Project Structure)
- `src/engine/v12/`: 决策引擎核心。**v12.0 贝叶斯正交推断逻辑**。
- `src/collector/`: 数据采集器。对接 FRED, yf, **Shiller TTM EPS**。
- `src/models/`: 领域模型。定义 PortfolioState, SignalResult 等数据契约。
- `src/store/`: 存储层。管理 DNA (CSV), Prior (JSON) 及 Vercel Blob 同步。
- `src/output/`: 输出层。生成 Web 状态、JSON 报告及 Discord 实时通知。
- `src/main.py`: 生产入口。执行每日 live 推断流程。
- `src/backtest.py`: 审计入口。执行 **PIT 合规**的全量性能回归。

---

## 3. 编码规范与命名准则 (Coding Style & Guardrails)
所有代码变更必须严格遵守以下 **AC (Acceptance Criteria)** 准则：

- **AC-6 PIT 完整性**: 严禁在回测中使用未来函数。必须通过物理发布滞后模拟历史真实可见性。
- **AC-8 10 因子三层正交**: 所有因子必须归属于 Discount, Real Economy 或 Sentiment 层。
- **AC-10 Gram-Schmidt 正交化**: MOVE 与信用利差必须执行残差化处理，以满足独立性假设。
- **AC-7 熵增诚实性**: 承认高维空间的稀疏性。严禁为追求虚高准确率而下调 `var_smoothing`。
- **AC-2 数值一致性**: 所有宏观指标必须采用**小数单位** (e.g. ERP 0.05)，严禁使用百分点。
- **AC-4 意志与行动分离**: 信号接口必须同时包含 `raw_target_beta` (原始推断) 与 `target_beta` (执行目标)。
- **AC-0 无硬编码参数**: 所有决策权重与基准必须源自 `regime_audit.json`。
- **AC-5 冷启动智能对齐**: 缺失 T0 状态时必须对齐首日原始期望，严禁使用固定默认值。

---

## 4. 运行与操作指令 (Operations)
**强制要求**: 禁止在宿主机直接运行 Python/Pip。必须使用 Docker 环境。

### 4.1 生产推断 (Production)
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.main
```

### 4.2 性能审计与回测 (Fidelity Audit)
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.backtest --evaluation-start 2010-01-01
```

### 4.3 核心测试 (Unit Testing)
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] pytest tests/unit/engine/v12 -q
```

---

## 5. 开发与审计入口 (SSoT Index)
- **架构规格书**: `docs/versions/v12/V12_ORTHOGONAL_FACTOR_SPEC.md`
- **产品需求 (PRD)**: `docs/core/PRD.md`
- **核心哲学**: `docs/core/V12_USER_PHILOSOPHY.md`
- **宏观 DNA 库**: `data/macro_historical_dump.csv`
- **审计配置文件**: `src/engine/v12/resources/regime_audit.json`

---
© 2026 QQQ Entropy 决策系统开发组.
