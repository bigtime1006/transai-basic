# 🔐 API密钥配置指南

（本文件从根目录迁移，内容保持一致）

## 📁 文件位置

### 主要配置文件
```
backend/.env                    # 实际的环境变量文件（包含真实API密钥）
backend/.env.example           # 配置示例文件（不包含真实密钥）
```

### 安全说明
- `.env` 文件包含真实的API密钥，永远不要提交到Git
- `.env.example` 文件是配置模板，可以安全提交到Git
- 两个文件都应该放在 `backend/` 目录下

## 各引擎API密钥获取方式

### 1. DeepSeek API
- 官网: https://platform.deepseek.com/
- 获取步骤:
  1. 注册/登录DeepSeek平台
  2. 进入API管理页面
  3. 创建新的API密钥
  4. 复制密钥到 `.env` 文件

```bash
# backend/.env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions
```

### 2. 腾讯原子能力API
- 官网: https://cloud.tencent.com/product/tmt
- 获取步骤:
  1. 注册腾讯云账号
  2. 开通机器翻译服务
  3. 在控制台获取SecretId和SecretKey
  4. 配置到 `.env` 文件

```bash
# backend/.env
TENCENT_SECRET_ID=your_tencent_secret_id_here
TENCENT_SECRET_KEY=your_tencent_secret_key_here
TENCENT_REGION=ap-beijing
```

### 3. Kimi API
- 官网: https://kimi.moonshot.cn/
- 获取步骤:
  1. 访问Kimi官网
  2. 注册/登录账号
  3. 进入API管理页面
  4. 生成API密钥

```bash
# backend/.env
KIMI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions
```

### 4. 有道云翻译API
- 官网: https://ai.youdao.com/
- 获取步骤:
  1. 注册有道智云账号
  2. 开通机器翻译服务
  3. 创建应用获取APP_ID和APP_SECRET
  4. 配置到 `.env` 文件

```bash
# backend/.env
YOUDAO_APP_ID=your_app_id_here
YOUDAO_APP_SECRET=your_app_secret_here
```

## 配置步骤

### 步骤1: 创建环境变量文件
```bash
cd backend
cp .env.example .env
```

### 步骤2: 编辑.env文件
```bash
nano .env
# 或者
vim .env
```

### 步骤3: 填入真实API密钥
```bash
DEEPSEEK_API_KEY=your_deepseek_api_key_here
TENCENT_SECRET_ID=your_tencent_secret_id_here
TENCENT_SECRET_KEY=your_tencent_secret_key_here
KIMI_API_KEY=your_kimi_api_key_here
YOUDAO_APP_ID=your_youdao_app_id_here
YOUDAO_APP_SECRET=your_youdao_app_secret_here
```

### 步骤4: 重启服务
```bash
docker-compose restart backend worker
```

## 安全注意事项

### 文件权限
```bash
chmod 600 backend/.env
```

### Git忽略配置
确保 `.gitignore` 包含：
```gitignore
.env
.env.local
.env.*.local
!.env.example
```

### 密钥轮换
- 定期更换API密钥
- 监控API使用情况
- 设置合理的配额限制

### 生产环境
- 使用环境变量或密钥管理服务
- 不要在代码中硬编码密钥
- 可用 Docker/Kubernetes secrets

## 验证配置

### 检查环境变量
```bash
docker-compose exec backend bash
env | grep -E "(DEEPSEEK|TENCENT|KIMI|YOUDAO)"
```

### 测试API连接
```bash
curl -X GET "http://localhost:8000/api/engines/status"
```

### 测试翻译
```bash
curl -X POST "http://localhost:8000/api/translate/text" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello","source_lang":"en","target_lang":"zh","engine":"deepseek"}'
```
