<template>
  <div class="engine-management">
    <div class="page-header">
      <h2>翻译引擎管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <i class="fas fa-plus"></i>
        添加引擎
      </el-button>
    </div>

    <!-- 引擎列表 -->
    <div class="engine-list">
      <el-table
        :data="engines"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="display_name" label="引擎名称" width="150" />
        <el-table-column prop="engine_name" label="标识符" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusTagType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100">
          <template #default="scope">
            <el-tag :type="getPriorityTagType(scope.row.priority)">
              {{ scope.row.priority }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rate_limit" label="速率限制" width="120">
          <template #default="scope">
            {{ scope.row.rate_limit }}/分钟
          </template>
        </el-table-column>
        <el-table-column prop="cost_per_token" label="成本" width="100">
          <template #default="scope">
            {{ scope.row.cost_per_token.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="is_default" label="默认引擎" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.is_default" type="success">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="viewEngine(scope.row)">
              <i class="fas fa-eye"></i>
              查看
            </el-button>
            <el-button size="small" type="primary" @click="editEngine(scope.row)">
              <i class="fas fa-edit"></i>
              编辑
            </el-button>
            <el-button 
              size="small" 
              :type="scope.row.status === 'active' ? 'warning' : 'success'"
              @click="toggleEngineStatus(scope.row)"
            >
              <i :class="scope.row.status === 'active' ? 'fas fa-pause' : 'fas fa-play'"></i>
              {{ scope.row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteEngine(scope.row)"
              :disabled="scope.row.is_default"
            >
              <i class="fas fa-trash"></i>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 创建引擎对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="添加翻译引擎"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="120px"
      >
        <el-form-item label="引擎标识符" prop="engine_name">
          <el-input v-model="createForm.engine_name" placeholder="请输入引擎标识符" />
          <div class="form-tip">唯一标识符，如：deepseek、kimi、youdao</div>
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="createForm.display_name" placeholder="请输入显示名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入引擎描述"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="createForm.status" placeholder="请选择状态">
            <el-option label="活跃" value="active" />
            <el-option label="维护中" value="maintenance" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number
            v-model="createForm.priority"
            :min="0"
            :max="100"
            placeholder="数字越小优先级越高"
          />
        </el-form-item>
        <el-form-item label="速率限制" prop="rate_limit">
          <el-input-number
            v-model="createForm.rate_limit"
            :min="1"
            :max="10000"
            placeholder="每分钟请求数"
          />
        </el-form-item>
        <el-form-item label="每Token成本" prop="cost_per_token">
          <el-input-number
            v-model="createForm.cost_per_token"
            :min="0"
            :precision="6"
            :step="0.000001"
            placeholder="每token的成本"
          />
        </el-form-item>
        <el-form-item label="支持的语言" prop="supported_languages">
          <el-select
            v-model="createForm.supported_languages"
            multiple
            filterable
            allow-create
            placeholder="请选择或输入支持的语言"
          >
            <el-option label="中文" value="zh" />
            <el-option label="英文" value="en" />
            <el-option label="日文" value="ja" />
            <el-option label="韩文" value="ko" />
            <el-option label="法文" value="fr" />
            <el-option label="德文" value="de" />
            <el-option label="西班牙文" value="es" />
            <el-option label="俄文" value="ru" />
          </el-select>
        </el-form-item>
        <el-form-item label="功能特性" prop="features">
          <el-select
            v-model="createForm.features"
            multiple
            filterable
            allow-create
            placeholder="请选择或输入功能特性"
          >
            <el-option label="文本翻译" value="text_translation" />
            <el-option label="文档翻译" value="document_translation" />
            <el-option label="JSON格式" value="json_format" />
            <el-option label="批量翻译" value="batch_translation" />
            <el-option label="术语管理" value="terminology" />
          </el-select>
        </el-form-item>
        <el-form-item label="设为默认引擎" prop="is_default">
          <el-switch v-model="createForm.is_default" />
        </el-form-item>
        <el-form-item label="API配置" prop="api_config">
          <el-input
            v-model="createForm.api_config_text"
            type="textarea"
            :rows="4"
            placeholder="请输入JSON格式的API配置"
            @input="updateApiConfig"
          />
          <div class="form-tip">JSON格式，包含API密钥、端点等信息</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="createEngine" :loading="createLoading">
            创建
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑引擎对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑翻译引擎"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="120px"
      >
        <el-form-item label="引擎标识符" prop="engine_name">
          <el-input v-model="editForm.engine_name" disabled />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="editForm.display_name" placeholder="请输入显示名称" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入引擎描述"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="editForm.status" placeholder="请选择状态">
            <el-option label="活跃" value="active" />
            <el-option label="维护中" value="maintenance" />
            <el-option label="禁用" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number
            v-model="editForm.priority"
            :min="0"
            :max="100"
            placeholder="数字越小优先级越高"
          />
        </el-form-item>
        <el-form-item label="速率限制" prop="rate_limit">
          <el-input-number
            v-model="editForm.rate_limit"
            :min="1"
            :max="10000"
            placeholder="每分钟请求数"
          />
        </el-form-item>
        <el-form-item label="每Token成本" prop="cost_per_token">
          <el-input-number
            v-model="editForm.cost_per_token"
            :min="0"
            :precision="6"
            :step="0.000001"
            placeholder="每token的成本"
          />
        </el-form-item>
        <el-form-item label="支持的语言" prop="supported_languages">
          <el-select
            v-model="editForm.supported_languages"
            multiple
            filterable
            allow-create
            placeholder="请选择或输入支持的语言"
          >
            <el-option label="中文" value="zh" />
            <el-option label="英文" value="en" />
            <el-option label="日文" value="ja" />
            <el-option label="韩文" value="ko" />
            <el-option label="法文" value="fr" />
            <el-option label="德文" value="de" />
            <el-option label="西班牙文" value="es" />
            <el-option label="俄文" value="ru" />
          </el-select>
        </el-form-item>
        <el-form-item label="功能特性" prop="features">
          <el-select
            v-model="editForm.features"
            multiple
            filterable
            allow-create
            placeholder="请选择或输入功能特性"
          >
            <el-option label="文本翻译" value="text_translation" />
            <el-option label="文档翻译" value="document_translation" />
            <el-option label="JSON格式" value="json_format" />
            <el-option label="批量翻译" value="batch_translation" />
            <el-option label="术语管理" value="terminology" />
          </el-select>
        </el-form-item>
        <el-form-item label="设为默认引擎" prop="is_default">
          <el-switch v-model="editForm.is_default" />
        </el-form-item>
        <el-form-item label="API配置" prop="api_config">
          <el-input
            v-model="editForm.api_config_text"
            type="textarea"
            :rows="4"
            placeholder="请输入JSON格式的API配置"
            @input="updateEditApiConfig"
          />
          <div class="form-tip">JSON格式，包含API密钥、端点等信息</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditDialog = false">取消</el-button>
          <el-button type="primary" @click="updateEngine" :loading="editLoading">
            更新
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 引擎详情对话框 -->
    <el-dialog
      v-model="showViewDialog"
      title="引擎详情"
      width="700px"
    >
      <div v-if="selectedEngine" class="engine-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="引擎ID">{{ selectedEngine.id }}</el-descriptions-item>
          <el-descriptions-item label="引擎标识符">{{ selectedEngine.engine_name }}</el-descriptions-item>
          <el-descriptions-item label="显示名称">{{ selectedEngine.display_name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusTagType(selectedEngine.status)">
              {{ getStatusText(selectedEngine.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="getPriorityTagType(selectedEngine.priority)">
              {{ selectedEngine.priority }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="速率限制">{{ selectedEngine.rate_limit }}/分钟</el-descriptions-item>
          <el-descriptions-item label="每Token成本">{{ selectedEngine.cost_per_token.toFixed(6) }}</el-descriptions-item>
          <el-descriptions-item label="默认引擎">
            <el-tag v-if="selectedEngine.is_default" type="success">是</el-tag>
            <span v-else>否</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(selectedEngine.create_time) }}</el-descriptions-item>
          <el-descriptions-item label="最后更新">{{ formatTime(selectedEngine.update_time) }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ selectedEngine.description || '无描述' }}</el-descriptions-item>
          <el-descriptions-item label="支持的语言" :span="2">
            <el-tag v-for="lang in selectedEngine.supported_languages" :key="lang" style="margin-right: 5px;">
              {{ lang }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="功能特性" :span="2">
            <el-tag v-for="feature in selectedEngine.features" :key="feature" style="margin-right: 5px;">
              {{ feature }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="API配置" :span="2">
            <pre>{{ JSON.stringify(selectedEngine.api_config, null, 2) || '无配置' }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'EngineManagement',
  setup() {
    const loading = ref(false)
    const createLoading = ref(false)
    const editLoading = ref(false)
    const engines = ref([])
    
    // 对话框状态
    const showCreateDialog = ref(false)
    const showEditDialog = ref(false)
    const showViewDialog = ref(false)
    
    // 表单数据
    const createForm = reactive({
      engine_name: '',
      display_name: '',
      description: '',
      status: 'active',
      priority: 0,
      rate_limit: 100,
      cost_per_token: 0.0,
      supported_languages: [],
      features: [],
      is_default: false,
      api_config: {},
      api_config_text: ''
    })
    
    const editForm = reactive({
      id: null,
      engine_name: '',
      display_name: '',
      description: '',
      status: '',
      priority: 0,
      rate_limit: 100,
      cost_per_token: 0.0,
      supported_languages: [],
      features: [],
      is_default: false,
      api_config: {},
      api_config_text: ''
    })
    
    const selectedEngine = ref(null)
    
    // 表单验证规则
    const createRules = {
      engine_name: [
        { required: true, message: '请输入引擎标识符', trigger: 'blur' },
        { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
      ],
      display_name: [
        { required: true, message: '请输入显示名称', trigger: 'blur' },
        { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
      ],
      status: [
        { required: true, message: '请选择状态', trigger: 'change' }
      ],
      priority: [
        { required: true, message: '请输入优先级', trigger: 'blur' }
      ],
      rate_limit: [
        { required: true, message: '请输入速率限制', trigger: 'blur' }
      ]
    }
    
    const editRules = {
      display_name: [
        { required: true, message: '请输入显示名称', trigger: 'blur' },
        { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
      ],
      status: [
        { required: true, message: '请选择状态', trigger: 'change' }
      ],
      priority: [
        { required: true, message: '请输入优先级', trigger: 'blur' }
      ],
      rate_limit: [
        { required: true, message: '请输入速率限制', trigger: 'blur' }
      ]
    }
    
    // 表单引用
    const createFormRef = ref()
    const editFormRef = ref()
    
    // 获取引擎列表
    const fetchEngines = async () => {
      try {
        loading.value = true
        const response = await fetch('/api/admin/engines', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          engines.value = data
        } else {
          ElMessage.error('获取引擎列表失败')
        }
      } catch (error) {
        console.error('获取引擎列表错误:', error)
        ElMessage.error('获取引擎列表失败')
      } finally {
        loading.value = false
      }
    }
    
    // 创建引擎
    const createEngine = async () => {
      try {
        await createFormRef.value.validate()
        createLoading.value = true
        
        const response = await fetch('/api/admin/engines', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(createForm)
        })
        
        if (response.ok) {
          ElMessage.success('引擎创建成功')
          showCreateDialog.value = false
          resetCreateForm()
          fetchEngines()
        } else {
          const error = await response.json()
          ElMessage.error(error.detail || '引擎创建失败')
        }
      } catch (error) {
        console.error('创建引擎错误:', error)
        ElMessage.error('创建引擎失败')
      } finally {
        createLoading.value = false
      }
    }
    
    // 编辑引擎
    const editEngine = (engine) => {
      editForm.id = engine.id
      editForm.engine_name = engine.engine_name
      editForm.display_name = engine.display_name
      editForm.description = engine.description || ''
      editForm.status = engine.status
      editForm.priority = engine.priority
      editForm.rate_limit = engine.rate_limit
      editForm.cost_per_token = engine.cost_per_token
      editForm.supported_languages = engine.supported_languages || []
      editForm.features = engine.features || []
      editForm.is_default = engine.is_default
      editForm.api_config = engine.api_config || {}
      editForm.api_config_text = JSON.stringify(engine.api_config || {}, null, 2)
      showEditDialog.value = true
    }
    
    // 更新引擎
    const updateEngine = async () => {
      try {
        await editFormRef.value.validate()
        editLoading.value = true
        
        const response = await fetch(`/api/admin/engines/${editForm.id}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(editForm)
        })
        
        if (response.ok) {
          ElMessage.success('引擎更新成功')
          showEditDialog.value = false
          fetchEngines()
        } else {
          const error = await response.json()
          ElMessage.error(error.detail || '引擎更新失败')
        }
      } catch (error) {
        console.error('更新引擎错误:', error)
        ElMessage.error('更新引擎失败')
      } finally {
        editLoading.value = false
      }
    }
    
    // 删除引擎
    const deleteEngine = async (engine) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除引擎 "${engine.display_name}" 吗？此操作不可恢复。`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const response = await fetch(`/api/admin/engines/${engine.id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          ElMessage.success('引擎删除成功')
          fetchEngines()
        } else {
          const error = await response.json()
          ElMessage.error(error.detail || '引擎删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除引擎错误:', error)
          ElMessage.error('删除引擎失败')
        }
      }
    }
    
    // 切换引擎状态
    const toggleEngineStatus = async (engine) => {
      try {
        const response = await fetch(`/api/admin/engines/${engine.id}/toggle`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          ElMessage.success(data.message)
          fetchEngines()
        } else {
          ElMessage.error('切换引擎状态失败')
        }
      } catch (error) {
        console.error('切换引擎状态错误:', error)
        ElMessage.error('切换引擎状态失败')
      }
    }
    
    // 查看引擎详情
    const viewEngine = (engine) => {
      selectedEngine.value = engine
      showViewDialog.value = true
    }
    
    // 重置创建表单
    const resetCreateForm = () => {
      createForm.engine_name = ''
      createForm.display_name = ''
      createForm.description = ''
      createForm.status = 'active'
      createForm.priority = 0
      createForm.rate_limit = 100
      createForm.cost_per_token = 0.0
      createForm.supported_languages = []
      createForm.features = []
      createForm.is_default = false
      createForm.api_config = {}
      createForm.api_config_text = ''
      createFormRef.value?.resetFields()
    }
    
    // 更新API配置
    const updateApiConfig = () => {
      try {
        if (createForm.api_config_text.trim()) {
          createForm.api_config = JSON.parse(createForm.api_config_text)
        } else {
          createForm.api_config = {}
        }
      } catch (error) {
        // JSON解析错误时不更新
      }
    }
    
    const updateEditApiConfig = () => {
      try {
        if (editForm.api_config_text.trim()) {
          editForm.api_config = JSON.parse(editForm.api_config_text)
        } else {
          editForm.api_config = {}
        }
      } catch (error) {
        // JSON解析错误时不更新
      }
    }
    
    // 获取状态标签类型
    const getStatusTagType = (status) => {
      const types = {
        active: 'success',
        maintenance: 'warning',
        inactive: 'danger'
      }
      return types[status] || 'info'
    }
    
    // 获取状态文本
    const getStatusText = (status) => {
      const texts = {
        active: '活跃',
        maintenance: '维护中',
        inactive: '禁用'
      }
      return texts[status] || status
    }
    
    // 获取优先级标签类型
    const getPriorityTagType = (priority) => {
      if (priority <= 10) return 'success'
      if (priority <= 30) return 'warning'
      return 'danger'
    }
    
    // 格式化时间
    const formatTime = (time) => {
      return new Date(time).toLocaleString('zh-CN')
    }
    
    onMounted(() => {
      fetchEngines()
    })
    
    return {
      loading,
      createLoading,
      editLoading,
      engines,
      showCreateDialog,
      showEditDialog,
      showViewDialog,
      createForm,
      editForm,
      selectedEngine,
      createRules,
      editRules,
      createFormRef,
      editFormRef,
      fetchEngines,
      createEngine,
      editEngine,
      updateEngine,
      deleteEngine,
      toggleEngineStatus,
      viewEngine,
      resetCreateForm,
      updateApiConfig,
      updateEditApiConfig,
      getStatusTagType,
      getStatusText,
      getPriorityTagType,
      formatTime
    }
  }
}
</script>

<style scoped>
.engine-management {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  color: #2c3e50;
}

.engine-list {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.engine-detail {
  padding: 20px 0;
}

.form-tip {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
}

.dialog-footer {
  text-align: right;
}

pre {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }
}
</style>

