# API状态检查配置说明

（本文件从根目录迁移，内容保持一致）

## 功能开关
默认关闭，可按需开启。

## 配置方式

### 1. 前端环境变量
```env
VITE_ENABLE_API_STATUS_CHECK=false
VITE_API_BASE_URL=http://localhost:8000
```

### 2. 用户偏好
界面开关：开启后每5分钟自动检查，也可手动检查。

## 界面显示
- 启用：显示状态、开关、检查按钮与健康状态
- 禁用：完全隐藏

## 性能优化
- 默认关闭减少请求与资源消耗
- 调试或生产监控时可开启

## 状态管理
- 智能缓存（30秒去抖，5分钟自动刷新）
- 共享状态、实时同步

## 使用方法
```bash
echo "VITE_ENABLE_API_STATUS_CHECK=true" > frontend/.env
docker-compose restart frontend
```

## 注意事项
- 环境变量优先于偏好
- 偏好保存在 localStorage

## 推荐配置
- 开发：true
- 生产：false
- 测试：true
