# SRD: AI Expert Interpreter Module (v1.1 - Resilience Edition)

## 1. 目标 (Objective)
为 `qqq-monitor` 增加一个高可用的 LLM 解读层。系统优先使用云端模型 (Gemini) 提供高质量解读，在触发 API 配额限制或网络故障时，自动切换到本地模型 (Ollama) 以保证服务连续性。

## 2. 系统架构 (Architecture)
- **模块位置**: `src/output/interpreter.py` (类名重构为 `AIInterpreter`)
- **云端引擎**: `google-genai` (Gemini API)
- **本地引擎**: `openai` (兼容 Ollama 的 OpenAI 协议)
- **调度策略**: **Cloud-First, Local-Fallback** (云端优先，本地容灾)。

## 3. 核心功能要求 (Functional Requirements)

### 3.1 多级配置管理 (Multi-Tier Config)
- **Gemini**: 必须配置 `GEMINI_API_KEY`。可选 `GEMINI_MODEL_NAME` (默认 `gemini-2.0-flash`)。
- **Ollama**: 可选 `OLLAMA_HOST` (默认 `http://host.docker.internal:11434/v1`)，`OLLAMA_MODEL` (建议 `qwen2.5:1.5b` 或 `qwen2.5:3b`)。
- **降级逻辑**: 
    1. 捕获 Gemini 429 (Quota), 5xx (Server Error) 或 ConnectionError。
    2. 自动尝试调用本地 Ollama 接口。
    3. 若两者均不可用，返回原始系统信号。

### 3.2 Prompt 一致性
- 无论云端还是本地，必须使用统一的 `EXPERT_INTERPRETER_PROMPT`。
- 本地 Qwen 模型应具备基本的量化指标理解力。

### 3.3 沙盒隔离兼容性
- Docker 容器内访问宿主机 Ollama 必须使用 `host.docker.internal` 作为 Host。

## 4. 接口定义 (Interface)

```python
class AIInterpreter:
    def __init__(self):
        """初始化云端和本地客户端。"""
    def explain_signal(self, result: SignalResult, market_data: MarketData) -> str:
        """执行调度逻辑，返回最终解读内容。"""
```

## 5. 验收标准 (Acceptance Criteria)
1. **容灾测试**: 模拟 `GEMINI_API_KEY` 无效或触发 429，系统应能自动输出由 Ollama 生成的报告。
2. **零依赖性**: 若无 API Key 且本地无 Ollama，应打印“AI 解释模块已静默”。
3. **输出质量**: 本地 Qwen 1.5B 解读必须符合 Markdown 格式。
4. **性能**: 本地推理时间在 M1/M2/M3 Mac 上应控制在 5s 以内。
