<template>
  <div class="document-translator-container">
    <div class="translation-container">
      <!-- 翻译选项行 - 更紧凑的布局 -->
      <div class="translation-options-row">
      <!-- AI引擎选择器 -->
      <div class="option-item">
        <span class="option-label">{{$t('doc.engine')}}</span>
        <EngineSelector 
          v-model="selectedEngine" 
          @change="handleEngineChange"
          :disabled="isUploading"
          class="compact-engine-selector"
        />
      </div>
      
      <!-- 源语言选择 -->
      <div class="option-item">
        <span class="option-label">{{$t('doc.sourceLang')}}</span>
        <el-select v-model="sourceLang" :placeholder="$t('doc.selectSource')" class="compact-select">
          <el-option v-for="item in sourceLangOptions" :key="item.value" :label="$t('lang.'+item.value)" :value="item.value"></el-option>
        </el-select>
      </div>
      
      <!-- 语言交换按钮 -->
      <div class="swap-button-container">
        <el-button @click="swapLanguages" icon="el-icon-sort" circle size="small"></el-button>
      </div>
      
      <!-- 目标语言选择 -->
      <div class="option-item">
        <span class="option-label">{{$t('doc.targetLang')}}</span>
        <el-select v-model="targetLang" :placeholder="$t('doc.selectTarget')" class="compact-select">
          <el-option v-for="item in targetLangOptions" :key="item.value" :label="$t('lang.'+item.value)" :value="item.value"></el-option>
        </el-select>
      </div>
      <!-- 风格预设（文档翻译） -->
      <div class="option-item" style="min-width:160px;">
        <span class="option-label">{{$t('style.presetLabel')}}</span>
        <el-tooltip :content="$t('style.help')" placement="top">
          <el-select v-model="stylePreset" clearable :placeholder="$t('style.presetPh')" class="compact-select" :disabled="isUploading" style="width:140px;">
            <el-option v-for="preset in stylePresets" :key="preset.value" :label="preset.label" :value="preset.value" />
          </el-select>
        </el-tooltip>
      </div>
      
      
    </div>
    
    <!-- 术语分类选择器 -->
    <div class="category-selection-row" v-if="terminologyOptions.categories_enabled">
      <CategorySelector
        v-model="selectedCategories"
        :categories="availableCategories"
        :max-categories="terminologyOptions.max_categories_per_translation"
        :disabled="isUploading"
        @change="handleCategoryChange"
      />
      <div v-if="selectedCategories.length" style="margin-top:8px;color:#666;font-size:13px;">
        {{$t('doc.selectedCategories')}}：
        <span>{{ selectedCategoryNames.join('、') }}</span>
      </div>
    </div>
    
    <!-- 文件上传区域 -->
    <el-upload ref="upload" class="upload-demo" drag :auto-upload="false" :on-change="handleFileChange" action="#" :limit="1" :on-exceed="handleFileExceed">
      <i class="el-icon-upload"></i>
      <div class="el-upload__text">{{$t('doc.dragHere')}} <em>{{$t('doc.clickToUpload')}}</em></div>
      <div class="el-upload__tip" slot="tip">{{$t('doc.supports')}}</div>
    </el-upload>
    
    <!-- 自定义指令（文档翻译） -->
    <el-form label-width="100px" style="margin-top:10px;">
      <el-form-item :label="$t('style.customLabel')">
        <el-input v-model="styleInstruction" type="textarea" :rows="2" placeholder="例如：这段翻译是商务用途，请用商务风格。" :disabled="isUploading" maxlength="300" show-word-limit />
      </el-form-item>
    </el-form>
    <!-- 翻译按钮 -->
    <div class="bottom-bar">
      <el-button type="primary" @click="startTranslation" :disabled="fileList.length === 0 || isUploading" class="translate-button">
        {{ isUploading ? $t('doc.uploading') : $t('doc.start') }}
      </el-button>
    </div>
    
    <!-- 任务进度显示区域 - 移到文件上传区域下方 -->
    <div v-if="task.id" class="task-status-container">
      <div class="task-header">
        <h4>{{$t('doc.taskStatus')}}</h4>
      </div>
      <div class="task-info">
        <div class="task-row">
          <span class="task-label">{{$t('doc.taskId')}}</span>
          <span class="task-value">{{ task.id }}</span>
        </div>
        <div class="task-row" v-if="task.filename">
          <span class="task-label">{{$t('doc.fileName')}}</span>
          <span class="task-value">{{ task.filename }}</span>
        </div>
        <div class="task-row">
          <span class="task-label">{{$t('doc.status')}}</span>
          <el-tag :type="getStatusType(task.status)" size="small">{{ task.status }}</el-tag>
          <span v-if="task.duration" class="task-duration">{{$t('doc.duration')}} {{ task.duration }}{{$t('doc.seconds')}}</span>
        </div>
      </div>
      
      <!-- 进度条 -->
      <el-progress 
        :percentage="task.status === 'completed' ? 100 : (task.status === 'processing' ? 50 : 0)" 
        :status="task.status === 'failed' ? 'exception' : (task.status === 'completed' ? 'success' : '')"
        class="task-progress"
      ></el-progress>
      
      <!-- 上传进度 -->
      <el-progress v-if="isUploading" :percentage="uploadProgress" class="upload-progress"></el-progress>
      
      <!-- 下载链接 -->
      <div v-if="task.resultPath" class="download-section">
        <el-button type="success" size="small" @click="downloadResult(task.resultPath)">
          <i class="el-icon-download"></i> {{$t('doc.downloadResult')}}
        </el-button>
      </div>
    </div>
    
    <!-- 文档翻译历史记录 -->
    <div class="document-history-section">
      <div class="history-header">
        <h3>{{$t('doc.historyTitle')}}</h3>
        <div style="display:flex;gap:8px;align-items:center;">
          <el-select v-model="historyFilterCategories" multiple clearable collapse-tags :placeholder="$t('doc.filterByCategory')" style="min-width:240px;">
            <el-option v-for="c in availableCategories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-button size="small" @click="refreshDocumentHistory" :loading="loadingHistory">
            {{$t('common.refresh')}}
          </el-button>
        </div>
      </div>
      
      <div v-if="documentHistory.length === 0" class="no-history">
        <el-empty :description="$t('doc.noHistory')" :image-size="80"></el-empty>
      </div>
      
      <div v-else class="history-list">
        <div 
          v-for="item in filteredDocumentHistory" 
          :key="item.task_id" 
          class="history-item"
          :class="{ 'current-task': item.task_id === task.id }"
        >
          <div class="history-content">
            <div class="history-meta">
              <span class="engine-tag">{{ item.engine }}</span>
              <span class="lang-info">{{ item.source_lang }} → {{ item.target_lang }}</span>
              <span class="username" v-if="item.username">{{$t('common.user')}}: {{ item.username }}</span>
              <span class="time">{{ formatTime(item.create_time) }}</span>
            </div>
            <div class="history-details">
              <div class="filename">
                <strong>{{$t('doc.fileName')}}：</strong>
                <span>{{ item.file_name }}</span>
              </div>
              <div v-if="item.engine_params" style="margin:6px 0;">
                <el-button size="small" @click="toggleParams(item.task_id)">{{$t('common.engineParams')}}</el-button>
                <div v-if="showParams[item.task_id]" style="margin-top:6px;background:#f6f8fa;padding:8px;border-radius:4px;font-size:12px;">
                  <pre style="white-space:pre-wrap;word-break:break-word;">{{ formatEngineParams(item.engine_params) }}</pre>
                </div>
              </div>
              <div class="term-categories" v-if="item.term_category_ids && item.term_category_ids.length">
                <strong>{{$t('doc.termCategories')}}：</strong>
                <el-tag size="small" style="margin-right:4px;" v-for="cid in item.term_category_ids" :key="cid">{{ categoryName(cid) }}</el-tag>
              </div>
              <div class="status-info">
                <strong>{{$t('doc.status')}}：</strong>
                <el-tag :type="getStatusType(item.status)" size="small">{{ item.status }}</el-tag>
                <span v-if="item.duration" class="duration">{{$t('doc.duration')}} {{ item.duration }}{{$t('doc.seconds')}}</span>
                <span v-if="item.token_count !== null" class="duration">Tokens: {{ item.token_count }}</span>
                <span v-if="item.source_file_size !== null" class="duration">{{$t('doc.source')}}: {{ (item.source_file_size/1024).toFixed(1) }}KB</span>
                <span v-if="item.target_file_size !== null" class="duration">{{$t('doc.target')}}: {{ (item.target_file_size/1024).toFixed(1) }}KB</span>
              </div>
            </div>
          </div>
          <div class="history-actions">
            <el-button 
              v-if="item.result_path" 
              size="small" 
              type="success"
              @click="downloadResult(item.result_path)"
            >
              {{$t('doc.download')}}
            </el-button>
            <el-button 
              size="small" 
              @click="loadHistoryItem(item)"
            >
              {{$t('doc.retranslate')}}
            </el-button>
            <el-button size="small" type="danger" @click="removeLocalHistory(item)">{{$t('common.delete')}}</el-button>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { ElMessage } from 'element-plus';
