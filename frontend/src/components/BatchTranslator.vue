<template>
  <div class="batch-translator">
    <!-- 翻译选项行 - 与文档翻译保持一致 -->
    <div class="translation-options-row">
      <!-- 源语言选择 -->
      <div class="option-item">
        <span class="option-label">{{ $t('doc.sourceLang') }}</span>
        <el-select v-model="form.source_lang" :placeholder="$t('doc.selectSource')" class="compact-select">
          <el-option v-for="item in sourceLangOptions" :key="item.value" :label="$t('lang.'+item.value)" :value="item.value"></el-option>
        </el-select>
      </div>
      
      <!-- 语言交换按钮 -->
      <div class="swap-button-container">
        <el-button @click="swapLanguages" icon="el-icon-sort" circle size="small"></el-button>
      </div>
      
      <!-- 目标语言选择 -->
      <div class="option-item">
        <span class="option-label">{{ $t('doc.targetLang') }}</span>
        <el-select v-model="form.target_lang" :placeholder="$t('doc.selectTarget')" class="compact-select">
          <el-option v-for="item in targetLangOptions" :key="item.value" :label="$t('lang.'+item.value)" :value="item.value"></el-option>
        </el-select>
      </div>
      
      <!-- 风格预设 -->
      <div class="option-item" style="min-width:160px;">
        <span class="option-label">{{ $t('style.presetLabel') }}</span>
        <el-tooltip :content="$t('style.help')" placement="top">
          <el-select v-model="form.style_preset" clearable :placeholder="$t('style.presetPh')" class="compact-select" style="width:140px;">
            <el-option v-for="preset in stylePresets" :key="preset.value" :label="preset.label" :value="preset.value" />
          </el-select>
        </el-tooltip>
      </div>
    </div>

    <!-- 术语分类选择器 -->
    <div class="category-selection-row" v-if="terminologyOptions.categories_enabled">
      <CategorySelector
        v-model="form.category_ids"
        :categories="availableCategories"
        :max-categories="terminologyOptions.max_categories_per_translation"
        @change="handleCategoryChange"
      />
      <div v-if="form.category_ids.length" style="margin-top:8px;color:#666;font-size:13px;">
        {{$t('doc.selectedCategories')}}：
        <span>{{ selectedCategoryNames.join('、') }}</span>
      </div>
    </div>

    <!-- 文件上传区域 -->
    <el-card class="upload-section">
      <template #header>
        <span>{{ $t('batch.uploadTitle') }}</span>
      </template>
      
      <el-upload
        ref="uploadRef"
        :action="null"
        :auto-upload="false"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
        :multiple="true"
        :accept="acceptedFileTypes"
        drag
        class="batch-upload"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          {{ $t('batch.dropFiles') }} <em>{{ $t('batch.clickToSelect') }}</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            {{ $t('batch.fileTypes') }} ({{ $t('batch.maxFiles') }}: 100)
          </div>
        </template>
      </el-upload>
    </el-card>

    <!-- 自定义指令 -->
    <el-form label-width="100px" style="margin-top:10px;">
      <el-form-item :label="$t('style.customLabel')">
        <el-input
          v-model="form.style_instruction"
          type="textarea"
          :rows="2"
          :placeholder="$t('style.help')"
          maxlength="300"
          show-word-limit
        />
      </el-form-item>
    </el-form>

    <!-- 提交按钮 -->
    <div class="submit-section">
      <el-button
        type="primary"
        size="large"
        :loading="submitting"
        :disabled="!canSubmit"
        @click="submitBatch"
      >
        {{ $t('batch.startTranslation') }}
      </el-button>
      <p class="submit-tip">{{ $t('batch.submitTip') }}</p>
      <p class="async-note">{{ $t('batch.asyncNote') }}</p>
    </div>

    <!-- 批次总体进度（简版） -->
    <el-alert v-if="currentBatch" type="info" :closable="false" show-icon style="margin-top: 10px;">
      <template #title>
        {{ $t('batch.statusTitle') }} - {{ currentBatch.batch_id }} | {{ currentBatch.completed }}/{{ currentBatch.total }} | Tokens {{ currentBatch.tokens }}
        <el-button size="small" style="margin-left:8px" @click="refreshBatchStatus" :loading="refreshing">刷新</el-button>
        <el-button size="small" style="margin-left:4px" @click="pruneBatchItems" type="primary">清理已完成项</el-button>
        <el-button size="small" style="margin-left:4px" @click="cancelBatchTranslation" type="danger">取消翻译</el-button>
      </template>
      <el-progress :percentage="progressPercentage" :status="progressStatus" :stroke-width="8" style="margin-top:8px"/>
    </el-alert>

    <!-- 批量翻译历史记录（新组件） -->
    <div class="history-wrapper">
      <BatchHistoryList
        ref="historyListRef"
        :current-batch-id="currentBatch?.batch_id"
        :available-categories="availableCategories"
        @retranslate-clicked="handleRetranslate"
      />
      </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import CategorySelector from './CategorySelector.vue';
