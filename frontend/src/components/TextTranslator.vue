<template>
  <div class="text-translator">
    <div class="translation-container">
      <!-- 翻译选项行 -->
      <div class="translation-options-row">
      <!-- AI引擎选择器 -->
      <div class="option-item">
        <span class="option-label">{{$t('text.engine')}}</span>
        <EngineSelector 
          v-model="selectedEngine" 
          @change="handleEngineChange"
          :disabled="translating"
          class="compact-engine-selector"
        />
      </div>
      
      <!-- 源语言选择 -->
      <div class="option-item">
        <span class="option-label">{{$t('text.sourceLang')}}</span>
        <el-select v-model="form.sourceLang" :placeholder="$t('text.selectSource')" :disabled="translating" class="compact-select">
          <el-option :label="$t('lang.zh')" value="zh"></el-option>
          <el-option :label="$t('lang.en')" value="en"></el-option>
          <el-option :label="$t('lang.ja')" value="ja"></el-option>
          <el-option :label="$t('lang.ko')" value="ko"></el-option>
          <el-option :label="$t('lang.auto')" value="auto"></el-option>
        </el-select>
      </div>
      
      <!-- 目标语言选择 -->
      <div class="option-item">
        <span class="option-label">{{$t('text.targetLang')}}</span>
        <el-select v-model="form.targetLang" :placeholder="$t('text.selectTarget')" :disabled="translating" class="compact-select">
          <el-option :label="$t('lang.zh')" value="zh"></el-option>
          <el-option :label="$t('lang.en')" value="en"></el-option>
          <el-option :label="$t('lang.ja')" value="ja"></el-option>
          <el-option :label="$t('lang.ko')" value="ko"></el-option>
        </el-select>
      </div>

      <!-- 风格预设 -->
      <div class="option-item" style="min-width:160px;">
        <span class="option-label">{{$t('style.presetLabel')}}</span>
        <el-tooltip :content="$t('style.help')" placement="top">
          <el-select v-model="stylePreset" clearable :placeholder="$t('style.presetPh')" class="compact-select" :disabled="translating" style="width:140px;">
            <el-option v-for="preset in stylePresets" :key="preset.value" :label="preset.label" :value="preset.value" />
          </el-select>
        </el-tooltip>
      </div>

      <!-- 启发式（仅聊天式引擎可用） -->
      <div class="option-item" v-if="supportsThinking">
        <span class="option-label">启发式</span>
        <el-tooltip content="开启后在支持的引擎上启用思维/推理模式，长句与复杂语义更稳，但可能略增时延与 tokens。" placement="top">
          <el-switch v-model="enableThinking" :disabled="translating" />
        </el-tooltip>
      </div>
    </div>
    
    <!-- 术语分类选择器 -->
    <div class="category-selection-row" v-if="terminologyOptions.categories_enabled">
      <CategorySelector
        v-model="selectedCategories"
        :categories="availableCategories"
        :max-categories="terminologyOptions.max_categories_per_translation"
        :disabled="translating"
        @change="handleCategoryChange"
      />
    </div>
    
    <div class="translation-content">
      <el-form :model="form" label-width="80px" class="translation-form">
        <el-form-item :label="$t('text.sourceText')">
          <el-input
            v-model="form.sourceText"
            type="textarea"
            :rows="6"
            :placeholder="$t('text.enterText')"
            :disabled="translating"
            maxlength="5000"
            show-word-limit
          ></el-input>
        </el-form-item>

        <!-- 自定义指令（影响风格） -->
        <el-form-item label="自定义指令">
          <el-input
            v-model="styleInstruction"
            type="textarea"
            :rows="2"
            placeholder="例如：这段翻译是商务用途，请用商务风格。"
            :disabled="translating"
            maxlength="300"
            show-word-limit
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            @click="translateText" 
            :loading="translating"
            :disabled="!form.sourceText.trim()"
          >
            {{ translating ? $t('text.translating') : $t('text.start') }}
          </el-button>
          <el-button @click="clearForm" :disabled="translating">{{$t('common.clear')}}</el-button>
        </el-form-item>
        
        <el-form-item :label="$t('text.result')" v-if="translationResult">
          <el-input
            v-model="translationResult"
            type="textarea"
            :rows="6"
            readonly
            :placeholder="$t('text.resultPlaceholder')"
          ></el-input>
          <div class="result-actions">
            <el-button size="small" @click="copyResult">{{$t('common.copy')}}</el-button>
            <el-button size="small" @click="clearResult">{{$t('common.clear')}}</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>
    
    <!-- 文本翻译历史记录 -->
    <div class="text-history-section">
      <div class="history-header">
        <h3>{{$t('text.historyTitle')}}</h3>
        <div style="display:flex;gap:8px;align-items:center;">
          <el-select v-model="historyFilterEngine" clearable placeholder="按引擎过滤" style="min-width:160px;">
            <el-option v-for="e in engineOptions" :key="e" :label="e" :value="e" />
          </el-select>
          <el-button size="small" @click="refreshTextHistory" :loading="loadingHistory">{{$t('common.refresh')}}</el-button>
        </div>
      </div>
      
      <div v-if="textHistory.length === 0" class="no-history">
        <el-empty :description="$t('text.noHistory')" :image-size="80"></el-empty>
      </div>
      
      <div v-else class="history-list">
        <div 
          v-for="item in filteredTextHistory" 
          :key="item.id" 
          class="history-item"
          :class="{ 'current-result': item.id === currentHistoryId }"
        >
          <div class="history-content">
            <div class="history-meta">
              <span class="engine-tag">{{ item.engine }}</span>
              <span class="lang-info">{{ item.source_lang }} → {{ item.target_lang }}</span>
              <span class="username" v-if="item.username">{{$t('common.user')}}: {{ item.username }}</span>
              <span class="time">{{ formatTime(item.create_time) }}</span>
              <span class="time" v-if="item.token_count !== null && item.token_count !== undefined">Tokens: {{ item.token_count }}</span>
              <span class="time" v-if="item.duration !== null && item.duration !== undefined">耗时: {{ Number(item.duration||0).toFixed(2) }}s</span>
            </div>
            <div class="history-texts">
              <div class="source-text">
                <strong>{{$t('text.source')}}：</strong>
                <span>{{ truncateText(item.source_text, 100) }}</span>
              </div>
              <div class="translated-text">
                <strong>{{$t('text.translation')}}：</strong>
                <span>{{ truncateText(item.translated_text, 100) }}</span>
              </div>
              <div v-if="item.engine_params" style="margin-top:6px;">
                <el-button size="mini" @click="toggleParams(item.id)">引擎参数</el-button>
                <div v-if="showParams[item.id]" style="margin-top:6px; background:#f6f8fa; padding:8px; border-radius:4px; font-size:12px;">
                  <pre style="white-space:pre-wrap;word-break:break-word;">{{ formatEngineParams(item.engine_params) }}</pre>
                </div>
              </div>
              <div class="term-categories" v-if="item.term_category_ids && item.term_category_ids.length">
                <strong>{{$t('text.termCategories')}}：</strong>
                <el-tag size="small" style="margin-right:4px;" v-for="cid in item.term_category_ids" :key="cid">{{ categoryName(cid) }}</el-tag>
              </div>
            </div>
          </div>
          <div class="history-actions">
            <el-button size="small" @click="copyHistoryText(item.translated_text)">{{$t('common.copy')}}</el-button>
            <el-button size="small" @click="loadHistoryItem(item)">{{$t('common.load')}}</el-button>
            <el-button size="small" type="danger" @click="deleteHistory(item)">{{$t('common.delete')}}</el-button>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script>
