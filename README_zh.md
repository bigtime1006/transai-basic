# TransAI - 多格式文档翻译工具

---

一个基于AI的多格式文档翻译工具，支持 DOCX、PPTX、XLSX、TXT、MD 等格式（PDF/OCR 计划中）。项目采用前后端分离 + 任务队列架构，提供高效、可扩展的翻译服务。

> 文档入口：请优先查看 `docs/` 目录的最新文档（如 `docs/README.md`、`docs/SYSTEM_DOCUMENTATION.md`）。

## 🚀 功能特性
### 最近更新（2025-08）

- 批量翻译页面重构：移除冗余卡片，仅保留总体进度与操作按钮；状态/下载在历史列表逐行展示。
- 新增批量管理接口：`POST /api/batch/cancel/{batch_id}`、`POST /api/batch/prune/{batch_id}`。
- 修复 PPTX 执行错误（参数冲突），提高稳定性。
- XLSX 增加“语言后验校验+二次强制翻译”，显著降低混杂语境导致的目标语言漂移。
- 前端控制台降噪：去除大量调试日志。


- **多格式支持**: DOCX、PPTX、XLSX、TXT、MD（PDF 与 OCR 即将支持）
- **多引擎支持**: DeepSeek、Tencent、Kimi、Youdao（可扩展）
- **智能翻译**: 支持 JSON 批量翻译，提高翻译效率
- **用户管理**: 用户注册、登录、权限控制，支持管理员和普通用户角色
- **历史记录**: 翻译历史保存/查询/删除，支持按用户权限查看；支持文本/文档分别设置每用户历史上限；支持每日自动清理过期文件/内容
- **实时进度**: 翻译任务实时进度显示，支持任务状态监控
- **文件下载**: 翻译完成后文件下载，支持多种文件格式
- **术语管理**: 专业术语库管理，提高翻译一致性
- **多语言支持**: 支持中文、英文、日文、韩文等多种语言

## 👥 默认账号

### Admin账号
- **用户名**: `admin`
- **密码**: `admin123`
- **角色**: 管理员
- **权限**: 可以查看所有用户的翻译历史记录，管理翻译引擎设置，配置系统参数

### 测试账号
- **用户名**: `testuser`
- **密码**: `testpass`
- **角色**: 普通用户
- **权限**: 只能查看自己的翻译历史记录

## 🛠️ 快速开始

### 1. 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少2GB可用内存

### 2. 启动服务

```bash
# 克隆项目
git clone <repository-url>
cd transai

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f backend
```

### 3. 访问应用（开发默认）

- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **任务监控**: http://localhost:8000/monitor

### 4. 登录系统（默认账号）

使用默认的admin账号登录：
- 用户名: `admin`
- 密码: `admin123`

## 🏗️ 技术架构

### 前端技术栈
- **框架**: Vue 3 + Composition API
- **UI组件**: Element Plus
- **状态管理**: Vue 3 Reactive
- **HTTP客户端**: Axios
- **构建工具**: Vite

### 后端技术栈
- **框架**: FastAPI + Python 3.9+
- **ORM**: SQLAlchemy 2.0
- **数据库**: PostgreSQL (生产) / SQLite (开发)
- **任务队列**: Celery + Redis
- **认证**: JWT + bcrypt
- **API文档**: OpenAPI/Swagger

### AI翻译引擎
- DeepSeek（可选 JSON 模式；支持对象/数组解析容错）
- Tencent（配置凭据后可启用）
- Kimi（配置凭据后可启用）
- Youdao（配置凭据后可启用）

### 部署架构
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx (生产环境)
- **数据库**: PostgreSQL + Redis
- **文件存储**: 本地文件系统
- **监控**: 内置健康检查

## ⚙️ 配置说明

### 环境变量配置（节选）

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/dbname
POSTGRES_DB=transai
POSTGRES_USER=transai_user
POSTGRES_PASSWORD=your_password

## DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_USE_JSON_FORMAT=true  # 可在系统设置中动态切换
DEEPSEEK_JSON_BATCH_SIZE=50

## Tencent
TENCENT_SECRET_ID=...
TENCENT_SECRET_KEY=...
TENCENT_REGION=ap-beijing

## Kimi
KIMI_API_KEY=...
KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions

## Youdao
YOUDAO_APP_ID=...
YOUDAO_APP_SECRET=...

