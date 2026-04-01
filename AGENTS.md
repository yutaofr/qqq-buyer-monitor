# AGENTS.md - Repository Guidelines & Execution

> **The Execution Guide & Development Mandate**
> 本文档定义了项目的开发规范、操作命令与模块职责。架构原理与设计哲学请参见 **[GEMINI.md](./GEMINI.md)**。

---

## 1. 项目结构与模块职责 (Project Structure)
- `src/engine/v12/`: 决策引擎核心。执行 **v12.0 贝叶斯正交推断**。
- `src/collector/`: 传感器层。采集 FRED, yf, **Shiller TTM EPS**。
- `src/models/`: 数据契约。定义 PortfolioState, SignalResult 等领域模型。
- `src/store/`: 存储与同步。管理 DNA (CSV), Prior (JSON) 及云端同步。
- `src/output/`: 输出与解释。生成 Web UI, JSON 报告及 Discord 通知。
- `src/main.py`: 生产入口。执行每日 live 流程。
- `src/backtest.py`: 审计入口。执行 **PIT 合规**的全量回归。

---

## 2. 编码规范：AC (Acceptance Criteria) 刚性准则
所有变更必须严格遵守以下 **v12.0 核心合规性** 准则：

- **AC-6 PIT 完整性**: 严禁回测中使用未来函数。物理发布滞后模拟是刚性要求。
- **AC-8 10 因子三层正交**: 所有因子必须归属于三层正交体系中的一层。
- **AC-10 Gram-Schmidt 正交化**: MOVE 与信用利差必须执行在线正交化处理。
- **AC-7 熵增诚实性**: 严禁为追求准确率而调小 `var_smoothing`。
- **AC-2 数值一致性**: 宏观指标必须采用**小数单位** (e.g. ERP 0.05)。
- **AC-4 意志与行动分离**: 接口必须显式返回 `raw_target_beta` 与 `target_beta`。
- **AC-0 无硬编码参数**: 决策基准必须源自 `regime_audit.json`。

---

## 3. 运行与操作指令 (Operations)
**注意**: 禁止在宿主机运行环境。必须使用 Docker。

### 3.1 生产推断与回测
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.main
docker run --rm -v $(pwd):/app -w /app [IMAGE] python -m src.backtest --evaluation-start 2010-01-01
```

### 3.2 自动化测试
```bash
docker run --rm -v $(pwd):/app -w /app [IMAGE] pytest tests/unit/engine/v12 -q
```

---
👉 **架构规格、因子公式与设计哲学请移步至: [GEMINI.md](./GEMINI.md)**

---
© 2026 QQQ Entropy 开发执行组.
