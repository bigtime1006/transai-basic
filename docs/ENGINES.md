### Qwen Plus (qwen-plus)

- Type: Chat/QA style; used for translation via prompt engineering.
- Model: `qwen-plus` (avoid `qwen-plus-latest` for stability).
- Config keys (env/db): api_key, api_url, model, max_workers, batch_size, retry_max, sleep_between_requests, timeout.
- Prompt control: supports `style_preset` and `style_instruction` for both text/document; `enable_thinking` allowed only on text.
- Output: Enforced JSON array with same length as input; parser falls back to lines; empty results fallback to original.
- Token usage: usage.total_tokens may be missing; aggregation planned.

# 多引擎与配置说明

## 已集成引擎
- DeepSeek：支持文本/JSON 双模式；JSON 可批量 + 结构化解析
- Tencent：批量较大，时延稳定
- Kimi：限流严格，含重试与退避
- Youdao：字符/批次限制严格，语言对受限
- Qwen3：兼容模式接入，逐条请求 + 退避；需针对 429 做节流

## Qwen3 配置键（以“系统设置 - 引擎设置”为准）
- api_key：`QWEN3_API_KEY` 或 `DASHSCOPE_API_KEY`
- api_url：`https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- model：`qwen-mt-turbo`（推荐）或 `qwen-mt-plus`
- max_workers：并发线程（文档翻译对 qwen3 路径已逐条）
- batch_size：批处理大小（对 qwen3 路径影响有限）
- timeout：超时（秒）
- retry_max：429/5xx 最大重试次数（建议 4~5）
- sleep_between_requests：单条请求间的轻抖动（秒，建议 0.08~0.20）

> 注意：脚本使用 OpenAI SDK 时 `base_url` 应为根地址：`https://dashscope.aliyuncs.com/compatible-mode/v1`
> 系统后端使用的是完整 `api_url`（带 `/chat/completions`）。

## 初始化与默认
- 启动自动插入缺失引擎配置，默认引擎优先 DeepSeek；否则选择第一个可用引擎

## 管理端操作
- 列表/创建/更新/删除：`/api/admin/engines` 系列
- 启停：`POST /api/admin/engines/{id}/toggle`
- 聚合只读：`GET /api/admin/settings/engines`

## Qwen3 并发与节流建议（当前验证结论）
- 文档翻译：逐条请求 + 轻抖动（0.08~0.20s）来降低 429 触发概率
- ≤60 条文本：`max_workers` 6–8；70–80 条：5；>80 条建议分批
- `retry_max` 4–5，指数退避；必要时增大 `sleep_between_requests`

## 运行期统计
- 日志会输出 Qwen3 汇总：`total` / `success` / `429`
- 文档历史明细会附带：`qwen3_total` / `qwen3_success` / `qwen3_429`（仅 qwen3）

## 环境变量（节选）
- Qwen3：`QWEN3_API_KEY` 或 `DASHSCOPE_API_KEY`、`QWEN3_API_URL`、`QWEN3_MODEL`
- DeepSeek：`DEEPSEEK_API_KEY`、`DEEPSEEK_USE_JSON_FORMAT`、`DEEPSEEK_JSON_BATCH_SIZE`
- Tencent：`TENCENT_SECRET_ID`、`TENCENT_SECRET_KEY`、`TENCENT_REGION`
- Kimi：`KIMI_API_KEY`
- Youdao：`YOUDAO_APP_ID`、`YOUDAO_APP_SECRET`
