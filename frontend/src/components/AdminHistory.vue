<template>
  <div class="admin-history-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane :label="$t('adminHistory.docTab')" name="doc">
        <div class="section">
          <div class="section-header">
            <div class="filters">
              <el-input v-model="docFilters.user" :placeholder="$t('adminHistory.filterByUser')" clearable size="small" style="width:160px;" />
              <el-select v-model="docFilters.status" clearable :placeholder="$t('common.status')" size="small" style="width:120px;">
                <el-option label="pending" value="pending" />
                <el-option label="processing" value="processing" />
                <el-option label="completed" value="completed" />
                <el-option label="failed" value="failed" />
              </el-select>
              <el-select v-model="docFilters.engine" clearable :placeholder="$t('doc.engine')" size="small" style="width:140px;">
                <el-option v-for="e in engines" :key="e" :label="e" :value="e" />
              </el-select>
              <el-select v-model="docFilters.categories" multiple clearable collapse-tags :placeholder="$t('doc.termCategories')" size="small" style="min-width:240px;">
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
              <el-select v-model="docSortBy" clearable placeholder="排序字段" size="small" style="width:140px;">
                <el-option v-for="opt in sortFieldOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
              </el-select>
              <el-select v-model="docSortOrder" clearable placeholder="顺序" size="small" style="width:110px;">
                <el-option label="降序" value="desc" />
                <el-option label="升序" value="asc" />
              </el-select>
              <el-button size="small" @click="refreshDocHistory" :loading="loadingDoc">{{ $t('common.refresh') }}</el-button>
            </div>
          </div>
          <el-table :data="filteredDocHistory" v-loading="loadingDoc" size="small" style="width:100%">
            <el-table-column :label="$t('adminHistory.time')" width="165">
              <template #default="scope">{{ formatDate(scope.row.create_time) }}</template>
            </el-table-column>
            <el-table-column prop="username" :label="$t('common.user')" width="120" />
            <el-table-column :label="$t('adminHistory.lang')" width="130">
              <template #default="scope">{{ scope.row.source_lang }} → {{ scope.row.target_lang }}</template>
            </el-table-column>
            <el-table-column :label="$t('adminHistory.engineStrategy')" width="180">
              <template #default="scope">{{ scope.row.engine }}｜{{ scope.row.strategy }}</template>
            </el-table-column>
            <el-table-column :label="$t('common.engineParams')" width="120">
              <template #default="scope">
                <el-popover placement="bottom" width="420" trigger="click">
                  <pre style="white-space:pre-wrap;word-break:break-word;font-size:12px;max-height:280px;overflow:auto;">{{ formatEngineParams(scope.row.engine_params) }}</pre>
                  <template #reference>
                    <el-button size="small">{{$t('common.view')}}</el-button>
                  </template>
                </el-popover>
              </template>
            </el-table-column>
            <el-table-column prop="file_name" :label="$t('doc.fileName')" min-width="220" />
            <el-table-column :label="$t('doc.termCategories')" min-width="200">
              <template #default="scope">
                <el-tag v-for="cid in (scope.row.term_category_ids||[])" :key="cid" size="small" style="margin-right:4px;">{{ categoryName(cid) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('adminHistory.sizeSourceTarget')" width="220">
              <template #default="scope">
                <span>
                  {{ $t('doc.source') }} {{ sizeWithBytes(scope.row.source_file_size) }}
                  <span v-if="scope.row.target_file_size">｜{{ $t('doc.target') }} {{ sizeWithBytes(scope.row.target_file_size) }}</span>
                </span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('adminHistory.textStats')" width="180">
              <template #default="scope">
                <span>
                  {{ $t('adminHistory.totalTexts') }}: {{ scope.row.total_texts ?? '-' }}｜{{ $t('adminHistory.translatedTexts') }}: {{ scope.row.translated_texts ?? '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="Qwen429" width="120">
              <template #default="scope">
                <span v-if="scope.row.engine==='qwen3'">429: {{ scope.row.qwen3_429 ?? 0 }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('adminHistory.charCount')" width="100">
              <template #default="scope">{{ scope.row.character_count ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="Tokens" width="100">
              <template #default="scope">{{ scope.row.token_count ?? '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('adminHistory.durationS')" width="100">
              <template #default="scope">{{ scope.row.duration ? Number(scope.row.duration).toFixed(2) : '-' }}</template>
            </el-table-column>
            <el-table-column :label="$t('adminHistory.download')" width="100">
              <template #default="scope">
                <el-button v-if="scope.row.result_path" type="success" size="small" @click="download(scope.row.result_path)">{{ $t('doc.download') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-container">
            <el-pagination
              background
              layout="prev, pager, next"
              :total="docTotalItems"
              :page-size="docPageSize"
              :current-page="docCurrentPage"
              @current-change="handleDocPageChange"
            ></el-pagination>
          </div>
        </div>
      </el-tab-pane>
      <el-tab-pane :label="$t('adminHistory.textTab')" name="text">
        <div class="section">
          <div class="section-header">
            <div class="filters">
              <el-input v-model="textFilters.user" :placeholder="$t('adminHistory.filterByUser')" clearable size="small" style="width:160px;" />
              <el-select v-model="textFilters.engine" clearable :placeholder="$t('doc.engine')" size="small" style="width:140px;">
                <el-option v-for="e in engines" :key="e" :label="e" :value="e" />
              </el-select>
              <el-select v-model="textFilters.categories" multiple clearable collapse-tags :placeholder="$t('doc.termCategories')" size="small" style="min-width:240px;">
                <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
              </el-select>
              <el-button size="small" @click="refreshTextHistory" :loading="loadingText">{{ $t('common.refresh') }}</el-button>
            </div>
          </div>
          <el-table :data="filteredTextHistory" v-loading="loadingText" size="small" style="width:100%">
            <el-table-column :label="$t('adminHistory.time')" width="165">
              <template #default="scope">{{ formatDate(scope.row.create_time) }}</template>
            </el-table-column>
            <el-table-column prop="username" :label="$t('common.user')" width="120" />
            <el-table-column :label="$t('adminHistory.lang')" width="130">
              <template #default="scope">{{ scope.row.source_lang }} → {{ scope.row.target_lang }}</template>
            </el-table-column>
            <el-table-column prop="engine" :label="$t('doc.engine')" width="120" />
            <el-table-column :label="$t('common.engineParams')" width="120">
              <template #default="scope">
                <el-popover placement="bottom" width="420" trigger="click">
                  <pre style="white-space:pre-wrap;word-break:break-word;font-size:12px;max-height:280px;overflow:auto;">{{ formatEngineParams(scope.row.engine_params) }}</pre>
                  <template #reference>
                    <el-button size="small">{{$t('common.view')}}</el-button>
                  </template>
                </el-popover>
              </template>
            </el-table-column>
            <el-table-column :label="$t('doc.termCategories')" min-width="220">
              <template #default="scope">
                <el-tag v-for="cid in (scope.row.term_category_ids||[])" :key="cid" size="small" style="margin-right:4px;">{{ categoryName(cid) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('adminHistory.srcDst')" min-width="360">
              <template #default="scope">
                <div class="text-pair">
                  <div class="text-src" :title="scope.row.source_text">{{ truncate(scope.row.source_text) }}</div>
                  <div class="text-dst" :title="scope.row.translated_text">{{ truncate(scope.row.translated_text) }}</div>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
export default {
  name: 'AdminHistory',
  data(){
    return {
      activeTab: 'doc',
      loadingDoc: false,
      loadingText: false,
      docHistory: [],
      textHistory: [],
      categories: [],
      engines: ['deepseek','tencent','kimi','youdao','qwen3','qwen_plus'],
      docFilters: { user:'', status:'', engine:'', categories: [] },
      textFilters: { user:'', engine:'', categories: [] },
      // Pagination state for doc history
      docCurrentPage: 1,
      docPageSize: 10,
      docTotalItems: 0,
      // Sorting
      docSortBy: 'create_time',
      docSortOrder: 'desc',
      sortFieldOptions: [
        { value: 'create_time', label: '创建时间' },
        { value: 'token_count', label: 'Tokens' },
        { value: 'duration', label: '耗时' },
        { value: 'source_file_size', label: '源文件大小' },
        { value: 'target_file_size', label: '目标文件大小' },
      ],
    }
  },
  computed: {
    filteredDocHistory(){
      const name = (this.docFilters.user||'').trim().toLowerCase()
      const status = this.docFilters.status
      const engine = this.docFilters.engine
      const cats = new Set(this.docFilters.categories||[])
      // Filtering is now done on the current page's data
      return (this.docHistory || []).filter(it => {
        if(name && !(String(it.username||'').toLowerCase().includes(name))) return false
        if(status && it.status !== status) return false
        if(engine && it.engine !== engine) return false
        if(cats.size>0){
          const arr = Array.isArray(it.term_category_ids)? it.term_category_ids: []
          if(!arr.some(id => cats.has(id))) return false
        }
        return true
      })
    },
    filteredTextHistory(){
      const name = (this.textFilters.user||'').trim().toLowerCase()
      const engine = this.textFilters.engine
      const cats = new Set(this.textFilters.categories||[])
      return (this.textHistory||[]).filter(it => {
        if(name && !(String(it.username||'').toLowerCase().includes(name))) return false
        if(engine && it.engine !== engine) return false
        if(cats.size>0){
          const arr = Array.isArray(it.term_category_ids)? it.term_category_ids: []
          if(!arr.some(id => cats.has(id))) return false
        }
        return true
      })
    }
  },
  mounted(){
    this.refreshDocHistory()
    this.refreshTextHistory()
    this.loadCategories()
  },
  methods: {
    handleDocPageChange(page) {
      this.docCurrentPage = page;
      this.refreshDocHistory();
    },
    formatDate(ts){
      if(!ts) return ''
      const d = new Date(ts)
      const y = d.getFullYear()
      const m = String(d.getMonth()+1).padStart(2,'0')
      const day = String(d.getDate()).padStart(2,'0')
      const hh = String(d.getHours()).padStart(2,'0')
      const mm = String(d.getMinutes()).padStart(2,'0')
      return `${y}-${m}-${day} ${hh}:${mm}`
    },
    sizeWithBytes(bytes){
      if(typeof bytes !== 'number' || isNaN(bytes)) return '-'
      const kb = (bytes/1024).toFixed(1)
      return `${bytes}B(${kb}KB)`
    },
    async refreshDocHistory(){
      try{
        this.loadingDoc = true
        const token = localStorage.getItem('token')
        const params = new URLSearchParams({
          include_all: 'true',
          page: String(this.docCurrentPage),
          limit: String(this.docPageSize),
        })
        if (this.docFilters.status) params.set('status', this.docFilters.status)
        if (this.docFilters.engine) params.set('engine', this.docFilters.engine)
        if (this.docFilters.user) params.set('username', this.docFilters.user.trim())
        if (this.docSortBy) params.set('sortBy', this.docSortBy)
        if (this.docSortOrder) params.set('sortOrder', this.docSortOrder)
        const url = `/api/history/document?${params.toString()}`;
        const resp = await fetch(url, { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
        if(resp.ok){ 
          const data = await resp.json();
          this.docHistory = data.items;
          this.docTotalItems = data.total;
        }
      } finally { this.loadingDoc = false }
    },
    async refreshTextHistory(){
      try{
        this.loadingText = true
        const token = localStorage.getItem('token')
        const resp = await fetch('/api/history/text?include_all=true', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
        if(resp.ok){ this.textHistory = await resp.json() }
      } finally { this.loadingText = false }
    },
    async loadCategories(){
      try{
        const token = localStorage.getItem('token')
        const resp = await fetch('/api/terminology/categories', { headers: token ? { 'Authorization': `Bearer ${token}` } : {} })
        if(resp.ok){ this.categories = await resp.json() }
      } catch{}
    },
    categoryName(id){
      const found = this.categories.find(c => c.id === id)
      return found ? found.name : id
    },
    statusType(s){
      return s==='completed' ? 'success' : (s==='failed' ? 'danger' : (s==='processing' ? 'warning' : 'info'))
    },
    truncate(t){
      if(!t) return ''
      const s = String(t)
      return s.length>120 ? (s.slice(0,80)+'…'+s.slice(-30)) : s
    },
    download(url){
      const backend = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      const link = document.createElement('a')
      link.href = url.startsWith('http') ? url : `${backend}${url.startsWith('/')?url:'/'+url}`
      link.target = '_blank'
      link.download = ''
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    },
    formatEngineParams(v){
      try{ return typeof v === 'string' ? v : JSON.stringify(v, null, 2) }catch{ return String(v) }
    }
  }
}
</script>

<style scoped>
.admin-history-container{ padding: 10px; }
.section{ background:#fff; border:1px solid #e4e7ed; border-radius:6px; padding:12px; }
.section-header{ display:flex; justify-content:flex-end; align-items:center; margin-bottom:8px; }
.filters{ display:flex; gap:8px; align-items:center; }
.text-pair{ display:flex; flex-direction:column; gap:6px; }
.text-src{ color:#666; font-size:12px; }
.text-dst{ color:#333; font-size:12px; }
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>


