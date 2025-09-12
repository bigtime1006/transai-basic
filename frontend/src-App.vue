<template>
  <div id="app">
    <el-container>
      <el-header class="header-container">
        <h1>多格式文档与文本翻译工具</h1>
        <div class="api-status">
          <el-tooltip :content="deepseekStatusMessage" :disabled="deepseekStatus !== 'error'" placement="bottom">
            <el-tag :type="deepseekStatus === 'success' ? 'success' : (deepseekStatus === 'error' ? 'danger' : 'info')" size="medium">
              DeepSeek API: {{ deepseekStatus === 'success' ? '正常' : (deepseekStatus === 'error' ? '异常' : '检查中') }}
            </el-tag>
          </el-tooltip>
          <el-button @click="checkApiStatus" :icon="Refresh" circle size="mini"></el-button>
        </div>
      </el-header>
      <el-main>
        <el-tabs v-model="activeTab" @tab-click="handleTabClick">
          <!-- Document Translation Tab -->
          <el-tab-pane label="文档翻译" name="document">
            <!-- ... existing document translation content ... -->
          </el-tab-pane>

          <!-- Text Translation Tab -->
          <el-tab-pane label="文本翻译" name="text">
            <!-- ... existing text translation content ... -->
          </el-tab-pane>

          <!-- History Tab -->
          <el-tab-pane label="历史记录" name="history">
            <el-table :data="historyList" style="width: 100%" v-loading="isHistoryLoading">
              <el-table-column prop="create_time" label="时间" width="180">
                <template #default="scope">{{ new Date(scope.row.create_time).toLocaleString() }}</template>
              </el-table-column>
              <el-table-column prop="type" label="类型" width="100">
                <template #default="scope">
                  <el-tag :type="scope.row.type === 'document' ? 'primary' : 'success'">{{ scope.row.type === 'document' ? '文档' : '文本' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="120">
                <template #default="scope">
                  <el-tag v-if="scope.row.type === 'document'" :type="getStatusTagType(scope.row.status)">
                    {{ scope.row.status }}
                  </el-tag>
                  <el-tag v-else type="success">completed</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="source_content" label="原文">
                <template #default="scope">
                  <div class="content-cell" :title="scope.row.source_content">{{ scope.row.source_content }}</div>
                </template>
              </el-table-column>
              <el-table-column prop="target_content" label="译文">
                 <template #default="scope">
                    <div v-if="scope.row.type === 'text'" class="content-cell" :title="scope.row.target_content">{{ scope.row.target_content }}</div>
                    <div v-else-if="scope.row.status === 'failed'" class="error-cell" :title="scope.row.error_message">
                      翻译失败
                    </div>
                    <div v-else-if="scope.row.status !== 'completed'">-</div>
                    <div v-else>{{ scope.row.target_content }}</div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="220">
                <template #default="scope">
                  <a :href="`${API_BASE_URL}${scope.row.source_url}`" target="_blank" v-if="scope.row.type === 'document'">下载原文</a>
                  <a :href="`${API_BASE_URL}${scope.row.target_url}`" target="_blank" v-if="scope.row.type === 'document' && scope.row.status === 'completed'" style="margin-left: 10px;">下载译文</a>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </el-main>
    </el-container>
  </div>
</template>

<script>
// ... existing script section ...
import { ElMessage } from 'element-plus';
import { Switch, CopyDocument, Refresh } from '@element-plus/icons-vue';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
// ...

export default {
  // ... existing data, computed, etc. ...
  methods: {
    // ... existing methods ...
    getStatusTagType(status) {
      if (status === 'completed') return 'success';
      if (status === 'failed') return 'danger';
      if (status === 'processing') return 'warning';
      return 'info';
    },
    fetchHistory() {
      this.isHistoryLoading = true;
      axios.get(`${API_BASE_URL}/api/history`)
        .then(response => {
          this.historyList = response.data;
        })
        .catch(error => {
          ElMessage.error('获取历史记录失败');
          console.error(error);
        })
        .finally(() => {
          this.isHistoryLoading = false;
        });
    },
  }
};
</script>

<style>
/* ... existing styles ... */
.error-cell {
  color: #F56C6C;
  cursor: help;
}
</style>