import BatchHistoryList from './BatchHistoryList.vue'; // 导入新组件
import { useI18n } from 'vue-i18n';
import { stylePresets } from '../utils/stylePresets.js';

const { t: $t } = useI18n();
const uploadRef = ref(null);
const historyListRef = ref(null); // 新增：用于引用历史列表组件
const fileList = ref([]);
const submitting = ref(false);
const currentBatch = ref(null);
const statusTimer = ref(null);
const refreshing = ref(false);

    const form = ref({
      source_lang: 'auto',
  target_lang: 'ja',
      style_preset: '',
      style_instruction: '',
  category_ids: [],
  engine: 'deepseek',
});

    const sourceLangOptions = [
  { value: 'auto', label: 'auto' }, { value: 'zh', label: 'zh' },
  { value: 'en', label: 'en' }, { value: 'ja', label: 'ja' }, { value: 'ko', label: 'ko' },
];
const targetLangOptions = sourceLangOptions.filter(opt => opt.value !== 'auto');
const acceptedFileTypes = '.docx,.pptx,.xlsx,.txt,.md';

    const terminologyOptions = ref({
      categories_enabled: false,
  max_categories_per_translation: 10,
});
const availableCategories = ref([]);

const canSubmit = computed(() => fileList.value.length > 0 && form.value.source_lang && form.value.target_lang);

    const progressPercentage = computed(() => {
  if (!currentBatch.value) return 0;
  return Math.round((currentBatch.value.completed / currentBatch.value.total) * 100);
});

    const progressStatus = computed(() => {
  if (!currentBatch.value) return '';
  if (currentBatch.value.failed > 0) return 'exception';
  if (currentBatch.value.completed === currentBatch.value.total) return 'success';
  return '';
});

    const selectedCategoryNames = computed(() => {
  if (!form.value.category_ids || !availableCategories.value) return [];
  const map = new Map(availableCategories.value.map(c => [c.id, c.name]));
  return form.value.category_ids.map(id => map.get(id)).filter(Boolean);
});

    const swapLanguages = () => {
      if (form.value.source_lang !== 'auto') {
    [form.value.source_lang, form.value.target_lang] = [form.value.target_lang, form.value.source_lang];
      }
};

    const handleFileChange = (file, uploadFileList) => {
      if (uploadFileList.length > 100) {
    ElMessage.warning('最多只能上传100个文件');
    uploadFileList.pop();
    return;
  }
  const allowedTypes = acceptedFileTypes.split(',');
  const fileExt = '.' + file.name.split('.').pop().toLowerCase();
      if (!allowedTypes.includes(fileExt)) {
    ElMessage.error(`不支持的文件类型: ${fileExt}`);
    // 从列表中移除无效文件
    fileList.value = uploadFileList.filter(f => f.uid !== file.uid);
    return;
  }
  fileList.value = uploadFileList;
};

    const handleFileRemove = (file, uploadFileList) => {
  fileList.value = uploadFileList;
};

    const handleCategoryChange = (categories) => {
  form.value.category_ids = categories;
};

