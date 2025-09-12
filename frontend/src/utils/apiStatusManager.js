// API状态管理器
class ApiStatusManager {
  constructor() {
    this.status = 'unknown'; // 'unknown', 'healthy', 'unhealthy', 'checking'
    this.lastCheck = null;
    this.checkInterval = null;
    this.listeners = [];
    this.autoCheckInterval = 5 * 60 * 1000; // 5分钟自动检查一次
    
    // 开关配置 - 可以通过环境变量或用户设置控制
    this.enabled = this.getDefaultEnabledState();
    
    // 默认禁用，不启动自动检查
    if (!this.enabled) {
      console.log('API状态检查已禁用，不会生成历史记录');
      return;
    }
  }
  
  // 获取默认启用状态
  getDefaultEnabledState() {
    // 优先使用环境变量
    const envEnabled = import.meta.env.VITE_ENABLE_API_STATUS_CHECK;
    if (envEnabled !== undefined) {
      return envEnabled === 'true';
    }
    
    // 其次使用localStorage中的用户偏好
    const userPreference = localStorage.getItem('api-status-check-enabled');
    if (userPreference !== null) {
      return userPreference === 'true';
    }
    
    // 默认禁用，避免生成无用的历史记录
    return false;
  }
  
  // 启用状态检查
  enable() {
    this.enabled = true;
    localStorage.setItem('api-status-check-enabled', 'true');
    this.startAutoCheck();
    console.log('API状态检查已启用');
  }
  
  // 禁用状态检查
  disable() {
    this.enabled = false;
    localStorage.setItem('api-status-check-enabled', 'false');
    this.stopAutoCheck();
    this.status = 'unknown';
    this.notifyListeners('unknown');
    console.log('API状态检查已禁用');
  }
  
  // 切换启用状态
  toggle() {
    if (this.enabled) {
      this.disable();
    } else {
      this.enable();
    }
    return this.enabled;
  }
  
  // 检查是否启用
  isEnabled() {
    return this.enabled;
  }

  // 添加状态变化监听器
  addListener(callback) {
    this.listeners.push(callback);
    // 立即返回当前状态
    callback(this.status);
  }

  // 移除监听器
  removeListener(callback) {
    const index = this.listeners.indexOf(callback);
    if (index > -1) {
      this.listeners.splice(index, 1);
    }
  }

  // 通知所有监听器状态变化
  notifyListeners(newStatus) {
    this.status = newStatus;
    this.listeners.forEach(callback => callback(newStatus));
  }

  // 检查API状态
  async checkApiStatus() {
    // 如果功能被禁用，直接返回
    if (!this.enabled) {
      return 'unknown';
    }
    
    // 如果正在检查中，直接返回
    if (this.status === 'checking') {
      return this.status;
    }

    // 如果距离上次检查时间太短，直接返回缓存状态
    if (this.lastCheck && Date.now() - this.lastCheck < 30000) { // 30秒内不重复检查
      return this.status;
    }

    this.notifyListeners('checking');
    
    try {
      const response = await fetch('/api/health/deepseek', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 10000, // 10秒超时
      });

      if (response.ok) {
        const data = await response.json();
        const newStatus = data.status === 'healthy' ? 'healthy' : 'unhealthy';
        this.notifyListeners(newStatus);
        this.lastCheck = Date.now();
        return newStatus;
      } else {
        this.notifyListeners('unhealthy');
        this.lastCheck = Date.now();
        return 'unhealthy';
      }
    } catch (error) {
      console.error('API状态检查失败:', error);
      this.notifyListeners('unhealthy');
      this.lastCheck = Date.now();
      return 'unhealthy';
    }
  }

  // 手动检查API状态（用户点击检查按钮时）
  async manualCheck() {
    if (!this.enabled) {
      return 'unknown';
    }
    
    this.lastCheck = null; // 清除缓存，强制重新检查
    return await this.checkApiStatus();
  }

  // 启动自动检查
  startAutoCheck() {
    if (!this.enabled) {
      return;
    }
    
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
    }
    
    // 立即检查一次
    this.checkApiStatus();
    
    // 设置定期检查
    this.checkInterval = setInterval(() => {
      this.checkApiStatus();
    }, this.autoCheckInterval);
  }

  // 停止自动检查
  stopAutoCheck() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  // 获取当前状态
  getStatus() {
    return this.status;
  }

  // 获取状态文本
  getStatusText() {
    if (!this.enabled) {
      return '已禁用';
    }
    
    switch (this.status) {
      case 'healthy':
        return '正常';
      case 'unhealthy':
        return '异常';
      case 'checking':
        return '检查中...';
      default:
        return '未知';
    }
  }

  // 获取状态图标类名
  getStatusIcon() {
    if (!this.enabled) {
      return 'el-icon-close';
    }
    
    switch (this.status) {
      case 'healthy':
        return 'el-icon-success';
      case 'unhealthy':
        return 'el-icon-error';
      case 'checking':
        return 'el-icon-loading';
      default:
        return 'el-icon-question';
    }
  }

  // 获取状态样式类名
  getStatusClass() {
    if (!this.enabled) {
      return 'disabled';
    }
    
    switch (this.status) {
      case 'healthy':
        return 'healthy';
      case 'unhealthy':
        return 'unhealthy';
      case 'checking':
        return 'checking';
      default:
        return 'unknown';
    }
  }
}

// 创建全局实例
const apiStatusManager = new ApiStatusManager();

// 默认不启动自动检查，避免生成无用的历史记录
// if (typeof window !== 'undefined') {
//   window.addEventListener('load', () => {
//     apiStatusManager.startAutoCheck();
//   });
// }

export default apiStatusManager;
