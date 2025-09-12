<template>
  <el-card class="batch-history-section">
    <template #header>
      <div class="history-header">
        <h3>{{ $t('batch.historyTitle') || '批量翻译历史' }}</h3>
        <div class="header-actions">
          <!-- Filters -->
          <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width:120px">
            <el-option v-for="opt in statusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-select v-model="filterEngine" placeholder="引擎" clearable size="small" style="width:140px">
            <el-option v-for="opt in engineOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-input v-model="filterUsername" placeholder="用户名(管理员)" clearable size="small" style="width:160px" />
          <el-select v-model="sortBy" placeholder="排序字段" clearable size="small" style="width:140px">
            <el-option v-for="opt in sortFieldOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-select v-model="sortOrder" placeholder="顺序" clearable size="small" style="width:110px">
            <el-option v-for="opt in sortOrderOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-switch
            v-model="isAutoRefreshEnabled"
            :active-text="$t('common.autoRefresh') || '自动刷新'"
            style="margin-right: 15px;"
            @change="handleAutoRefreshToggle"
          ></el-switch>
          <el-button 
            size="small" 
            @click="refreshBatchHistory" 
            :loading="loadingBatchHistory"
            type="primary"
          >
            {{ $t('common.refresh') || '刷新' }}
          </el-button>
        </div>
      </div>
    </template>
    
    <!-- 当前批次汇总（可选显示） -->
    <div v-if="batchSummary && batchSummary.total > 0" class="batch-summary-bar">
      <span>批次 {{ batchSummary.batch_id }}</span>
      <span>总文件：{{ batchSummary.total }}</span>
      <span>已完成：{{ batchSummary.completed }}</span>
      <span>失败：{{ batchSummary.failed }}</span>
      <span>Tokens：{{ batchSummary.tokens }}</span>
    </div>

    <!-- 正在进行的任务 -->
    <div v-if="ongoingTasks.length > 0" class="ongoing-tasks-section">
      <h4>{{ $t('batch.ongoingTitle') || '正在进行的任务' }}</h4>
      <div class="history-list">
        <div 
          v-for="item in ongoingTasks" 
          :key="item.task_id" 
          class="history-item"
          :class="{ 'current-batch': currentBatchTaskIds.has(item.task_id) }"
        >
          <!-- History Item Content -->
          <div class="history-content">
            <div class="history-meta">
              <span class="engine-tag">{{ item.engine }}</span>
              <span class="strategy-tag">{{ item.strategy }}</span>
              <span class="lang-info">{{ item.source_lang }} → {{ item.target_lang }}</span>
              <span class="username" v-if="item.username">{{ $t('common.user') || '用户' }}: {{ item.username }}</span>
              <span class="time">{{ formatTime(item.create_time) }}</span>
            </div>
            <div class="history-details">
              <div class="filename">
                <strong>{{ $t('doc.fileName') || '文件名' }}：</strong>
                <span>{{ item.file_name || '批量任务' }}</span>
              </div>
              <div class="status-info">
                <strong>{{ $t('doc.status') || '状态' }}：</strong>
                <el-tag :type="getStatusType(item.status)" size="small">{{ getStatusText(item.status) }}</el-tag>
              </div>
            </div>
          </div>
          <div class="history-actions">
            <!-- No actions for ongoing tasks -->
          </div>
        </div>
      </div>
    </div>

    <!-- 已完成的历史记录 -->
    <div class="completed-history-section" :style="{ 'margin-top': ongoingTasks.length > 0 ? '20px' : '0' }">
       <h4 v-if="ongoingTasks.length > 0">{{ $t('batch.completedTitle') || '已完成的历史记录' }}</h4>
      <div v-if="completedTasks.length === 0 && ongoingTasks.length === 0" class="no-history">
        <el-empty :description="$t('batch.noHistory') || '暂无批量翻译历史'" :image-size="80"></el-empty>
      </div>
      
      <div v-if="completedTasks.length > 0" class="history-list">
        <div 
          v-for="item in completedTasks" 
          :key="item.task_id" 
          class="history-item"
          :class="{ 'current-batch': currentBatchTaskIds.has(item.task_id) }"
        >
          <!-- History Item Content -->
          <div class="history-content">
            <div class="history-meta">
              <span class="engine-tag">{{ item.engine }}</span>
              <span class="strategy-tag">{{ item.strategy }}</span>
              <span class="lang-info">{{ item.source_lang }} → {{ item.target_lang }}</span>
              <span class="username" v-if="item.username">{{ $t('common.user') || '用户' }}: {{ item.username }}</span>
              <span class="time">{{ formatTime(item.create_time) }}</span>
            </div>
            <div class="history-details">
              <div class="filename">
                <strong>{{ $t('doc.fileName') || '文件名' }}：</strong>
                <span>{{ item.file_name || '批量任务' }}</span>
              </div>
              <div v-if="item.engine_params" style="margin:6px 0;">
                <el-button size="small" @click="toggleBatchParams(item.task_id)">{{ $t('common.engineParams') || '引擎参数' }}</el-button>
                <div v-if="showBatchParams[item.task_id]" style="margin-top:6px;background:#f6f8fa;padding:8px;border-radius:4px;font-size:12px;">
                  <pre style="white-space:pre-wrap;word-break:break-word;">{{ formatEngineParams(item.engine_params) }}</pre>
                </div>
              </div>
              <div class="term-categories" v-if="item.term_category_ids && item.term_category_ids.length">
                <strong>{{ $t('doc.termCategories') || '术语分类' }}：</strong>
                <el-tag size="small" style="margin-right:4px;" v-for="cid in item.term_category_ids" :key="cid">{{ categoryName(cid) }}</el-tag>
              </div>
              <div class="status-info">
                <strong>{{ $t('doc.status') || '状态' }}：</strong>
                <el-tag :type="getStatusType(item.status)" size="small">{{ getStatusText(item.status) }}</el-tag>
                <span v-if="item.duration" class="duration">{{ $t('doc.duration') || '耗时' }} {{ item.duration }}{{ $t('doc.seconds') || '秒' }}</span>
                <span v-if="item.token_count !== null" class="duration">Tokens: {{ item.token_count }}</span>
                <span v-if="item.source_file_size !== null" class="duration">{{ $t('doc.source') || '源文件' }}: {{ (item.source_file_size/1024).toFixed(1) }}KB</span>
                <span v-if="item.target_file_size !== null" class="duration">{{ $t('doc.target') || '目标文件' }}: {{ (item.target_file_size/1024).toFixed(1) }}KB</span>
                <span v-if="item.total_texts !== null" class="duration">{{ $t('batch.totalTexts') || '总文本' }}: {{ item.total_texts }}</span>
                <span v-if="item.translated_texts !== null" class="duration">{{ $t('batch.translatedTexts') || '已译文本' }}: {{ item.translated_texts }}</span>
              </div>
            </div>
          </div>
          <div class="history-actions">
            <el-button 
              v-if="item.result_path" 
              size="small" 
              type="success"
              @click="downloadFile(item.result_path)"
            >
              {{ $t('doc.download') || '下载' }}
            </el-button>
            <el-button 
              size="small" 
              @click="emitRetranslate(item)"
            >
              {{ $t('batch.retranslate') || '重新翻译' }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="removeBatchHistory(item)"
            >
              {{ $t('common.delete') || '删除' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分页控件 -->
    <div v-if="totalItems > 0" class="pagination-container">
      <el-pagination
        background
        layout="prev, pager, next"
        :total="totalItems"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handlePageChange"
      ></el-pagination>
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useI18n } from 'vue-i18n';

const { t: $t } = useI18n();

const props = defineProps({
  currentBatchId: {
    type: String,
    default: null,
  },
  availableCategories: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(['retranslate-clicked']);

const batchHistory = ref([]);
const loadingBatchHistory = ref(false);
const showBatchParams = ref({});
const isAutoRefreshEnabled = ref(true);
const historyRefreshTimer = ref(null);
const currentBatchTaskIds = ref(new Set());
const handleAutoRefreshToggle = (val) => {
  // 由 watch(isAutoRefreshEnabled) 处理实际开启/关闭逻辑
};
const batchSummary = ref(null);

// Filters & sorting state
const filterStatus = ref(null);
const filterEngine = ref(null);
const filterUsername = ref("");
const sortBy = ref(null);
const sortOrder = ref("desc");

const statusOptions = [
  { value: 'pending', label: $t('batch.statusTypes.pending') || '等待中' },
  { value: 'processing', label: $t('batch.statusTypes.processing') || '处理中' },
  { value: 'completed', label: $t('batch.statusTypes.completed') || '已完成' },
  { value: 'failed', label: $t('batch.statusTypes.failed') || '失败' },
];
const sortFieldOptions = [
  { value: 'create_time', label: '创建时间' },
  { value: 'token_count', label: 'Tokens' },
  { value: 'duration', label: '耗时' },
  { value: 'source_file_size', label: '源文件大小' },
  { value: 'target_file_size', label: '目标文件大小' },
];
const sortOrderOptions = [
  { value: 'desc', label: '降序' },
  { value: 'asc', label: '升序' },
];
const engineOptions = ref([]);

// Pagination state
const currentPage = ref(1);
const pageSize = ref(10);
const totalItems = ref(0);

const ongoingTasks = computed(() => 
  batchHistory.value.filter(item => ['pending', 'processing'].includes(item.status?.toLowerCase()))
);

const completedTasks = computed(() => 
  batchHistory.value.filter(item => !['pending', 'processing'].includes(item.status?.toLowerCase()))
);

const getStatusType = (status) => {
  const types = {
    'pending': 'info', 'processing': 'warning', 'completed': 'success', 'failed': 'danger',
    'PENDING': 'info', 'PROCESSING': 'warning', 'COMPLETED': 'success', 'FAILED': 'danger'
  };
  return types[status] || 'info';
};

const getStatusText = (status) => {
  const s = (status || '').toLowerCase();
  const statusMap = {
    pending: $t('batch.statusTypes.pending') || '等待中',
    processing: $t('batch.statusTypes.processing') || '处理中',
    completed: $t('batch.statusTypes.completed') || '已完成',
    failed: $t('batch.statusTypes.failed') || '失败',
  };
  return statusMap[s] || status || '';
};

const formatTime = (timestamp) => {
  if (!timestamp) return '未知时间';
  return new Date(timestamp).toLocaleString();
};

const categoryName = (id) => {
  const category = props.availableCategories.find(c => c.id === id);
  return category ? category.name : id;
};

const formatEngineParams = (params) => {
  if (!params) return '无参数';
  try {
    return JSON.stringify(params, null, 2);
  } catch (e) {
    return params;
  }
};

const toggleBatchParams = (taskId) => {
  showBatchParams.value[taskId] = !showBatchParams.value[taskId];
};

const downloadFile = (filePath) => {
  if (!filePath) {
    ElMessage.warning('文件路径不存在，无法下载');
    return;
  }
  const fileName = filePath.split('/').pop();
  const link = document.createElement('a');
  const baseUrl = import.meta.env.VITE_API_BASE_URL || (window.location.origin.includes(':5173') ? 'http://localhost:8000' : window.location.origin);
  let downloadUrl = filePath.startsWith('http') ? filePath : (filePath.startsWith('/') ? `${baseUrl}${filePath}` : `${baseUrl}/${filePath}`);
  
  link.href = downloadUrl;
  link.download = fileName;
  link.target = '_blank';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  ElMessage.success(`开始下载: ${fileName}`);
};

const emitRetranslate = (item) => {
  emit('retranslate-clicked', item);
};

const removeBatchHistory = async (item) => {
  try {
    await ElMessageBox.confirm(`确定要删除批次 "${item.task_id}" 的记录吗？`, '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    const token = localStorage.getItem('token');
    const response = await fetch(`/api/history/${item.task_id}?type=document`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    ElMessage.success('批次记录已删除');
    await refreshBatchHistory();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除批次记录失败');
    }
  }
};

const loadBatchHistoryData = async () => {
  loadingBatchHistory.value = true;
  try {
    const token = localStorage.getItem('token');
    const params = new URLSearchParams({
      page: String(currentPage.value),
      limit: String(pageSize.value),
      batch_only: 'true',
    });
    if (filterStatus.value) params.set('status', filterStatus.value);
    if (filterEngine.value) params.set('engine', filterEngine.value);
    if (filterUsername.value) params.set('username', filterUsername.value.trim());
    if (sortBy.value) params.set('sortBy', sortBy.value);
    if (sortOrder.value) params.set('sortOrder', sortOrder.value);

    const url = `/api/history/document?${params.toString()}`;
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (!response.ok) throw new Error('Failed to fetch history');
    const data = await response.json();
    batchHistory.value = data.items;
    totalItems.value = data.total;

    const hasOngoingTasks = data.items.some(item => ['pending', 'processing'].includes(item.status?.toLowerCase()));
    if (!hasOngoingTasks && isAutoRefreshEnabled.value) {
      isAutoRefreshEnabled.value = false;
    }
  } catch (error) {
    ElMessage.error('加载批量翻译历史失败: ' + error.message);
  } finally {
    loadingBatchHistory.value = false;
  }
};

const handlePageChange = (page) => {
  currentPage.value = page;
  loadBatchHistoryData();
};

const refreshBatchHistory = async () => {
  currentPage.value = 1; // Refresh should always go back to the first page
  await loadBatchHistoryData();
  ElMessage.success('批量翻译历史已刷新');
};

watch(isAutoRefreshEnabled, (newValue) => {
  if (newValue) {
    if (!historyRefreshTimer.value) {
      historyRefreshTimer.value = setInterval(loadBatchHistoryData, 30000);
      loadBatchHistoryData();
    }
  } else {
    if (historyRefreshTimer.value) {
      clearInterval(historyRefreshTimer.value);
      historyRefreshTimer.value = null;
    }
  }
}, { immediate: true });

// 监听筛选/排序变化，回到第一页并刷新
watch([filterStatus, filterEngine, filterUsername, sortBy, sortOrder], () => {
  currentPage.value = 1;
  loadBatchHistoryData();
});

// 拉取当前批次的 task_id 集合用于高亮
watch(() => props.currentBatchId, async (bid) => {
  currentBatchTaskIds.value = new Set();
  if (!bid) return;
  try {
    const token = localStorage.getItem('token');
    const resp = await fetch(`/api/batch/${bid}`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (resp.ok) {
      const data = await resp.json();
      if (Array.isArray(data.items)) {
        currentBatchTaskIds.value = new Set(data.items.map(it => it.task_id));
      }
      // 若存在当前批次，自动开启自动刷新
      if (!isAutoRefreshEnabled.value) {
        isAutoRefreshEnabled.value = true;
      }
      // 保存批次汇总
      batchSummary.value = {
        batch_id: data.batch_id,
        total: data.total,
        completed: data.completed,
        failed: data.failed,
        tokens: data.tokens,
      };
    }
  } catch {}
}, { immediate: true });

onMounted(() => {
  if (isAutoRefreshEnabled.value) {
    loadBatchHistoryData();
  }
  // 加载可用引擎列表
  (async () => {
    try {
      const resp = await fetch('/api/engines/available');
      if (resp.ok) {
        const list = await resp.json();
        engineOptions.value = list.map(e => ({ value: e.engine_name, label: e.display_name || e.engine_name }));
      }
    } catch {}
  })();
});

onUnmounted(() => {
  if (historyRefreshTimer.value) {
    clearInterval(historyRefreshTimer.value);
  }
});

defineExpose({
  refreshBatchHistory,
});
</script>

<style scoped>
.batch-history-section {
  margin-top: 12px;
  padding: 16px 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background-color: #fff;
}

.history-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.history-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
  letter-spacing: 0.5px;
  white-space: nowrap; /* 防止标题被挤压成竖排 */
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap; /* 过滤控件过多时自动换行到下一行 */
}

.ongoing-tasks-section h4, .completed-history-section h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #333;
  font-size: 16px;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.batch-summary-bar {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 10px;
  background: #f8fafc;
  border: 1px dashed #e4e7ed;
  border-radius: 6px;
  color: #606266;
  font-size: 13px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background-color: #fff;
  transition: background-color 0.3s ease;
}

.history-item:hover {
  background-color: #f0f9eb;
}

.history-item.current-batch {
  border: 2px solid #409eff;
  box-shadow: 0 0 10px rgba(64, 158, 255, 0.2);
}

.history-content {
  flex-grow: 1;
  margin-right: 15px;
}

.history-meta {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.engine-tag, .strategy-tag {
  background-color: #ecf5ff;
  color: #409eff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.lang-info, .username, .time {
  color: #909399;
  font-size: 12px;
}

.history-details {
  font-size: 14px;
  color: #333;
}

.filename {
  margin-bottom: 5px;
}

.term-categories {
  margin: 5px 0;
}

.status-info {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 5px;
}

.duration {
  color: #909399;
  font-size: 12px;
}

.history-actions {
  display: flex;
  gap: 8px;
}

.no-history {
  text-align: center;
  padding: 40px 0;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