import EngineSelector from './EngineSelector.vue'
import CategorySelector from './CategorySelector.vue' // Added import for CategorySelector
import { stylePresets } from '../utils/stylePresets.js';

export default {
  name: 'TextTranslator',
  components: {
    EngineSelector,
    CategorySelector // Added CategorySelector to components
  },
  mounted() {
    this.refreshTextHistory()
    this.loadTerminologyOptions()
    this.loadAvailableCategories()
  },
  data() {
    return {
      selectedEngine: 'deepseek', // 默认选择的引擎
      form: {
        sourceLang: 'auto',
        targetLang: 'ja',
        sourceText: '',
        categories: [] // 术语分类ID列表
      },
      // 新增：风格与启发式
      stylePreset: '',
      styleInstruction: '',
      enableThinking: false,
      selectedCategories: [], // 选中的分类ID列表
      translating: false,
      translationResult: '',
      textHistory: [], // 存储文本翻译历史
      loadingHistory: false, // 加载历史记录时的loading状态
      // 历史
      historyFilterEngine: '',
      engineOptions: ['deepseek','qwen_plus','qwen3','tencent','kimi','youdao'],
      historyFilterCategories: [],
      currentHistoryId: null, // 当前加载的历史记录的ID
      terminologyOptions: { // 术语选项
        categories_enabled: false,
        max_categories_per_translation: 10
      },
      availableCategories: [], // 可用分类列表
      showParams: {},
      stylePresets: stylePresets
    }
  },
  methods: {
    // 加载术语选项
    async loadTerminologyOptions() {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/terminology/options', {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        })
        if (response.ok) {
          const options = await response.json()
          // 后端返回键为 categories_enabled / max_categories_per_translation
          this.terminologyOptions = {
            categories_enabled: !!options.categories_enabled,
            max_categories_per_translation: Number(options.max_categories_per_translation || 10)
          }
        }
      } catch (error) {
        console.error('Failed to load terminology options:', error)
      }
    },
    
    // 加载可用分类
    async loadAvailableCategories() {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/terminology/categories', {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        })
        if (response.ok) {
          this.availableCategories = await response.json()
        } else {
          // 未认证或无数据时，保证结构存在，避免 UI 条件判断失败
          this.availableCategories = []
        }
      } catch (error) {
        console.error('Failed to load categories:', error)
      }
    },
    
    // 翻译文本
    async translateText() {
      if (!this.form.sourceText.trim()) {
        this.$message.warning(this.$t('text.enterTextWarn'))
        return
      }
      
      this.translating = true
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/translate/text', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          },
          body: JSON.stringify({
            text: this.form.sourceText,
            source_lang: this.form.sourceLang,
            target_lang: this.form.targetLang,
            engine: this.selectedEngine,
            category_ids: this.form.categories, // 传递术语分类ID列表
            // 风格与启发式
            style_preset: this.stylePreset || undefined,
            style_instruction: this.styleInstruction || undefined,
            enable_thinking: this.supportsThinking ? this.enableThinking : false
          })
        })
        
        if (response.ok) {
          const result = await response.json()
          this.translationResult = result.translated_text
          this.$message.success(this.$t('text.done'))
          
          // 刷新历史记录
          this.refreshTextHistory()
        } else {
          const error = await response.json()
          this.$message.error(error.detail || this.$t('text.failed'))
        }
      } catch (error) {
        console.error('Translation error:', error)
        this.$message.error(this.$t('text.error'))
      } finally {
        this.translating = false
      }
    },
    
    handleEngineChange(engine) {
      this.selectedEngine = engine
    },
    toggleParams(id){
      this.showParams[id] = !this.showParams[id]
    },
    formatEngineParams(v){
      try{ return typeof v === 'string' ? v : JSON.stringify(v, null, 2) }catch{ return String(v) }
    },

    handleCategoryChange(categories) {
      this.selectedCategories = categories
      this.form.categories = categories
    },
    
    clearForm() {
      this.form.sourceText = ''
      this.form.categories = [] // Clear categories
      this.translationResult = ''
    },
    
    clearResult() {
      this.translationResult = ''
    },
    
    async copyResult() {
      if (this.translationResult) {
        try {
          await navigator.clipboard.writeText(this.translationResult)
          this.$message.success(this.$t('common.copied'))
        } catch (error) {
          // 降级方案
          const textArea = document.createElement('textarea')
          textArea.value = this.translationResult
          document.body.appendChild(textArea)
          textArea.select()
          document.execCommand('copy')
          document.body.removeChild(textArea)
          this.$message.success(this.$t('common.copied'))
        }
      }
    },

    // 保存翻译结果到历史记录
    saveToHistory(data) {
      const historyItem = {
        id: Date.now().toString(), // 临时ID，实际应该使用后端返回的ID
        engine: this.selectedEngine,
        source_lang: this.form.sourceLang,
        target_lang: this.form.targetLang,
        source_text: this.form.sourceText,
        translated_text: data.translated_text,
        token_count: data.tokens ?? null,
        duration: data.duration ?? null,
        create_time: new Date().toISOString()
      }
      this.textHistory.unshift(historyItem) // 添加到列表最前面
      this.currentHistoryId = historyItem.id
    },

    // 刷新文本翻译历史
    async refreshTextHistory() {
      this.loadingHistory = true
      try {
        const token = localStorage.getItem('token')
        const headers = {}
        if (token) {
          headers['Authorization'] = `Bearer ${token}`
        }
        
        const response = await fetch(`/api/history/text?mine_only=true`, {
          headers
        })

        if (response.ok) {
          const data = await response.json()
          this.textHistory = data
          this.$message.success(this.$t('text.historyRefreshed'))
          this.loadAvailableCategories()
        } else {
          const errorData = await response.json()
          this.$message.error(errorData.detail || this.$t('text.historyRefreshFailed'))
        }
      } catch (error) {
        console.error('Refresh history error:', error)
        this.$message.error(this.$t('text.historyRefreshError'))
      } finally {
        this.loadingHistory = false
      }
    },

    // 复制历史记录中的文本
    async copyHistoryText(text) {
      try {
        await navigator.clipboard.writeText(text)
        this.$message.success(this.$t('common.copied'))
      } catch (error) {
        // 降级方案
        const textArea = document.createElement('textarea')
        textArea.value = text
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        this.$message.success(this.$t('common.copied'))
      }
    },

    // 加载历史记录中的特定项
    loadHistoryItem(item) {
      this.form.sourceText = item.source_text
      this.form.sourceLang = item.source_lang
      this.form.targetLang = item.target_lang
      this.selectedEngine = item.engine
      this.form.categories = item.categories // Load categories from history
      this.translationResult = item.translated_text
      this.currentHistoryId = item.id
      this.$message.success(this.$t('text.loaded'))
    },

    deleteHistory(item) {
      const API_BASE_URL = window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : 'http://backend:8000'
      // 小历史中没有真实ID，这里仅本地移除；若需要等同后端删除，请在“历史记录”页执行
      // 可扩展：当加载自 /api/history/text 时，项会有真实 id，可调用后端删除
      if(item.id && String(item.id).length < 20){
        const token = localStorage.getItem('token')
        fetch(`${API_BASE_URL}/api/history/${item.id}?type=text`, { method:'DELETE', headers:{ 'Authorization': `Bearer ${token}` } })
          .then(r => { if(!r.ok) throw new Error('删除失败') })
          .catch(()=>{})
      }
      this.textHistory = this.textHistory.filter(h => h.id !== item.id)
      if (this.currentHistoryId === item.id) this.currentHistoryId = null
      this.$message.success('已从列表移除')
    },

    // 格式化时间戳
    formatTime(timestamp) {
      const date = new Date(timestamp)
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      return `${year}-${month}-${day} ${hours}:${minutes}`
    },

    // 截断文本，显示前n和后n个字符
    truncateText(text, length = 50) {
      if (text.length <= length * 2) {
        return text
      }
      const start = text.substring(0, length)
      const end = text.substring(text.length - length)
      return `${start}...${end}`
    },
    categoryName(id){
      if(!this.availableCategories || !Array.isArray(this.availableCategories)) return id
      const found = this.availableCategories.find(c => c.id === id)
      return found ? found.name : id
    }
  },
  computed: {
    filteredTextHistory(){
      const eng = (this.historyFilterEngine||'').trim()
      return (this.textHistory||[]).filter(it => !eng || (String(it.engine||'').toLowerCase() === eng.toLowerCase()))
    },
    supportsThinking(){
      const e = (this.selectedEngine||'').toLowerCase()
      return ['qwen_plus','deepseek'].includes(e)
    }
  }
}
</script>