// 新增：处理重新翻译事件
const handleRetranslate = (historyItem) => {
  form.value.source_lang = historyItem.source_lang;
  form.value.target_lang = historyItem.target_lang;
  form.value.style_preset = historyItem.engine_params?.style_preset || '';
  form.value.style_instruction = historyItem.engine_params?.style_instruction || '';
  form.value.category_ids = historyItem.term_category_ids || [];
  ElMessage.success('翻译配置已加载，请重新选择文件并提交。');
  window.scrollTo(0, 0); // 滚动到页面顶部
};

    const submitBatch = async () => {
  if (!canSubmit.value) return;

  submitting.value = true;
  try {
    const formData = new FormData();
    formData.append('source_lang', form.value.source_lang);
    formData.append('target_lang', form.value.target_lang);
    formData.append('style_preset', form.value.style_preset);
    formData.append('style_instruction', form.value.style_instruction);
    if (form.value.category_ids.length > 0) {
      formData.append('category_ids', JSON.stringify(form.value.category_ids));
    }
    fileList.value.forEach(file => {
      formData.append('files', file.raw);
    });
    if (currentBatch.value?.batch_id) {
      formData.append('batch_id', currentBatch.value.batch_id);
    }

    const token = localStorage.getItem('token');
        const response = await fetch('/api/batch/submit', {
          method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });

        if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '提交失败');
        }

    const result = await response.json();
    
    if (!currentBatch.value || !currentBatch.value.batch_id) {
        currentBatch.value = {
          batch_id: result.batch_id,
          total: result.items.length,
          completed: 0,
          failed: 0,
        tokens: result.tokens || 0,
      };
      startStatusMonitoring(result.batch_id);
    } else {
      await loadBatchStatus(currentBatch.value.batch_id);
    }

    ElMessage.success('批量翻译任务已提交，开始监控进度...');
    fileList.value = [];
    uploadRef.value.clearFiles();
    
    // 触发现已分离的子组件刷新历史
    if (historyListRef.value) {
      historyListRef.value.refreshBatchHistory();
    }
        
      } catch (error) {
    ElMessage.error(error.message || '提交失败');
      } finally {
    submitting.value = false;
      }
};

    const startStatusMonitoring = (batchId) => {
  saveBatchStatus(batchId);
  if (statusTimer.value) clearInterval(statusTimer.value);
  
  loadBatchStatus(batchId); // 立即获取一次
      
      statusTimer.value = setInterval(async () => {
        try {
      const status = await loadBatchStatus(batchId);
      if (status && (status.completed + status.failed === status.total) && status.total > 0) {
        clearInterval(statusTimer.value);
        statusTimer.value = null;
        ElMessage.success('批量翻译任务已完成！');
        localStorage.removeItem('transai_current_batch_id');
        if (historyListRef.value) {
          historyListRef.value.refreshBatchHistory();
            }
          }
        } catch (error) {
      // 监控时出错，可以考虑停止或忽略
    }
  }, 5000); // 每5秒检查一次
};

