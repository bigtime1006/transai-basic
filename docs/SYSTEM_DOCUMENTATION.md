# TransAI 系统文档（当前版本，对齐实现）

本文件与当前系统实现保持一致，优先于根目录旧版。

## 架构与技术栈
- 后端: FastAPI、SQLAlchemy、JWT(bcrypt)、Celery+Redis、PostgreSQL
- 前端: Vue3 + Element Plus
- 容器化: Docker Compose

## 认证与用户
- 登录: `POST /api/auth/token`
- 注册: `POST /api/users/register`（系统开关 `allow_registration`）
- 当前用户: `GET /api/users/me`
- 用户改密: `POST /api/users/me/change-password`
- 管理员重置密码: `POST /api/users/admin/users/{user_id}/reset-password`
- 密码策略（系统设置 security）：`min_length` / `require_uppercase` / `require_lowercase` / `require_digit` / `require_special`

## 历史记录
- 文档历史: `GET /api/history/document` (支持分页)
  - **参数**: `page: int = 1`, `limit: int = 10`, `include_all: bool`, `batch_only: bool`, `normal_only: bool`
  - **响应**: `{ "items": [...], "total": 0 }`
- 文本历史: `GET /api/history/text?include_all=true`
- 删除记录: `DELETE /api/history/{item_id}?type=text|document`
  - 文本：清空内容保留统计
  - 文档：删除源/目标文件，置空路径，记录与统计保留
- 新增字段（文档历史）：
  - `total_texts`、`translated_texts`（文本统计）
  - `qwen3_total`、`qwen3_success`、`qwen3_429`（仅 qwen3）

## 术语与分类
- 开关：`terminology_enabled`、`terminology_case_sensitive`、`terminology_categories_enabled`、`terminology_max_categories_per_translation`
- 规则更新（文档翻译）：当“分类启用”且未显式选择分类（未传或空数组）时，不应用术语；显式选择分类时，仅应用所选分类（当前已在 DOCX 路径生效，其余格式将逐步对齐）
- 前端：翻译页选择分类时，仅在选择非空时随请求携带 `category_ids`（JSON）

## 翻译接口
- 文本: `POST /api/translate/text`
- 文档: `POST /api/translate/document`（后台处理）
- 结果: `GET /api/translate/result/{task_id}`
- 引擎/策略公开：`GET /api/engines/available`、`GET /api/strategies/available`

## 引擎与并发（Qwen3 重点）
- Qwen3：逐条请求 + 轻抖动；`retry_max` 支持配置；系统日志输出批次汇总：total/success/429
- 引擎配置以 DB 的 `translation_engines.api_config` 为准（通过“系统设置-引擎设置”界面保存后立即生效）
- Qwen3 推荐参数：`model=qwen-mt-turbo`、`retry_max=4~5`、`sleep_between_requests=0.08~0.20`、`timeout=60`

## 管理后台与前端
- 管理端“历史记录”页新增列：文本统计（总/已译）与 Qwen429（仅 qwen3）
- 引擎设置：qwen3 的 `retry_max`、`sleep_between_requests` 等参数可视化调整

## 部署与重启建议
- 开发：代码改动需重启 `backend` 与 `worker`；文档入口不变
- 配置更新（通过界面保存）：无需重启，新请求即生效
- 生产：代码改动需重建镜像并重启服务
