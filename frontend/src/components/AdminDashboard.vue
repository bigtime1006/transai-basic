<template>
  <div class="admin-dashboard">
    <div class="dashboard-header">
      <h2>系统管理仪表板</h2>
      <p class="dashboard-subtitle">实时监控系统状态和性能指标</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.key">
        <div class="stat-icon" :class="stat.iconClass">
          <i :class="stat.icon"></i>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ stat.value }}</div>
          <div class="stat-label">{{ stat.label }}</div>
        </div>
        <div class="stat-trend" v-if="stat.trend">
          <span :class="stat.trend > 0 ? 'positive' : 'negative'">
            {{ stat.trend > 0 ? '+' : '' }}{{ stat.trend }}%
          </span>
        </div>
      </div>
    </div>

    <!-- 系统健康状态 -->
    <div class="health-section">
      <h3>系统健康状态</h3>
      <div class="health-indicators">
        <div class="health-item" :class="systemHealth.status">
          <div class="health-icon">
            <i :class="getHealthIcon(systemHealth.status)"></i>
          </div>
          <div class="health-info">
            <div class="health-title">整体状态</div>
            <div class="health-status">{{ getHealthText(systemHealth.status) }}</div>
          </div>
        </div>
        
        <div class="health-item" :class="systemHealth.database">
          <div class="health-icon">
            <i class="fas fa-database"></i>
          </div>
          <div class="health-info">
            <div class="health-title">数据库</div>
            <div class="health-status">{{ getHealthText(systemHealth.database) }}</div>
          </div>
        </div>
        
        <div class="health-item" :class="systemHealth.redis">
          <div class="health-icon">
            <i class="fas fa-memory"></i>
          </div>
          <div class="health-info">
            <div class="health-title">Redis</div>
            <div class="health-status">{{ getHealthText(systemHealth.redis) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速操作 -->
    <div class="quick-actions">
      <h3>快速操作</h3>
      <div class="action-buttons">
        <el-button type="primary" @click="refreshStats" :loading="loading">
          <i class="fas fa-sync-alt"></i>
          刷新统计
        </el-button>
        
        <el-button type="success" @click="resetQuotas">
          <i class="fas fa-redo"></i>
          重置配额
        </el-button>
        
        <el-button type="warning" @click="clearLogs">
          <i class="fas fa-trash"></i>
          清理日志
        </el-button>
        
        <el-button type="danger" @click="cleanupPendingBatch">
          <i class="fas fa-broom"></i>
          一键清理待处理批量任务
        </el-button>
        
        <el-button type="info" @click="checkSystemHealth">
          <i class="fas fa-heartbeat"></i>
          系统检查
        </el-button>
      </div>
    </div>

    <!-- 最近活动 -->
    <div class="recent-activity">
      <h3>最近活动</h3>
      <div class="activity-list">
        <div class="activity-item" v-for="activity in recentActivities" :key="activity.id">
          <div class="activity-icon" :class="activity.type">
            <i :class="getActivityIcon(activity.type)"></i>
          </div>
          <div class="activity-content">
            <div class="activity-title">{{ activity.title }}</div>
            <div class="activity-time">{{ formatTime(activity.time) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'AdminDashboard',
  setup() {
    const loading = ref(false)
    const stats = ref([])
    const systemHealth = ref({
      status: 'unknown',
      database: 'unknown',
      redis: 'unknown'
    })
    const recentActivities = ref([])

    // 获取仪表板统计数据
    const fetchDashboardStats = async () => {
      try {
        loading.value = true
        const response = await fetch('/api/admin/dashboard', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          updateStats(data)
        } else {
          ElMessage.error('获取统计数据失败')
        }
      } catch (error) {
        console.error('获取统计数据错误:', error)
        ElMessage.error('获取统计数据失败')
      } finally {
        loading.value = false
      }
    }

    // 更新统计数据
    const updateStats = (data) => {
      stats.value = [
        {
          key: 'users',
          label: '总用户数',
          value: data.total_users,
          icon: 'fas fa-users',
          iconClass: 'users'
        },
        {
          key: 'active_users',
          label: '活跃用户',
          value: data.active_users,
          icon: 'fas fa-user-check',
          iconClass: 'active'
        },
        {
          key: 'translations',
          label: '总翻译数',
          value: data.total_translations,
          icon: 'fas fa-language',
          iconClass: 'translations'
        },
        {
          key: 'tasks',
          label: '总任务数',
          value: data.total_tasks,
          icon: 'fas fa-tasks',
          iconClass: 'tasks'
        },
        {
          key: 'pending_tasks',
          label: '待处理任务',
          value: data.pending_tasks,
          icon: 'fas fa-clock',
          iconClass: 'pending'
        },
        {
          key: 'engines',
          label: '活跃引擎',
          value: data.active_engines,
          icon: 'fas fa-cogs',
          iconClass: 'engines'
        }
      ]
    }

    // 检查系统健康状态
    const checkSystemHealth = async () => {
      try {
        const response = await fetch('/api/admin/system/health', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          systemHealth.value = {
            status: data.overall_health,
            database: data.database,
            redis: data.redis
          }
          ElMessage.success('系统健康检查完成')
        } else {
          ElMessage.error('系统健康检查失败')
        }
      } catch (error) {
        console.error('系统健康检查错误:', error)
        ElMessage.error('系统健康检查失败')
      }
    }

    // 重置配额
    const resetQuotas = async () => {
      try {
        const response = await fetch('/api/admin/maintenance/reset-quotas', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          ElMessage.success(data.message)
          fetchDashboardStats()
        } else {
          ElMessage.error('重置配额失败')
        }
      } catch (error) {
        console.error('重置配额错误:', error)
        ElMessage.error('重置配额失败')
      }
    }

    // 清理日志
    const clearLogs = async () => {
      try {
        const response = await fetch('/api/admin/maintenance/clear-logs?days=30', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          ElMessage.success(data.message)
        } else {
          ElMessage.error('清理日志失败')
        }
      } catch (error) {
        console.error('清理日志错误:', error)
        ElMessage.error('清理日志失败')
      }
    }

    // 一键清理待处理批量任务
    const cleanupPendingBatch = async () => {
      try {
        loading.value = true
        const resp = await fetch('/api/admin/history/cleanup/pending-batch', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        if (resp.ok) {
          const data = await resp.json()
          ElMessage.success(`已清理待处理任务: ${data.deleted_tasks}，批次关联: ${data.deleted_batch_items}，空批次: ${data.deleted_empty_batches}`)
        } else if (resp.status === 403) {
          ElMessage.error('需要管理员权限')
        } else {
          const err = await resp.json().catch(() => ({}))
          ElMessage.error(err.detail || '清理失败')
        }
      } catch (e) {
        ElMessage.error('清理失败')
      } finally {
        loading.value = false
      }
    }

    // 刷新统计
    const refreshStats = () => {
      fetchDashboardStats()
      checkSystemHealth()
    }

    // 获取健康状态图标
    const getHealthIcon = (status) => {
      const icons = {
        healthy: 'fas fa-check-circle',
        warning: 'fas fa-exclamation-triangle',
        critical: 'fas fa-times-circle',
        unknown: 'fas fa-question-circle'
      }
      return icons[status] || icons.unknown
    }

    // 获取健康状态文本
    const getHealthText = (status) => {
      const texts = {
        healthy: '正常',
        warning: '警告',
        critical: '严重',
        unknown: '未知'
      }
      return texts[status] || '未知'
    }

    // 获取活动图标
    const getActivityIcon = (type) => {
      const icons = {
        user: 'fas fa-user',
        translation: 'fas fa-language',
        system: 'fas fa-cog',
        error: 'fas fa-exclamation-triangle'
      }
      return icons[type] || 'fas fa-info-circle'
    }

    // 格式化时间
    const formatTime = (time) => {
      return new Date(time).toLocaleString('zh-CN')
    }

    onMounted(() => {
      fetchDashboardStats()
      checkSystemHealth()
    })

    return {
      loading,
      stats,
      systemHealth,
      recentActivities,
      refreshStats,
      resetQuotas,
      clearLogs,
      cleanupPendingBatch,
      checkSystemHealth,
      getHealthIcon,
      getHealthText,
      getActivityIcon,
      formatTime
    }
  }
}
</script>

<style scoped>
.admin-dashboard {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-header {
  text-align: center;
  margin-bottom: 30px;
}

.dashboard-header h2 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.dashboard-subtitle {
  color: #7f8c8d;
  font-size: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  transition: transform 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
  font-size: 24px;
  color: white;
}

.stat-icon.users { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.stat-icon.active { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
.stat-icon.translations { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
.stat-icon.tasks { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
.stat-icon.pending { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
.stat-icon.engines { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 5px;
}

.stat-label {
  color: #7f8c8d;
  font-size: 14px;
}

.stat-trend {
  font-size: 12px;
  font-weight: bold;
}

.stat-trend.positive {
  color: #27ae60;
}

.stat-trend.negative {
  color: #e74c3c;
}

.health-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.health-section h3 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.health-indicators {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.health-item {
  display: flex;
  align-items: center;
  padding: 15px;
  border-radius: 8px;
  border: 2px solid;
}

.health-item.healthy {
  border-color: #27ae60;
  background: #d5f4e6;
}

.health-item.warning {
  border-color: #f39c12;
  background: #fef9e7;
}

.health-item.critical {
  border-color: #e74c3c;
  background: #fadbd8;
}

.health-item.unknown {
  border-color: #95a5a6;
  background: #f8f9fa;
}

.health-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  font-size: 18px;
}

.health-item.healthy .health-icon {
  color: #27ae60;
}

.health-item.warning .health-icon {
  color: #f39c12;
}

.health-item.critical .health-icon {
  color: #e74c3c;
}

.health-item.unknown .health-icon {
  color: #95a5a6;
}

.health-title {
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 5px;
}

.health-status {
  font-size: 14px;
  color: #7f8c8d;
}

.quick-actions {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 30px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.quick-actions h3 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
}

.recent-activity {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.recent-activity h3 {
  color: #2c3e50;
  margin-bottom: 20px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.activity-item {
  display: flex;
  align-items: center;
  padding: 15px;
  border-radius: 8px;
  background: #f8f9fa;
  transition: background-color 0.2s ease;
}

.activity-item:hover {
  background: #e9ecef;
}

.activity-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  font-size: 16px;
  color: white;
}

.activity-icon.user { background: #3498db; }
.activity-icon.translation { background: #e74c3c; }
.activity-icon.system { background: #9b59b6; }
.activity-icon.error { background: #f39c12; }

.activity-content {
  flex: 1;
}

.activity-title {
  font-weight: bold;
  color: #2c3e50;
  margin-bottom: 5px;
}

.activity-time {
  font-size: 12px;
  color: #7f8c8d;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .health-indicators {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }
}
</style>