const cancelBatchTranslation = async () => {
  if (!currentBatch.value?.batch_id) return;
  try {
    await ElMessageBox.confirm('确定要取消当前的批量翻译任务吗？', '确认取消', { type: 'warning' });
    if (statusTimer.value) clearInterval(statusTimer.value);
    const token = localStorage.getItem('token');
    await fetch(`/api/batch/cancel/${currentBatch.value.batch_id}`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
    currentBatch.value = null;
    localStorage.removeItem('transai_current_batch_id');
    ElMessage.success('批量翻译任务已取消');
    if (historyListRef.value) {
      historyListRef.value.refreshBatchHistory();
    }
  } catch (error) {
    // User cancelled
  }
};

const pruneBatchItems = async () => {
  if (!currentBatch.value?.batch_id) return;
  try {
    const token = localStorage.getItem('token');
    await fetch(`/api/batch/prune/${currentBatch.value.batch_id}`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
    await loadBatchStatus(currentBatch.value.batch_id);
    ElMessage.success('已清理已完成或无效的项');
  } catch (e) {
    ElMessage.error('清理失败');
  }
};

    const saveBatchStatus = (batchId) => {
  if (batchId) localStorage.setItem('transai_current_batch_id', batchId);
};

    const restoreBatchStatus = async () => {
  const savedBatchId = localStorage.getItem('transai_current_batch_id');
      if (savedBatchId) {
        try {
      await loadBatchStatus(savedBatchId);
      ElMessage.info('已恢复之前的批量翻译任务状态');
        } catch (error) {
      localStorage.removeItem('transai_current_batch_id');
        }
      }
};

    const loadBatchStatus = async (batchId) => {
      try {
    const token = localStorage.getItem('token');
    const response = await fetch(`/api/batch/${batchId}`, { headers: { 'Authorization': `Bearer ${token}` } });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const status = await response.json();
    currentBatch.value = status;
    if ((status.completed + status.failed) < status.total) {
      if (!statusTimer.value) startStatusMonitoring(batchId);
    }
    return status;
      } catch (error) {
    currentBatch.value = null; // 如果获取失败，则清除状态
    localStorage.removeItem('transai_current_batch_id');
    if (statusTimer.value) clearInterval(statusTimer.value);
    throw error;
  }
};

    const loadTerminologyOptions = async () => {
      try {
    const token = localStorage.getItem('token');
    const response = await fetch('/api/terminology/categories', { headers: { 'Authorization': `Bearer ${token}` } });
        if (response.ok) {
      const categories = await response.json();
      availableCategories.value = categories;
      terminologyOptions.value.categories_enabled = categories.length > 0;
        }
      } catch (error) {
    console.error('Failed to load terminology categories:', error);
      }
};

    const refreshBatchStatus = async () => {
      if (!currentBatch.value?.batch_id) {
    ElMessage.warning('没有可刷新的批量任务');
    return;
      }
  refreshing.value = true;
      try {
    await loadBatchStatus(currentBatch.value.batch_id);
    ElMessage.success('状态已刷新');
      } catch (error) {
    ElMessage.error('刷新状态失败: ' + error.message);
      } finally {
    refreshing.value = false;
  }
};

onMounted(async () => {
  await restoreBatchStatus();
  await loadTerminologyOptions();
});

    onUnmounted(() => {
  if (statusTimer.value) clearInterval(statusTimer.value);
});

</script>

<style scoped>
.batch-translator {
  max-width: 900px;
  margin: 0 auto;
  padding: 10px 20px 20px 20px;
  border: 1px solid #e4e7ed;
  border-radius: 10px;
  background-color: #fff;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}

.translation-options-row {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
  white-space: nowrap;
}

.compact-select {
  width: 110px;
}

.category-selection-row {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
}

.upload-section {
  margin-bottom: 20px;
}

.submit-section {
  text-align: center;
  padding: 20px;
}

.submit-tip {
  color: #666;
  font-size: 14px;
  margin-top: 10px;
}

.async-note {
  color: #999;
  font-size: 12px;
  margin-top: 10px;
}

.swap-button-container {
  display: flex;
  align-items: center;
}

@media (max-width: 768px) {
  .translation-options-row {
    flex-direction: column;
    align-items: stretch;
  }
  .option-item {
    width: 100%;
  }
  .compact-select {
    width: 100%;
  }
}

.history-wrapper {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background-color: #fff;
  padding: 8px 8px 4px 8px;
  margin-top: 10px;
}
</style>
