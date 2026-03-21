# SRD: AI Expert Interpreter Module (Chinese)

## 1. 目标 (Objective)
为 `qqq-monitor` 增加一个基于 LLM 的输出层，将复杂的量化指标（Tier 0/1/2）转化为非专业投资者可理解的“中文专家解读”，旨在提升工具的教育价值和决策可解释性。

## 2. 系统架构 (Architecture)
- **模块位置**: `src/output/interpreter.py`
- **集成点**: `src/main.py` (新增 `--explain` 参数)
- **依赖库**: `google-generativeai`, `python-dotenv`
- **身份验证**: 强制使用 `GEMINI_API_KEY` (环境变量)。

## 3. 核心功能要求 (Functional Requirements)

### 3.1 AI 配置管理
- 支持通过 `.env` 配置 `GEMINI_MODEL_NAME` (默认为 `models/gemini-3.1-pro-preview`)。
- 必须具备异常处理机制：若 API Key 失效或网络中断，系统应打印友好错误并优雅退出该子模块，不影响核心监测功能。

### 3.2 Prompt 工程设计
- **角色定位**: Senior Trading Mentor (资深交易导师)。
- **逻辑注入**: 必须在 Prompt 中包含对 `GEMINI.md` 定义的三层过滤逻辑 (Tiered Logic) 的描述。
- **语言限制**: 强制输出为简体中文。
- **术语转换**: 自动将 `Gamma Flip`, `Put Wall`, `Credit Spreads` 等术语用生活化比喻进行二次解释。

### 3.3 数据流 (Data Flow)
1. `main.py` 收集 `Engine` 生成的 `SignalResult` 对象和 `MarketData` 对象。
2. 数据摘要发送至 `GeminiInterpreter.explain_signal()`。
3. 调用 Gemini API 获取生成的 Markdown 格式报告。
4. 在 CLI 中以分隔线包裹的形式进行打印。

## 4. 接口定义 (Interface)

```python
class GeminiInterpreter:
    def __init__(self):
        """初始化 API 配置并加载模型。"""
    def explain_signal(self, result: SignalResult, market_data: MarketData) -> str:
        """生成并返回中文解读报告。"""
```

## 5. 验收标准 (Acceptance Criteria)
1. **Docker 兼容性**: 必须能通过 `docker-compose run --rm app python -m src.main --explain` 正常运行。
2. **零耦合**: 删除 `GEMINI_API_KEY` 后，系统应提示“AI 模块不可用”并正常显示原始信号。
3. **输出质量**: 解读报告必须准确识别出“哪一层 Tier 触发了硬性阻断”。
4. **单元测试**: 模块代码应支持传入 Mock 后的 Gemini 对象以进行逻辑验证。
