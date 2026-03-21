# SRD: AI Expert Interpreter Module (v1.2 - Local Only)

## 1. 目标 (Objective)
为 `qqq-monitor` 增加一个基于本地 LLM 的解读层。系统强制使用本地 **Ollama** 引擎进行推理，以确保 100% 的隐私性、数据安全及在无外网环境下的可用性，彻底避免云端 API 的配额限制和延迟不确定性。

## 2. 系统架构 (Architecture)
- **模块位置**: `src/output/interpreter.py`
- **核心引擎**: 本地 Ollama (通过 OpenAI 兼容协议或直接 REST API)
- **通信方式**: `httpx` 直连宿主机 Ollama 服务。

## 3. 核心功能要求 (Functional Requirements)

### 3.1 本地配置管理 (Local Config)
- **Ollama**: 可选 `OLLAMA_HOST` (默认 `http://host.docker.internal:11434`)。
- **Model**: 可选 `OLLAMA_MODEL` (默认 `qwen3.5:0.8b`，建议根据硬件性能选择 `qwen3.5:9b` 以获得更佳效果)。
- **超时控制**: 默认 90s 超时，以适配大模型在非 GPU 环境下的推理。

### 3.2 Prompt 工程设计
- **角色定位**: Senior Trading Mentor (资深交易导师)。
- **输出格式**: 简体中文 Markdown 报告。
- **清理逻辑**: 自动剥离模型输出中的 `<think>` 思考标签。

### 3.3 沙盒隔离兼容性
- Docker 容器内访问宿主机 Ollama 强制使用 `host.docker.internal`。

## 4. 接口定义 (Interface)

```python
class AIInterpreter:
    def __init__(self):
        """初始化本地配置。"""
    def explain_signal(self, result: SignalResult, market_data: MarketData) -> str:
        """调用本地 Ollama API，返回中文解读内容。"""
```

## 5. 验收标准 (Acceptance Criteria)
1. **纯本地化**: 即使在断网状态下（且已 Pull 模型），系统仍能输出解读报告。
2. **零云端依赖**: 移除所有 Gemini 相关的代码、库和环境变量。
3. **输出质量**: 解读报告必须准确识别并对比 `SignalResult` 中的量化指标。
4. **性能**: 本地推理时间在 M1/M2/M3 Mac 上应控制在合理范围内。
