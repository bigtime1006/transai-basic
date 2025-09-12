<template>
  <div id="app">
    <!-- 头部 -->
    <div class="header">
      <div class="header-content">
        <div class="logo">
          <h1>TransAI</h1>
        </div>
        
        <div class="user-info">
          <el-select v-model="$i18n.locale" size="small" style="width:110px;margin-right:12px;">
            <el-option label="中文" value="zh"/>
            <el-option label="日本語" value="ja"/>
            <el-option label="한국어" value="ko"/>
            <el-option label="English" value="en"/>
          </el-select>
          <el-dropdown v-if="isLoggedIn" @command="onUserMenu">
            <span class="el-dropdown-link username">
              {{ username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">{{ $t('common.profile') }}</el-dropdown-item>
                <el-dropdown-item divided command="logout">{{ $t('common.logout') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- 主要内容 -->
    <div class="main-content">
      <div class="main-content-inner">
        <!-- 登录组件 -->
        <Login v-if="!isLoggedIn" @login-success="handleLoginSuccess" />
        
        <!-- 已登录用户的功能区域 -->
        <div v-else class="functional-area">
          <el-tabs v-model="activeTab" @tab-click="handleTabClick">
            <!-- 文本翻译 -->
            <el-tab-pane :label="$t('menu.textTranslation')" name="text-translation">
              <TextTranslator />
            </el-tab-pane>
            
            <!-- 文档翻译 -->
            <el-tab-pane :label="$t('menu.documentTranslation')" name="document-translation">
              <DocumentTranslator />
            </el-tab-pane>
            
            <!-- 批量翻译 -->
            <el-tab-pane :label="$t('menu.batchTranslation')" name="batch-translation">
              <BatchTranslator />
            </el-tab-pane>
            
            <!-- 术语管理 -->
            <el-tab-pane :label="$t('menu.terminology')" name="terminology">
              <TerminologyManager :current-role="userRole" />
            </el-tab-pane>
            
            <!-- 管理仪表板 -->
            <el-tab-pane v-if="isAdmin" :label="$t('menu.adminDashboard')" name="admin-dashboard">
              <AdminDashboard />
            </el-tab-pane>
            
            <!-- 用户管理 -->
            <el-tab-pane v-if="isAdmin" :label="$t('menu.userManagement')" name="user-management">
              <UserManagement />
            </el-tab-pane>
            
            <!-- 管理员翻译历史 -->
            <el-tab-pane v-if="isAdmin" :label="$t('menu.history')" name="admin-history">
              <AdminHistory />
            </el-tab-pane>

            
            
            <!-- 系统设置 -->
            <el-tab-pane v-if="isAdmin" :label="$t('menu.systemSettings')" name="system-settings">
              <SystemSettings />
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>
    <el-dialog v-model="showProfile" title="个人信息" width="520px">
      <div v-if="profile">
        <el-descriptions :column="1" border style="margin-bottom:12px;">
          <el-descriptions-item :label="$t('profile.username')">{{ profile.username }}</el-descriptions-item>
          <el-descriptions-item :label="$t('profile.role')">{{ profile.role }}</el-descriptions-item>
          <el-descriptions-item :label="$t('profile.email')">{{ profile.email || $t('profile.notSet') }}</el-descriptions-item>
          <el-descriptions-item :label="$t('profile.lastLogin')">{{ profile.last_login ? new Date(profile.last_login).toLocaleString(): $t('profile.never') }}</el-descriptions-item>
        </el-descriptions>
        <el-divider>{{ $t('profile.changePassword') }}</el-divider>
        <el-form :model="pwdForm" label-width="100px">
          <el-form-item :label="$t('profile.oldPassword')">
            <el-input v-model="pwdForm.old_password" type="password" />
          </el-form-item>
          <el-form-item :label="$t('profile.newPassword')">
            <el-input v-model="pwdForm.new_password" type="password" placeholder="至少8位，含大小写与数字" />
          </el-form-item>
          <el-form-item :label="$t('profile.confirmNewPassword')">
            <el-input v-model="pwdForm.confirm_password" type="password" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showProfile=false">{{ $t('common.close') }}</el-button>
          <el-button type="primary" :loading="pwdLoading" @click="submitChangePwd">{{ $t('common.save') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import Login from './components/Login.vue'
import TextTranslator from './components/TextTranslator.vue'
import DocumentTranslator from './components/DocumentTranslator.vue'
import TerminologyManager from './components/TerminologyManager.vue'
import AdminDashboard from './components/AdminDashboard.vue'
import UserManagement from './components/UserManagement.vue'
import SystemSettings from './components/SystemSettings.vue'
import AdminHistory from './components/AdminHistory.vue'
import BatchTranslator from './components/BatchTranslator.vue'

export default {
  name: 'App',
  components: {
    Login,
    TextTranslator,
    DocumentTranslator,
    TerminologyManager,
    AdminDashboard,
    UserManagement,
    SystemSettings,
    AdminHistory,
    BatchTranslator
  },
  setup() {
    const isLoggedIn = ref(false)
    const username = ref('')
    const userRole = ref('')
    const activeTab = ref('text-translation')
    const showProfile = ref(false)
    const profile = ref(null)
    const pwdForm = ref({ old_password:'', new_password:'', confirm_password:'' })
    const pwdLoading = ref(false)

    // 检查登录状态
    const checkLoginStatus = async () => {
      const token = localStorage.getItem('token')
      if (token) {
        try {
          // 验证token并获取用户信息
          const response = await fetch('/api/users/me', {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          
          if (response.ok) {
            const userData = await response.json()
            isLoggedIn.value = true
            username.value = userData.username
            userRole.value = userData.role || 'user'
          } else {
            // token无效，清除本地存储
            localStorage.removeItem('token')
            isLoggedIn.value = false
            username.value = ''
            userRole.value = ''
          }
        } catch (error) {
          console.error('Token validation failed:', error)
          localStorage.removeItem('token')
          isLoggedIn.value = false
          username.value = ''
          userRole.value = ''
        }
      } else {
        isLoggedIn.value = false
        username.value = ''
        userRole.value = ''
      }
    }

    // 计算属性：是否为管理员
    const isAdmin = computed(() => {
      return userRole.value === 'admin'
    })

    // 处理登录成功
    const handleLoginSuccess = (userData) => {
      isLoggedIn.value = true
      username.value = userData.username
      userRole.value = userData.role
      // 将用户信息放入localStorage，供子组件（如TerminologyManager）判定权限
      try { localStorage.setItem('user', JSON.stringify(userData)) } catch {}
      activeTab.value = 'text-translation'
    }

    // 处理登出
    const logout = () => {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      isLoggedIn.value = false
      username.value = ''
      userRole.value = ''
      activeTab.value = 'text-translation'
    }

    const openProfile = async () => {
      try{
        const token = localStorage.getItem('token')
        const resp = await fetch('/api/users/me', { headers:{ 'Authorization': `Bearer ${token}` } })
        if(resp.ok){ profile.value = await resp.json(); showProfile.value = true }
      }catch(e){ /* ignore */ }
    }
    const onUserMenu = (cmd) => {
      if(cmd==='logout') return logout()
      if(cmd==='profile') return openProfile()
    }
    const submitChangePwd = async () => {
      try{
        pwdLoading.value = true
        if(pwdForm.value.new_password !== pwdForm.value.confirm_password){ throw new Error('两次输入的新密码不一致') }
        const token = localStorage.getItem('token')
        const resp = await fetch('/api/users/me/change-password', {
          method:'POST',
          headers:{ 'Content-Type':'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ old_password: pwdForm.value.old_password, new_password: pwdForm.value.new_password })
        })
        if(!resp.ok){ const e = await resp.json(); throw new Error(e.detail||'修改失败') }
        showProfile.value = false
      }catch(e){ console.error(e) }
      finally{ pwdLoading.value = false }
    }

    // 处理标签选择
    const handleTabSelect = (key) => {
      activeTab.value = key
    }

    // 处理标签点击
    const handleTabClick = (tab) => {
      activeTab.value = tab.name
    }

    onMounted(() => {
      checkLoginStatus()
    })

    return {
      isLoggedIn,
      username,
      userRole,
      activeTab,
      isAdmin,
      handleLoginSuccess,
      logout,
      handleTabSelect,
      handleTabClick
      ,showProfile, profile, pwdForm, pwdLoading, onUserMenu, submitChangePwd
    }
  }
}
</script>

<style>
/* 全局样式 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f5f7fa;
  color: #333;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* 头部样式 */
.header {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
}

.logo h1 {
  color: #409EFF;
  font-size: 24px;
  font-weight: bold;
  margin: 0;
}

.nav-menu {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-menu .el-menu {
  border: none;
}

.nav-menu .el-menu-item {
  font-size: 16px;
  padding: 0 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.username {
  color: #666;
  font-size: 14px;
  cursor: pointer;
}

/* 主要内容样式 */
.main-content {
  flex: 1;
  padding: 20px 0;
}

.main-content-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.functional-area {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

/* Element Plus 标签页样式调整 */
.el-tabs__nav-wrap {
  padding: 0 20px;
  background: #f8f9fa;
}

.el-tabs__content {
  padding: 20px;
}

.el-tabs__item {
  padding: 12px 20px;
  font-size: 16px;
}

.el-tabs__item.is-active {
  font-weight: bold;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    padding: 0 15px;
    flex-direction: column;
    height: auto;
    padding: 15px;
  }
  
  .nav-menu {
    margin: 15px 0;
  }
  
  .nav-menu .el-menu {
    flex-wrap: wrap;
  }
  
  .nav-menu .el-menu-item {
    padding: 0 15px;
    font-size: 14px;
  }
  
  .main-content-inner {
    padding: 0 15px;
  }
  
  .el-tabs__content {
    padding: 15px;
  }
}
</style>