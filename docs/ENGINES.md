# 引擎配置说明

本文档说明了系统中支持的翻译引擎及其配置方式。

## 配置优先级

所有引擎的配置都遵循统一的优先级顺序：

1.  **数据库配置**：在“系统管理” -> “引擎设置”中为特定引擎保存的 JSON 配置。这是最高优先级，会覆盖下面的所有默认值。
2.  **环境变量**：为容器或主机设置的环境变量。
3.  **代码内置默认值**：代码中硬编码的备用 URL 或参数。

## 已集成引擎

### 1. DeepSeek

-   **引擎名称**: `deepseek`
-   **特点**: 默认引擎，支持文本/JSON 双模式，JSON 模式下支持更大的批处理和结构化解析。
-   **数据库/环境变量配置键**:
    -   `api_key`: API 密钥 (必要)
    -   `api_url`: API 地址 (默认为 `https://api.deepseek.com/v1/chat/completions`)
    -   `model`: 模型名称 (默认为 `deepseek-chat`)
    -   `max_workers`: 最大并发线程数
    -   `batch_size`: 批处理大小
    -   `timeout`: 请求超时 (秒)
    -   `use_json_format`: 是否启用 JSON 模式 (布尔值, `true`/`false`)
    -   `json_batch_size`: JSON 模式下的批处理大小

### 2. Qwen Plus (qwen-plus)

-   **引擎名称**: `qwen_plus` (或 `qwen-plus`)
-   **特点**: 聊天式翻译引擎，通过提示工程实现翻译。
-   **数据库/环境变量配置键**:
    -   `api_key`: API 密钥 (必要, 可共用 `DASHSCOPE_API_KEY`)
    -   `api_url`: API 地址 (默认为 `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`)
    -   `model`: 模型名称 (默认为 `qwen-plus`)
    -   `max_workers`, `batch_size`, `timeout`
    -   `retry_max`: 失败重试次数
    -   `sleep_between_requests`: 请求间的节流等待时间 (秒)

### 3. Qwen3 (qwen3)

-   **引擎名称**: `qwen3` (或 `qwen`, `qwen-mt`)
-   **特点**: 阿里通义翻译模型，兼容 OpenAI 模式接入。
-   **数据库/环境变量配置键**:
    -   `api_key`: API 密钥 (必要, 可共用 `DASHSCOPE_API_KEY`)
    -   `api_url`: API 地址
    -   `model`: 模型名称 (推荐 `qwen-mt-turbo`)
    -   `max_workers`, `batch_size`, `timeout`, `retry_max`, `sleep_between_requests`

### 4. Kimi

-   **引擎名称**: `kimi`
-   **特点**: 月之暗面公司的大模型，限流较严格，内置了重试与退避机制。
-   **数据库/环境变量配置键**:
    -   `api_key`: API 密钥 (必要)
    -   `api_url`: API 地址 (默认为 `https://api.moonshot.cn/v1/chat/completions`)
    -   `model`: 模型名称 (默认为 `moonshot-v1-8k`)
    -   `max_workers`, `batch_size`, `timeout`

### 5. Tencent Translator

-   **引擎名称**: `tencent`
-   **特点**: 腾讯翻译服务，批处理量大，延迟稳定。
-   **环境变量配置键** (暂不支持数据库配置):
    -   `TENCENT_SECRET_ID`: Secret ID (必要)
    -   `TENCENT_SECRET_KEY`: Secret Key (必要)
    -   `TENCENT_REGION`: 区域 (默认为 `ap-beijing`)

### 6. Youdao

-   **引擎名称**: `youdao`
-   **特点**: 有道智云翻译，对字符数和批次大小限制严格。
-   **环境变量配置键** (暂不支持数据库配置):
    -   `YOUDAO_APP_ID`: 应用 ID (必要)
    -   `YOUDAO_APP_SECRET`: 应用密钥 (必要)

---

## 如何添加新引擎 (样例)

系统已内置了添加新引擎的逻辑框架。以下是如何配置 ChatGPT 和 Gemini 的示例。

### ChatGPT (openai)

1.  **引擎名称**: `chatgpt` (或 `openai`)
2.  **添加配置**:
    -   **方式一 (推荐)**: 在“引擎设置”中，创建一个新引擎，引擎名称填 `chatgpt`。在 API 配置的 JSON 中输入以下内容：
        ```json
        {
          "api_key": "sk-...",
          "api_url": "https://api.openai.com/v1/chat/completions",
          "model": "gpt-4o"
        }
        ```
    -   **方式二 (环境变量)**: 设置 `CHATGPT_API_KEY`, `CHATGPT_API_URL`, `CHATGPT_MODEL` 等环境变量。
3.  **实现代码**: 需要在 `backend/app/services/utils_translator.py` 中仿照 `DeepSeekTranslator` 创建一个 `ChatGPTTranslator` 类并注册到工厂中。

### Gemini (google)

1.  **引擎名称**: `gemini` (或 `google`)
2.  **添加配置**:
    -   **方式一 (推荐)**: 在“引擎设置”中创建新引擎 `gemini`，并配置 JSON：
        ```json
        {
          "api_key": "...",
          "api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
          "model": "gemini-pro"
        }
        ```
    -   **方式二 (环境变量)**: 设置 `GEMINI_API_KEY`, `GEMINI_API_URL`, `GEMINI_MODEL` 等环境变量。
3.  **实现代码**: 与 ChatGPT 类似，需要创建 `GeminiTranslator` 类并注册。
