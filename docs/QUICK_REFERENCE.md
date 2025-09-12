## Frontend Quick Ops

- Text translator: select engine (defaults to backend default), choose style preset, optionally add custom instruction, toggle enable_thinking for qwen_plus/deepseek.
- Document translator: upload file (DOCX/PPTX/XLSX/TXT/MD), select engine/style; custom instruction supported.
- History: text/document pages show engine_params via toggle/popover for inspection.

## Backend Quick Ops

- Set unique default engine via Admin -> Engines; only one is default now.
- Qwen Plus env (example):
  - DASHSCOPE_API_KEY=sk-... (or configured via db)
  - API URL: OpenAI-compatible endpoint for Qwen Plus

### Common APIs (incl. Batch)
- Auth token: `POST /api/auth/token`
- Text translate: `POST /api/translate/text`
- Document translate: `POST /api/translate/document`
- History (combined): `GET /api/history`
- Text history: `GET /api/history/text`
- Document history: `GET /api/history/document`
- Batch-only history: `GET /api/history/document?batch_only=true` or `GET /api/history/batch`

### Batch APIs
- Create batch: `POST /api/batch/start`
- Submit batch: `POST /api/batch/submit` (fields: files[], source_lang, target_lang, style_preset, style_instruction, category_ids JSON, batch_id)
- Get batch status: `GET /api/batch/{batch_id}`
- Note: Batch uses qwen-plus Batch API; async and cost-effective; results may be delayed.

## Docker Dev

- docker compose -f docker-compose.dev.yml up -d --build
- Frontend at 5173, Backend at 8000; API calls are relative through Vite proxy.

# TransAI 快速参考手册

（本文件从根目录迁移，内容保持一致，链接已指向 docs 内文件）

## 用户账号
- 默认管理员：`admin` / `admin123`

## 快速启动
```bash
docker-compose up -d
```

## 常用配置与端口
- 前端 5173，后端 8000，DB 5432，Redis 6379

## 常用命令
- 重启：`docker-compose restart backend`
- 进入容器：`docker-compose exec backend bash`

## 日志与健康
- `docker-compose logs -f backend`
- `curl http://localhost:8000/api/engines/status`
- `curl http://localhost:8000/api/health/deepseek`

## 故障排除与调试
- 查看 API_KEY / ping / 查看日志尾部

## 参考文档
- [完整系统文档](./SYSTEM_DOCUMENTATION.md)
- [多引擎与配置说明](./ENGINES.md)
- [Docker使用说明](./DOCKER_USAGE.md)
- [API密钥设置](./API_KEYS_SETUP.md)
