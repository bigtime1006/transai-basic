# Docker 使用说明

（本文件从根目录迁移，内容保持一致）

## 双模式配置
- `docker-compose.yml`（开发）
- `docker-compose.dev.yml`（开发）
- `docker-compose.prod.yml`（生产）

## 开发模式
```bash
docker-compose -f docker-compose.dev.yml up -d
# 或
docker-compose up -d
```

## 生产模式
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 模式切换
参考原说明中的步骤（down、build --no-cache、up -d）。

## 常见问题
- 代码更新不生效：使用开发模式或重建镜像
- 环境变量缺失导致启动失败：补全 .env
- API 地址差异：开发 `localhost`，生产 `backend`

## 环境变量示例
```env
DEEPSEEK_API_KEY=...
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=transaidb
MAX_TEXT_TRANSLATION_BYTES=5000
```