# 安全配置
SECRET_KEY=your_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 服务配置
BACKEND_PORT=8000
FRONTEND_PORT=5173
WORKER_CONCURRENCY=2
```

### DeepSeek JSON 格式配置（为何默认）

项目支持 DeepSeek 文本/JSON 两种模式（可在系统设置动态切换）。JSON 模式优势：
- **批量处理**: 支持50个文本片段同时翻译
- **结构化输出**: JSON格式确保翻译结果的一致性
- **错误处理**: 更好的错误识别和处理机制
- **性能优化**: 减少API调用次数，提高翻译效率

## 🔧 开发说明

### 数据库初始化

应用启动时会自动：
1. 创建数据库表结构
2. 创建默认的admin用户账号
3. 初始化必要的设置和配置（包含历史上限、删除策略、保留天数、术语开关等）

### 用户权限系统

- **admin**: 管理员，可以查看所有记录，管理设置，配置引擎参数
- **user**: 普通用户，只能查看自己的记录，使用翻译服务

### 翻译任务流程

1. **文件上传**: 支持拖拽和点击上传
2. **格式检测**: 自动识别文档格式
3. **内容提取**: 提取文档中的可翻译文本
4. **批量翻译**: 使用AI引擎进行批量翻译
5. **结果生成**: 生成翻译后的文档
6. **文件下载**: 提供翻译结果下载

### 历史记录与清理（新）
- 文本删除：清空 `source_text`/`translated_text` 内容，保留语言、引擎、时间与统计（tokens/字符/字节/耗时）
- 文档删除：删除上传源文件（uploads）与生成文件（downloads），清空 `file_name`/`result_path`，保留记录与统计
- 每用户历史上限：可分别配置文本/文档上限（到达上限返回 409，需先删除再继续）
- 定时清理：每日清理超期文件/内容（保留天数可在系统设置配置）
- 小历史删除行为可配置为“等同后台删除”

### 翻译策略说明
项目支持多种翻译策略，可根据文档类型自动选择最适合的处理方案：
- `ooxml_direct`: 直接解析Office文档格式，保持原始格式
- `text_direct`: 适用于纯文本文档的高效处理
- `aspose`: 基于Aspose云服务的文档处理（可选）

## 🚀 部署说明

### 开发环境

```bash
# 使用开发配置
docker-compose -f docker-compose.dev.yml up -d

# 启用调试模式
docker-compose -f docker-compose.dev.yml -f docker-compose.override.yml up -d
```

### 生产环境

```bash
# 使用生产配置
docker-compose -f docker-compose.prod.yml up -d

# 配置环境变量
cp .env.example .env
# 编辑.env文件，配置生产环境参数
```

### 生产环境要求

1. **数据库**: 使用PostgreSQL数据库
2. **缓存**: 配置Redis作为Celery broker和结果后端
3. **安全**: 设置HTTPS，配置反向代理
4. **监控**: 配置日志收集和监控系统
5. **备份**: 定期备份数据库和文件
6. **任务调度**: Celery beat 用于清理任务（已内置每日调度）

## 📁 项目结构（关键路径）

```
transai/
├── frontend/                 # Vue 3前端应用
│   ├── src/
│   │   ├── components/      # Vue组件
│   │   ├── utils/           # 工具函数
│   │   └── App.vue          # 主应用组件
│   └── package.json
├── backend/                  # FastAPI后端应用
│   ├── app/
│   │   ├── services/        # 业务逻辑服务
│   │   ├── models/          # 数据模型
│   │   ├── schemas/         # 数据验证
│   │   └── main.py          # 主应用入口
│   └── requirements.txt
├── docker-compose.yml        # Docker编排配置
├── temp_responses/           # 临时响应文件（调试用）
├── uploads/                  # 文件上传目录
├── downloads/                # 文件下载目录
└── README.md                 # 项目说明文档
```

## 🔍 故障排除

### 常见问题

1. **服务启动失败**: 检查Docker和Docker Compose版本
2. **数据库连接错误**: 确认PostgreSQL服务状态和连接参数
3. **翻译失败**: 检查AI引擎API密钥配置
4. **文件上传失败**: 确认文件格式支持和大小限制

### 日志查看

```bash
# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 查看工作进程日志
docker-compose logs -f worker
```

### 健康检查

```bash
# 检查API状态
curl http://localhost:8000/health

# 检查数据库连接
curl http://localhost:8000/api/health/db
```

## 📚 文档说明

详细的系统架构和使用说明，请参考 `docs/` 目录中的相关文档：

- `SYSTEM_DOCUMENTATION.md` - 系统架构和核心模块说明
- `API_KEYS_SETUP.md` - 各翻译引擎的API密钥配置指南
- `DOCKER_USAGE.md` - Docker部署和管理说明
- `QUICK_REFERENCE.md` - 常用操作和故障排除指南

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

## 授权协议
本项目采用双许可证模式：
- **非商业开源使用**：遵循 [GNU General Public License v3.0](LICENSE) 协议。允许免费获取、使用、修改和分发代码，但衍生作品必须以相同许可证开源，且不得用于商业目的。
- **商业使用**：如需将本项目用于商业场景（包括但不限于盈利产品、商业服务、企业内部付费系统等），请联系 [你的邮箱/联系方式] 获取单独的商业授权，商业授权不适用 GPLv3 的开源要求。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**TransAI** - 让文档翻译更智能、更高效！ 🚀 