<style scoped>
.text-translator {
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

.compact-engine-selector {
  width: 110px;
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

.translation-content {
  margin-top: 20px;
}

.translation-form {
  margin-top: 20px;
}

.result-actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
}

/* 历史记录样式 */
.text-history-section {
  margin-top: 30px;
  border-top: 1px solid #e4e7ed;
  padding-top: 20px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.history-header h3 {
  margin: 0;
  color: #333;
  font-size: 18px;
}

.no-history {
  text-align: center;
  padding: 40px 0;
}

.history-list {
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  margin-bottom: 10px;
  background-color: #fafafa;
  transition: all 0.3s ease;
}

.history-item:hover {
  background-color: #f0f0f0;
  border-color: #c0c4cc;
}

.history-item.current-result {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.history-content {
  flex: 1;
  margin-right: 15px;
}

.history-meta {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
  align-items: center;
}

.engine-tag {
  background-color: #409eff;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.lang-info {
  color: #666;
  font-size: 12px;
}

.username {
  color: #555;
  font-size: 12px;
}

.time {
  color: #999;
  font-size: 12px;
}

.history-texts {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.source-text, .translated-text {
  font-size: 14px;
  line-height: 1.4;
}

.source-text strong, .translated-text strong {
  color: #333;
  margin-right: 5px;
}

.history-actions {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 80px;
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

  .compact-engine-selector,
  .compact-select {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .text-translator {
    padding: 10px;
  }
  
  .translation-options-row {
    gap: 10px;
  }
  
  .result-actions {
    flex-direction: column;
  }
}
</style>
