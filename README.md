# QQQ 买点信号监控系统 (v6.2)

`qqq-monitor` 是一款高精度的市场监控系统，旨在识别 QQQ ETF 的高概率买入信号。系统采用多层级、白盒化的架构，整合了宏观经济数据、市场情绪、机构资金流以及期权市场结构。

## 🚀 v6.2 新特性：决策透明化 (Decision Transparency)
v6.2 版本引入了 **决策白盒追踪 (Decision White-box Tracing)**，将核心引擎重构为 **决策状态单子 (Decision State Monad, DSM)** 模式。这确保了每一个信号不再仅仅是一个结论，而是一条完整、可审计的证据链。

- **AI 投资解释器 (AI Narrative Interpreter)：** 将复杂的量化数据翻译为通俗易懂的投资逻辑，专为非专业投资者设计。
- **可视化决策树 (Visual Decision Tree)：** 直观展示系统的执行路径和逻辑分叉（例如：宏观约束如何精准压制了战术上的贪婪）。
- **持久化决策追踪：** 每一个决策点现在都经过序列化并存储在数据库中，支持历史审计和性能复盘。

---

## 🏗 核心架构 (分层流水线)

系统作为一个函数式流水线（状态单子）运行，将状态容器顺序传递给五个不同的阶段：

1.  **Tier 0 (宏观气候)：** 监控 ERP 和信用利差，定调“结构性环境”（如：干旱季节、危机模式）。
2.  **Tier 1 (战术天气)：** 聚合 VIX、恐惧贪婪指数和市场广度，识别“体感温度”（如：投降式抛售、恐慌）。
3.  **仓位分配策略 (Allocation Policy)：** 核心决策引擎，负责解决宏观与战术层面的逻辑冲突（如：“宏观要求减速，即使战术信号正在尖叫买入”）。
4.  **Tier 2 (期权与地形)：** 叠加期权墙 (Put/Call Walls) 和成交量控制点 (Volume POC)，确认结构性支撑。
5.  **定案与修正 (Finalization)：** 应用最终否决权和“贪婪”逃生逻辑。

---

## 📊 输出层级

### 1. 专业版报告
高密度 CLI 报告，包含 Z-Score、期权墙位置以及各项背离红利。

### 2. AI 投资解释器
通俗化解释层，回答 **“为什么要看这个指标”** 以及 **“这对你当下的决策意味着什么”**。

### 3. 可视化决策树
内部 `if-else` 分支的树状视图：
```text
🌳 [AI 决策树执行路径]
├── [STRUCTURAL REGIME] ──▶ RICH_TIGHTENING
│   └── 理由: 信用利差 > 300bps
├── [TACTICAL STATE] ──▶ CAPITULATION
│   └── 理由: 恐惧与贪婪指数 < 20
└── [ALLOCATION POLICY] ──▶ SLOW_ACCUMULATE
    └── 理由: Tactical CAPITULATION capped by RICH_TIGHTENING regime
```

---

## 🛠 技术栈
- **语言：** Python 3.13 (类型提示，函数式范式)
- **引擎：** 基于状态单子 (State Monad) 的决策流水线
- **数据：** `yfinance`, FRED API, 网页爬虫
- **存储：** SQLite + JSON-blob 决策追踪
- **质检：** `pytest` (150+ 测试用例), 历史回测系统

---

## 🚦 快速开始

### 1. 环境准备
在根目录创建 `.env` 文件：
```bash
FRED_API_KEY=your_key_here
```

### 2. 运行实时监控
```bash
# 重建沙盒以确保包含最新的架构组件
docker-compose build

# 运行标准报告（含 AI 叙事与决策树）
docker-compose run --rm app python -m src.main --no-save
```

### 3. 历史回测
验证逻辑在过去 25 年以上的市场表现：
```bash
docker-compose run --rm app python -m src.backtest
```

### 4. 执行测试
```bash
docker-compose run --rm test
```

---

## 📖 架构决策记录 (ADR)
详细的逻辑规范请参考：
- `ADR-006`: 决策状态单子与白盒逻辑。
- `ADR-005`: 机构资金流与空头卷入指标。
