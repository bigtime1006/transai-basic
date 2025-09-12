<template>
  <div class="global-api-status">
    <span class="status-label">API状态:</span>
    <span class="status-indicator" :class="statusClass">
      <i :class="statusIcon"></i>
      {{ statusText }}
    </span>
    
    <!-- 开关按钮 -->
    <el-button 
      size="small" 
      @click="toggleStatusCheck" 
      :type="isEnabled ? 'success' : 'info'"
      class="toggle-btn"
    >
      {{ isEnabled ? '关闭' : '开启' }}
    </el-button>
    
    <!-- 检查状态按钮 - 只在启用时显示 -->
    <el-button 
      v-if="isEnabled"
      size="small" 
      @click="manualCheck" 
      :loading="isChecking" 
      class="check-status-btn"
      type="text"
    >
      检查状态
    </el-button>
  </div>
</template>

<script>
import apiStatusManager from '../utils/apiStatusManager.js';

export default {
  name: 'GlobalApiStatus',
  data() {
    return {
      status: 'unknown',
      isChecking: false
    };
  },
  computed: {
    statusClass() {
      return apiStatusManager.getStatusClass();
    },
    statusIcon() {
      return apiStatusManager.getStatusIcon();
    },
    statusText() {
      return apiStatusManager.getStatusText();
    },
    isEnabled() {
      return apiStatusManager.isEnabled();
    }
  },
  mounted() {
    // 注册状态变化监听器
    this.statusListener = (newStatus) => {
      this.status = newStatus;
    };
    apiStatusManager.addListener(this.statusListener);
  },
  beforeDestroy() {
    // 移除监听器
    if (this.statusListener) {
      apiStatusManager.removeListener(this.statusListener);
    }
  },
  methods: {
    async manualCheck() {
      this.isChecking = true;
      try {
        await apiStatusManager.manualCheck();
      } finally {
        this.isChecking = false;
      }
    },
    toggleStatusCheck() {
      apiStatusManager.toggle();
      // 强制更新组件
      this.$forceUpdate();
    }
  }
};
</script>

<style scoped>
.global-api-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.status-label {
  color: #606266;
  font-weight: 500;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-indicator.healthy {
  background-color: #f0f9ff;
  color: #67c23a;
}

.status-indicator.unhealthy {
  background-color: #fef0f0;
  color: #f56c6c;
}

.status-indicator.checking {
  background-color: #f0f9ff;
  color: #409eff;
}

.status-indicator.unknown {
  background-color: #f4f4f5;
  color: #909399;
}

.status-indicator.disabled {
  background-color: #f4f4f5;
  color: #909399;
}

.toggle-btn {
  padding: 2px 8px;
  font-size: 12px;
  margin-left: 8px;
}

.check-status-btn {
  padding: 2px 8px;
  font-size: 12px;
  color: #409eff;
  margin-left: 4px;
}

.check-status-btn:hover {
  color: #66b1ff;
}
</style>