import EngineSelector from './EngineSelector.vue';
import CategorySelector from './CategorySelector.vue';
import { stylePresets } from '../utils/stylePresets.js';

const API_BASE_URL = '';

export default {
  name: 'DocumentTranslator',
  components: {
    EngineSelector,
    CategorySelector
  },
  data() {
    const sourceLangOptions = [
      { value: 'auto', label: 'auto' },
      { value: 'zh', label: 'zh' },
      { value: 'en', label: 'en' },
      { value: 'ja', label: 'ja' },
      { value: 'ko', label: 'ko' },
    ];
    const targetLangOptions = sourceLangOptions.filter(opt => opt.value !== 'auto');
    
    return {
      sourceLang: 'auto',
      targetLang: 'ja',
      strategy: 'ooxml_direct',
      selectedEngine: 'deepseek',  // 使用新的引擎选择器
      fileList: [],
      isUploading: false,
      uploadProgress: 0,
      sourceLangOptions,
      targetLangOptions,
      strategyOptions: [],
      // 新增：文档风格
      stylePreset: '',
      styleInstruction: '',
      task: {
        id: null,
        status: '',
        resultPath: null,
        duration: null,
        filename: ''
      },
      polling: null,
      // API状态相关
      apiStatus: 'unknown', // 'unknown', 'healthy', 'unhealthy', 'checking'
      checkingStatus: false,
      documentHistory: [], // 新增：文档翻译历史记录
      loadingHistory: false, // 新增：加载历史记录时的loading状态
      historyFilterCategories: [],
      frontendDeletePermanent: true,
      // 术语分类相关
      selectedCategories: [],
      terminologyOptions: {
        categories_enabled: false,
        max_categories_per_translation: 10
      },
      availableCategories: [],
      showParams: {},
      stylePresets: stylePresets
    };
  },
  computed: {
    statusIcon() {
      const icons = {
        unknown: 'el-icon-question',
        healthy: 'el-icon-success',
        unhealthy: 'el-icon-error',
        checking: 'el-icon-loading'
      };
      return icons[this.apiStatus];
    },
    statusText() {
      const texts = {
        unknown: '未知',
        healthy: '正常',
        unhealthy: '异常',
        checking: '检查中'
      };
      return texts[this.apiStatus];
    },
    selectedCategoryNames(){
      if(!this.selectedCategories || !this.availableCategories) return []
      const map = new Map(this.availableCategories.map(c => [c.id, c.name]))
      return this.selectedCategories.map(id => map.get(id)).filter(Boolean)
    },
    filteredDocumentHistory(){
      if(!this.historyFilterCategories || this.historyFilterCategories.length === 0) return this.documentHistory
      const set = new Set(this.historyFilterCategories)
      return (this.documentHistory||[]).filter(it => Array.isArray(it.term_category_ids) && it.term_category_ids.some(id => set.has(id)))
    }
  },
  // API状态检查已移除，使用全局API状态管理器
  mounted() {
    this.refreshDocumentHistory();
    // 策略列表选择已移除，内部自动按文件类型选择
    // 术语分类配置与可选分类
    this.loadTerminologyOptions();
    this.loadAvailableCategories();
    // 仅管理员查询删除模式配置，避免普通用户403报错
    try{
      const raw = localStorage.getItem('user');
      const u = raw ? JSON.parse(raw) : null;
      if(u && u.role === 'admin'){
        this.loadDeleteMode();
      }
    }catch{}
  },
  methods: {
    
    // 加载术语选项
    async loadTerminologyOptions() {
      try {
        const token = localStorage.getItem('token');
        const resp = await fetch('/api/terminology/options', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} });
        if (resp.ok) {
          const options = await resp.json();
          this.terminologyOptions = {
            categories_enabled: !!options.categories_enabled,
            max_categories_per_translation: Number(options.max_categories_per_translation || 10)
          };
        }
      } catch (e) {
        console.error('Failed to load terminology options:', e);
      }
    },
    // 加载可用分类
    async loadAvailableCategories() {
      try {
        const token = localStorage.getItem('token');
        const resp = await fetch('/api/terminology/categories', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} });
        if (resp.ok) {
          this.availableCategories = await resp.json();
        } else {
          this.availableCategories = [];
        }
      } catch (e) {
        console.error('Failed to load categories:', e);
        this.availableCategories = [];
      }
    },
    handleFileChange(file) {
      this.fileList = [file];
    },
    handleFileExceed(files) {
      this.$refs.upload.clearFiles();
      const file = files[0];
      this.fileList = [file];
      this.$refs.upload.handleStart(file);
    },
    swapLanguages() {
      if (this.sourceLang === 'auto') return;
      [this.sourceLang, this.targetLang] = [this.targetLang, this.sourceLang];
    },
    startTranslation() {
      if (this.fileList.length === 0) {
        ElMessage.warning(this.$t('doc.selectFileWarn'));
        return;
      }

      const file = this.fileList[0];
      const fileExtension = file.name.split('.').pop().toLowerCase();
      
      // 根据文件类型自动选择翻译策略
      let strategy = this.strategy;
      if (fileExtension === 'txt' || fileExtension === 'md') {
        strategy = 'text_direct';  // 文本文件使用文本翻译器
      } else if (fileExtension === 'docx') {
        strategy = 'ooxml_direct';  // Word文档
      } else if (fileExtension === 'xlsx') {
        strategy = 'ooxml_direct';  // Excel文档
      } else if (fileExtension === 'pptx') {
        strategy = 'ooxml_direct';  // PowerPoint文档
      }

      const formData = new FormData();
      formData.append('file', file.raw);
      formData.append('source_lang', this.sourceLang);
      formData.append('target_lang', this.targetLang);
      formData.append('strategy', strategy);
      formData.append('engine', this.selectedEngine);
      // 术语分类：以JSON字符串传递到后端
      if (this.selectedCategories && this.selectedCategories.length > 0) {
        formData.append('category_ids', JSON.stringify(this.selectedCategories));
      }
      // 文档风格：仅在非空时传
      if (this.stylePreset) formData.append('style_preset', this.stylePreset);
      if (this.styleInstruction) formData.append('style_instruction', this.styleInstruction);

      this.isUploading = true;
      this.uploadProgress = 0;
      this.task = { id: null, status: '', resultPath: null, duration: null, filename: '' };

      // 模拟上传进度
      const progressInterval = setInterval(() => {
        if (this.uploadProgress < 90) {
          this.uploadProgress += 10;
        }
      }, 200);

      axios.post(`/api/translate/document`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      .then(response => {
        clearInterval(progressInterval);
        this.uploadProgress = 100;
        
        if (response.data && response.data.task_id) {
          this.task = {
            id: response.data.task_id,
            status: 'pending',
            resultPath: null,
            duration: null,
            filename: file.name
          };
          ElMessage.success('文件上传成功，开始翻译');
          this.pollTaskStatus();
        } else {
          throw new Error('Invalid response format: missing task_id');
        }
      })
      .catch(error => {
        clearInterval(progressInterval);
        this.uploadProgress = 0;
        
        let errorMessage = '上传失败';
        if (error.response?.status === 409) {
          errorMessage = error.response?.data?.detail || '文档历史已达上限，请先删除历史记录';
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail;
        } else if (error.message) {
          errorMessage = error.message;
        }
        
        ElMessage.error(errorMessage);
        
        // 重置任务状态
        this.task = { id: null, status: '', resultPath: null, duration: null, filename: '' };
      })
      .finally(() => {
        this.isUploading = false;
      });
    },
    
    handleEngineChange(engine) {
      this.selectedEngine = engine;
      ElMessage.info(`已选择 ${engine} 翻译引擎`);
    },
    handleCategoryChange(categories) {
      this.selectedCategories = categories;
    },
    pollTaskStatus() {
      this.polling = setInterval(() => {
        if (!this.task.id) {
          clearInterval(this.polling);
          return;
        }
        
        axios.get(`/api/translate/result/${this.task.id}`)
          .then(response => {
            const data = response.data;
            
            this.task.status = data.status;
            
            if (data.status === 'completed' || data.status === 'success') {
              if (data.result && data.result.translated_file_path) {
                this.task.resultPath = `${API_BASE_URL}${data.result.translated_file_path}`;
              } else if (data.result && data.result.message) {
              }
              
              if (data.result && data.result.duration) {
                this.task.duration = data.result.duration;
              }
              
              clearInterval(this.polling);
              ElMessage.success('翻译完成！');
              // 任务完成后自动刷新文档历史
              this.refreshDocumentHistory();
            } else if (data.status === 'failed') {
              const errorMsg = data.error || '翻译失败';
              ElMessage.error('翻译失败: ' + errorMsg);
              clearInterval(this.polling);
              // 失败也刷新一次，便于看到失败记录
              this.refreshDocumentHistory();
            } else if (data.status === 'pending' || data.status === 'processing') {
            }
          })
          .catch((error) => {
          });
      }, 3000);
    },
    // API状态检查已移除，使用全局API状态管理器
    refreshDocumentHistory() {
      this.loadingHistory = true;
      // 仅展示普通文档记录，排除批量记录
      axios.get(`/api/history/document?normal_only=true&page=1&limit=100`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      .then(response => {
        const data = response.data
        this.documentHistory = Array.isArray(data) ? data : (data.items || [])
        ElMessage.success('文档翻译历史刷新成功！');
        this.loadAvailableCategories();
      })
      .catch(error => {
        ElMessage.error('刷新文档翻译历史失败');
      })
      .finally(() => {
        this.loadingHistory = false;
      });
    },
    loadHistoryItem(item) {
      this.sourceLang = item.source_lang;
      this.targetLang = item.target_lang;
      this.strategy = item.strategy;
      this.selectedEngine = item.engine;
      this.fileList = [{ name: item.file_name, raw: null }]; // 模拟上传文件
      this.startTranslation(); // 重新开始翻译
    },
    async removeLocalHistory(item){
      if(this.frontendDeletePermanent){
        const token = localStorage.getItem('token')
        const id = item.task_id || item.id
        if(!id){ this.$message.error('记录无效，无法删除'); return }
        fetch(`${API_BASE_URL}/api/history/${id}?type=document`, { method:'DELETE', headers:{ 'Authorization': `Bearer ${token}` } })
          .then(r => {
            if(!r.ok) throw new Error('删除失败')
            // 刷新以展示记录仍保留、文件链接已清空
            this.refreshDocumentHistory()
            this.$message.success('文件已清理（记录保留）')
          })
          .catch(()=>{ this.$message.error('删除失败') })
      } else {
        const id = item.task_id || item.id
        this.documentHistory = this.documentHistory.filter(h => (h.task_id || h.id) !== id)
        this.$message.success('已从列表移除（不影响后端历史）')
      }
    },
    downloadResult(url) {
      // 构建完整的下载URL，指向后端
      let downloadUrl;
      if (url.startsWith('http')) {
        // 如果已经是完整URL，直接使用
        downloadUrl = url;
      } else {
        // 如果是相对路径，构建完整的后端URL
        const backendUrl = import.meta.env.VITE_API_BASE_URL || (window.location.origin.includes(':5173') ? 'http://localhost:8000' : window.location.origin);
        downloadUrl = `${backendUrl}${url.startsWith('/') ? url : `/${url}`}`;
      }
      
      // 创建下载链接
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.target = '_blank';
      link.download = ''; // 触发下载而不是在新窗口打开
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
    categoryName(id){
      if(!this.availableCategories || !Array.isArray(this.availableCategories)) return id
      const found = this.availableCategories.find(c => c.id === id)
      return found ? found.name : id
    },
    formatTime(timestamp) {
      if (!timestamp) return '';
      const date = new Date(timestamp);
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day} ${hours}:${minutes}`;
    },
    toggleParams(id){
      this.showParams[id] = !this.showParams[id]
    },
    formatEngineParams(v){
      try{ return typeof v === 'string' ? v : JSON.stringify(v, null, 2) }catch{ return String(v) }
    },
    getStatusType(status) {
      switch (status) {
        case 'pending':
          return 'info';
        case 'processing':
          return 'warning';
        case 'completed':
          return 'success';
        case 'failed':
          return 'danger';
        default:
          return 'info';
      }
    },
    async loadDeleteMode(){
      try{
        const token = localStorage.getItem('token')
        const hdrs = token ? { 'Authorization': `Bearer ${token}` } : {}
        const resp = await fetch('/api/admin/settings?category=history', { headers: hdrs })
        if(resp.ok){
          const items = await resp.json()
          const row = items.find(i => i.key === 'frontend_delete_permanent')
          if(row){ this.frontendDeletePermanent = String(row.value).toLowerCase() === 'true' }
        }
      } catch{}
    }
  },
  beforeUnmount() {
    clearInterval(this.polling);
  }
};
</script>

<style scoped>
.document-translator-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 10px 20px 20px 20px;
}

.translation-container {
  padding: 20px;
  background-color: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  margin-bottom: 20px;
}

.translation-options-row {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: auto;
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

.compact-engine-selector {
  width: 110px;
}

.swap-button-container {
  margin: 0 8px;
}

.category-selection-row {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
}

.upload-demo {
  margin-bottom: 20px;
}

.bottom-bar {
  text-align: center;
  margin-bottom: 20px;
}

.translate-button {
  padding: 12px 30px;
  font-size: 16px;
}

/* 任务状态容器样式 */
.task-status-container {
  margin: 20px 0;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.task-header {
  margin-bottom: 15px;
  border-bottom: 2px solid #409eff;
  padding-bottom: 8px;
}

.task-header h4 {
  margin: 0;
  color: #409eff;
  font-size: 16px;
  font-weight: 600;
}

.task-info {
  margin-bottom: 15px;
}

.task-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  gap: 10px;
}

.task-label {
  font-weight: 600;
  color: #333;
  min-width: 80px;
}

.task-value {
  color: #666;
  font-family: monospace;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.task-duration {
  margin-left: 10px;
  color: #666;
  font-size: 13px;
}

.task-progress {
  margin-bottom: 15px;
}

.upload-progress {
  margin-bottom: 15px;
}

.download-section {
  text-align: center;
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #e4e7ed;
}

.document-history-section {
  margin-top: 20px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  background-color: #fafafa;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.history-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  background-color: #f0f9eb; /* 浅绿色背景 */
}

.history-item.current-task {
  border: 2px solid #409eff; /* 蓝色边框 */
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
}

.history-meta .engine-tag,
.history-meta .strategy-tag {
  background-color: #ecf5ff;
  color: #409eff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.history-meta .lang-info {
  color: #909399;
  margin: 0 5px;
}

.history-meta .username {
  color: #555;
  margin: 0 5px;
  font-size: 12px;
}

.history-details {
  font-size: 14px;
  color: #333;
}

.history-details .filename {
  margin-bottom: 5px;
}

.history-details .status-info {
  display: flex;
  align-items: center;
}

.history-details .status-info .duration {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.history-actions {
  display: flex;
  gap: 8px;
}

.history-actions .el-button {
  padding: 5px 10px;
  font-size: 12px;
}

.no-history {
  text-align: center;
  padding: 40px 0;
}

.no-history .el-empty {
  margin-top: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .translation-options-row {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
  }

  .option-item {
    min-width: auto;
    width: 100%;
  }

  .compact-select,
  .compact-engine-selector {
    width: 100%;
  }

  .swap-button-container {
    align-self: center;
    margin: 10px 0;
  }
}

@media (max-width: 480px) {
  .document-translator-container {
    padding: 10px;
  }
  
  .translation-options-row {
    gap: 10px;
  }
}
</style>
