
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // 允许外部访问
    watch: {
      usePolling: true, // 在Docker中使用轮询监听文件变化
      interval: 1000,   // 轮询间隔
    },
    proxy: {
      '/api': {
        target: 'http://host.docker.internal:8000', // Docker容器内访问宿主机
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://host.docker.internal:8000', // Docker容器内访问宿主机
        changeOrigin: true,
      }
    },
  },
})
