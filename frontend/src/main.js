import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import i18n from './i18n'

// 1. 定义路由
// 由于App.vue是自包含的，一个简单的通配符路由就足够了
const routes = [
  { path: '/:pathMatch(.*)*', name: 'App', component: App },
]

// 2. 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)

app.use(ElementPlus)
app.use(i18n)
app.use(router) // 3. 使用路由

app.mount('#app')