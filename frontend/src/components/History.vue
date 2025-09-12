<template>
  <div class="history-container">
    <!-- 添加刷新按钮和状态显示 -->
    <div class="history-header">
      <h3>翻译历史记录</h3>
      <div class="header-actions">
        <el-button 
          @click="refreshHistory" 
          :loading="isLoading" 
          type="primary" 
          size="small"
          icon="el-icon-refresh"
        >
          刷新
        </el-button>
        <span v-if="lastFetchTime" class="last-update">
          最后更新: {{ formatLastUpdate() }}
        </span>
      </div>
    </div>
    
    <el-table :data="historyList" style="width: 100%" v-loading="isLoading" :row-key="'id'" :expand-row-keys="expandedRows" @expand-change="handleExpandChange" class="custom-table">
      <el-table-column type="expand">
        <template #default="props">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="任务ID">{{ props.row.id }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ props.row.type === 'document' ? '文档' : '文本' }}</el-descriptions-item>
            <el-descriptions-item label="源语言">{{ props.row.source_lang }}</el-descriptions-item>
            <el-descriptions-item label="目标语言">{{ props.row.target_lang }}</el-descriptions-item>
            <el-descriptions-item v-if="props.row.type === 'document'" label="引擎">{{ props.row.engine }}</el-descriptions-item>
            <el-descriptions-item v-if="props.row.type === 'document'" label="策略">{{ props.row.strategy }}</el-descriptions-item>
            <el-descriptions-item v-if="props.row.type === 'document' && props.row.source_file_size !== null" label="源文件大小">{{ formatFileSize(props.row.source_file_size) }}</el-descriptions-item>
            <el-descriptions-item v-if="props.row.type === 'document' && props.row.target_file_size !== null" label="目标文件大小">{{ formatFileSize(props.row.target_file_size) }}</el-descriptions-item>
            <el-descriptions-item v-if="props.row.character_count !== null" label="字符数">{{ props.row.character_count }}</el-descriptions-item>
            <el-descriptions-item v-if="props.row.token_count !== null" label="Token数">{{ props.row.token_count }}</el-descriptions-item>
            <el-descriptions-item v-if="props.row.type === 'text' && props.row.byte_count !== null" label="字节数">{{ props.row.byte_count }}</el-descriptions-item>
            <el-descriptions-item v-if="props.row.duration !== null" label="耗时">{{ props.row.duration }} 秒</el-descriptions-item>
            <el-descriptions-item v-if="props.row.type === 'document' && props.row.error_message" label="错误信息" :span="2">
              <el-alert type="error" :closable="false" :title="props.row.error_message" />
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </el-table-column>
      <el-table-column prop="create_time" label="时间" width="180">
        <template #default="scope">
          {{ formatDateTime(scope.row.create_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="source_content" label="文件名 / 原文" width="250">
        <template #default="scope">
          <a v-if="scope.row.type === 'document'" :href="scope.row.source_url" target="_blank" :title="scope.row.source_content" class="content-cell">
            {{ scope.row.source_content }}
          </a>
          <div v-else class="content-cell" :title="scope.row.source_content">
            {{ scope.row.source_content }}
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="type" label="类型" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.type === 'document' ? 'primary' : 'success'">
            {{ scope.row.type === 'document' ? '文档' : '文本' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_content" label="译文">
         <template #default="scope">
            <a v-if="scope.row.type === 'document' && scope.row.target_url" :href="scope.row.target_url" target="_blank">下载文件</a>
            <div v-else-if="scope.row.type !== 'document'" class="content-cell">{{ scope.row.target_content }}</div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
         <template #default="scope">
            <el-tag v-if="scope.row.type === 'document'" :type="scope.row.status === 'completed' ? 'success' : (scope.row.status === 'failed' ? 'danger' : 'warning')">
              {{ scope.row.status }}
            </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="scope">
          <el-button @click="handleDelete(scope.row)" type="danger" size="small">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script>
import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default {
  name: 'History',
  data() {
    return {
      historyList: [],
      isLoading: false,
      expandedRows: [],
      lastFetchTime: null, // 记录最后获取时间
      cacheExpiry: 5 * 60 * 1000, // 5分钟缓存过期
    };
  },
  // 使用activated钩子，避免重复创建组件时重复请求
  activated() {
    // 如果数据为空才重新获取
    if (this.historyList.length === 0) {
      this.fetchHistory();
    }
  },
  // 组件首次创建时获取数据
  mounted() {
    this.fetchHistory();
  },
  methods: {
    fetchHistory() {
      // 检查缓存是否有效
      if (this.lastFetchTime && (Date.now() - this.lastFetchTime) < this.cacheExpiry) {
        console.log('使用缓存的历史记录数据');
        return;
      }
      
      this.isLoading = true;
      
      // 设置请求超时
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时
      
      axios.get(`${API_BASE_URL}/api/history`, {
        signal: controller.signal,
        timeout: 10000
      })
        .then(response => {
          this.historyList = response.data.map(item => {
            if (item.type === 'document') {
              if (item.source_url && !item.source_url.startsWith('http')) {
                item.source_url = `${API_BASE_URL}${item.source_url}`;
              }
              if (item.target_url && !item.target_url.startsWith('http')) {
                item.target_url = `${API_BASE_URL}${item.target_url}`;
              }
            }
            return item;
          });
          this.lastFetchTime = Date.now(); // 更新缓存时间
          console.log('历史记录获取成功，数据条数:', this.historyList.length);
        })
        .catch((error) => {
          if (error.name === 'AbortError') {
            ElMessage.error('获取历史记录超时，请重试');
          } else {
            ElMessage.error('获取历史记录失败');
          }
          console.error('获取历史记录失败:', error);
        })
        .finally(() => {
          clearTimeout(timeoutId);
          this.isLoading = false;
        });
    },
    handleDelete(item) {
      ElMessageBox.confirm(
        `确定要永久删除这条记录吗？${item.type === 'document' ? '相关文件也将被删除。' : ''}`,
        '确认删除',
        {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        }
      ).then(() => {
        axios.delete(`${API_BASE_URL}/api/history/${item.id}?type=${item.type}`)
          .then(() => {
            ElMessage.success('删除成功');
            this.historyList = this.historyList.filter(h => h.id !== item.id);
          })
          .catch(error => {
            ElMessage.error(error.response?.data?.detail || '删除失败');
          });
      }).catch(() => {});
    },
    formatFileSize(bytes) {
      if (bytes === null || bytes === undefined) return 'N/A';
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    handleExpandChange(row, expandedRows) {
      this.expandedRows = expandedRows.map(r => r.id);
    },
    
    // 手动刷新历史记录
    refreshHistory() {
      this.lastFetchTime = null; // 清除缓存，强制刷新
      this.fetchHistory();
    },
    
    // 格式化最后更新时间
    formatLastUpdate() {
      if (!this.lastFetchTime) return '从未更新';
      
      const now = Date.now();
      const diff = now - this.lastFetchTime;
      
      if (diff < 60000) { // 1分钟内
        return '刚刚';
      } else if (diff < 3600000) { // 1小时内
        return `${Math.floor(diff / 60000)}分钟前`;
      } else if (diff < 86400000) { // 1天内
        return `${Math.floor(diff / 3600000)}小时前`;
      } else {
        return new Date(this.lastFetchTime).toLocaleString('zh-CN');
      }
    },
    
    // 格式化日期时间，确保使用北京时间
    formatDateTime(dateTimeString) {
      try {
        const date = new Date(dateTimeString);
        // 检查日期是否有效
        if (isNaN(date.getTime())) {
          return '时间格式错误';
        }
        
        // 使用北京时间格式化
        return date.toLocaleString('zh-CN', {
          timeZone: 'Asia/Shanghai',
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false
        });
      } catch (error) {
        console.error('时间格式化错误:', error);
        return '时间格式错误';
      }
    },
  }
};
</script>

<style scoped>
.history-container {
  padding: 20px;
  background-color: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e0e0e0;
}

.history-header h3 {
  margin: 0;
  color: #333;
  font-size: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.last-update {
  font-size: 12px;
  color: #666;
  font-style: italic;
}

.content-cell {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 加载状态优化 */
.el-table {
  min-height: 400px;
}

/* 空数据状态 */
.el-table__empty-block {
  min-height: 200px;
}
</style>
