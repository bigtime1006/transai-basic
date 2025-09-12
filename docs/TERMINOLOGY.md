# 术语与分类使用说明

## 功能概览
- 术语库：公共/私有，启用/禁用
- 分类：公共/私有，排序；统计术语数量
- 翻译时可选择多个分类，最长优先匹配 + ASCII 占位符保护

## 系统设置（terminology）
- `terminology_enabled`：启用术语处理（默认 true）
- `terminology_case_sensitive`：大小写敏感（默认 false）
- `terminology_categories_enabled`：启用分类（默认 true）
- `terminology_max_categories_per_translation`：单次最大分类数（默认 10）

## 应用规则（更新）
- 当“分类启用”且翻译时未显式选择分类（未传 `category_ids` 或传 `[]`）时：不应用术语
- 显式选择分类时：仅应用所选分类的术语
- 注：本规则已在 DOCX 路径生效，其他格式将逐步对齐
- 前端：仅在选择非空分类时才随请求传 `category_ids`（JSON）

## 前端入口
- `TerminologyManager.vue`：术语与分类 CRUD
- `CategorySelector.vue`：文本/文档翻译页选择分类
- `TextTranslator.vue` / `DocumentTranslator.vue`：提交时携带 `category_ids`

## 历史回显
- 使用过的分类记录到 `translation_term_sets`，在历史页面展示

## 最佳实践
- 通用术语放公共分类；团队/个人专有术语放私有分类
- 文本多段翻译时控制单条长度，便于引擎保持占位符一致性

---

## 附：分类快速开始与接口要点（合并自术语分类README）

### 快速开始
- 数据库/设置初始化（如需）：
  - `backend/init_terminology_settings.py` 初始化分类相关配置
  - 可用 `backend/test_terminology_categories.py` 验证分类功能

### 主要接口（节选）
- 分类 CRUD：
  - `POST /api/terminology/categories`
  - `GET /api/terminology/categories`
  - `PUT /api/terminology/categories/{category_id}`
  - `DELETE /api/terminology/categories/{category_id}`
- 术语（带分类）：
  - `POST /api/terminology/`（可含 `category_id`）
  - `GET /api/terminology/?category_id=...&is_active=true`
- 分类下术语：
  - `GET /api/terminology/categories/{category_id}/terms`

### 权限与状态
- 公共分类：所有用户可见，仅管理员可编辑
- 私有分类：仅创建者可见和管理
- 分类/术语支持 `is_active` 启用/禁用

### 性能与缓存建议
- 分类元数据缓存：~1小时
- 分类术语缓存：~5分钟；分类组合缓存：~3分钟（服务层已有缓存）
- 表建议索引：`term_categories(owner_type, owner_id, is_active, sort_order)`、`terminologies(category_id, is_active)`

### 故障排除
- 翻译时分类不生效：检查分类是否启用、分类下是否有术语、语言对是否匹配
- 分类删除失败：确认无术语关联

更多设计细节与阶段计划见 `docs/TERMINOLOGY_ENABLE_PLAN.md`。
