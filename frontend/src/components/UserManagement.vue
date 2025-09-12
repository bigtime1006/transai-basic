<template>
  <div class="user-management">
    <div class="page-header">
      <h2>{{ $t('users.title') }}</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <i class="fas fa-plus"></i>
        {{ $t('users.create') }}
      </el-button>
    </div>

    <!-- 搜索和筛选 -->
    <div class="search-filters">
      <el-row :gutter="20">
        <el-col :span="8">
          <el-input
            v-model="searchQuery"
            :placeholder="$t('users.searchPh')"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <i class="fas fa-search"></i>
            </template>
          </el-input>
        </el-col>
        <el-col :span="6">
          <el-select v-model="roleFilter" :placeholder="$t('users.roleFilter')" clearable @change="handleSearch">
            <el-option :label="$t('users.roleAdmin')" value="admin" />
            <el-option :label="$t('users.roleModerator')" value="moderator" />
            <el-option :label="$t('users.roleUser')" value="user" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="statusFilter" :placeholder="$t('users.statusFilter')" clearable @change="handleSearch">
            <el-option :label="$t('users.active')" :value="true" />
            <el-option :label="$t('users.inactive')" :value="false" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="info" @click="refreshUsers">
            <i class="fas fa-sync-alt"></i>
            {{ $t('common.refresh') }}
          </el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 用户列表 -->
    <div class="user-table">
      <el-table
        :data="filteredUsers"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" :label="$t('users.username')" width="150" />
        <el-table-column prop="email" :label="$t('users.email')" width="200" />
        <el-table-column prop="role" :label="$t('users.role')" width="100">
          <template #default="scope">
            <el-tag :type="getRoleTagType(scope.row.role)">
              {{ getRoleText(scope.row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="$t('common.status')" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status ? 'success' : 'danger'">
              {{ scope.row.status ? $t('users.active') : $t('users.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_verified" :label="$t('users.verified')" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_verified ? 'success' : 'warning'">
              {{ scope.row.is_verified ? $t('users.verifiedYes') : $t('users.verifiedNo') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" :label="$t('users.createdAt')" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_login" :label="$t('users.lastLogin')" width="180">
          <template #default="scope">
            {{ scope.row.last_login ? formatTime(scope.row.last_login) : $t('profile.never') }}
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="180" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="viewUser(scope.row)">
              <i class="fas fa-eye"></i>
              {{ $t('common.view') }}
            </el-button>
            <el-button size="small" type="primary" @click="editUser(scope.row)">
              <i class="fas fa-edit"></i>
              {{ $t('common.edit') }}
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteUser(scope.row)"
              :disabled="scope.row.id === currentUserId"
            >
              <i class="fas fa-trash"></i>
              {{ $t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalUsers"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 创建用户对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      :title="$t('users.create')"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="100px"
      >
        <el-form-item :label="$t('users.username')" prop="username">
          <el-input v-model="createForm.username" :placeholder="$t('users.enterUsername')" />
        </el-form-item>
        <el-form-item :label="$t('users.email')" prop="email">
          <el-input v-model="createForm.email" :placeholder="$t('users.enterEmail')" />
        </el-form-item>
        <el-form-item :label="$t('users.password')" prop="password">
          <el-input
            v-model="createForm.password"
            type="password"
            :placeholder="$t('users.enterPassword')"
            show-password
          />
        </el-form-item>
        <el-form-item :label="$t('users.role')" prop="role">
          <el-select v-model="createForm.role" :placeholder="$t('users.selectRole')">
            <el-option :label="$t('users.roleUser')" value="user" />
            <el-option :label="$t('users.roleModerator')" value="moderator" />
            <el-option :label="$t('users.roleAdmin')" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="createUser" :loading="createLoading">
            {{ $t('common.create') }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑用户对话框 -->
    <el-dialog
      v-model="showEditDialog"
      :title="$t('users.edit')"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="100px"
      >
        <el-form-item :label="$t('users.username')" prop="username">
          <el-input v-model="editForm.username" :placeholder="$t('users.enterUsername')" />
        </el-form-item>
        <el-form-item :label="$t('users.email')" prop="email">
          <el-input v-model="editForm.email" :placeholder="$t('users.enterEmail')" />
        </el-form-item>
        <el-form-item :label="$t('users.role')" prop="role">
          <el-select v-model="editForm.role" :placeholder="$t('users.selectRole')">
            <el-option :label="$t('users.roleUser')" value="user" />
            <el-option :label="$t('users.roleModerator')" value="moderator" />
            <el-option :label="$t('users.roleAdmin')" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('common.status')" prop="status">
          <el-switch
            v-model="editForm.status"
            :active-text="$t('users.active')"
            :inactive-text="$t('users.inactive')"
          />
        </el-form-item>
        <el-form-item :label="$t('users.verified')" prop="is_verified">
          <el-switch
            v-model="editForm.is_verified"
            :active-text="$t('users.verifiedYes')"
            :inactive-text="$t('users.verifiedNo')"
          />
        </el-form-item>
        <el-divider>账户信息</el-divider>
        <el-form-item :label="$t('users.createdAt')">
          <span>{{ editMeta.create_time ? formatTime(editMeta.create_time) : '-' }}</span>
        </el-form-item>
        <el-form-item :label="$t('users.lastLogin')">
          <span>{{ editMeta.last_login ? formatTime(editMeta.last_login) : $t('profile.never') }}</span>
        </el-form-item>

        <el-divider>重置密码</el-divider>
        <el-form-item :label="$t('users.newPassword')">
          <el-input v-model="editPwd.new_password" type="password" placeholder="至少8位，含大小写与数字" />
        </el-form-item>
        <el-form-item :label="$t('users.confirmNewPassword')">
          <el-input v-model="editPwd.confirm_password" type="password" />
        </el-form-item>
        <div style="text-align:right;margin-bottom:8px;">
          <el-button type="warning" :loading="resetLoading" @click="submitResetInEdit">{{ $t('users.resetPassword') }}</el-button>
        </div>

        <el-divider>配额</el-divider>
        <div style="margin-bottom:8px;">
          <el-button size="small" @click="fetchQuotas(editForm.id)">{{ $t('users.refreshQuotas') }}</el-button>
        </div>
        <el-table :data="quotas" v-loading="quotasLoading" size="small" style="width:100%">
          <el-table-column prop="quota_type" :label="$t('users.quotaType')" width="120" />
          <el-table-column prop="limit_value" :label="$t('users.quotaLimit')" width="100" />
          <el-table-column prop="used_value" :label="$t('users.quotaUsed')" width="100" />
          <el-table-column :label="$t('users.quotaActive')" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success':'info'">{{ scope.row.is_active? $t('common.yes'):$t('common.no') }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reset_date" :label="$t('users.quotaReset')">
            <template #default="scope">{{ scope.row.reset_date ? formatTime(scope.row.reset_date) : '-' }}</template>
          </el-table-column>
        </el-table>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditDialog = false">{{ $t('common.cancel') }}</el-button>
          <el-button type="primary" @click="updateUser" :loading="editLoading">
            {{ $t('common.update') }}
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 用户详情对话框 -->
    <el-dialog
      v-model="showViewDialog"
      title="用户详情"
      width="600px"
    >
      <div v-if="selectedUser" class="user-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="用户ID">{{ selectedUser.id }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ selectedUser.username }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ selectedUser.email || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="角色">
            <el-tag :type="getRoleTagType(selectedUser.role)">
              {{ getRoleText(selectedUser.role) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="selectedUser.status ? 'success' : 'danger'">
              {{ selectedUser.status ? '活跃' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="验证状态">
            <el-tag :type="selectedUser.is_verified ? 'success' : 'warning'">
              {{ selectedUser.is_verified ? '已验证' : '未验证' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(selectedUser.create_time) }}</el-descriptions-item>
          <el-descriptions-item label="最后登录">
            {{ selectedUser.last_login ? formatTime(selectedUser.last_login) : '从未登录' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'UserManagement',
  setup() {
    const loading = ref(false)
    const createLoading = ref(false)
    const editLoading = ref(false)
    const users = ref([])
    const totalUsers = ref(0)
    const currentPage = ref(1)
    const pageSize = ref(20)
    
    // 对话框状态
    const showCreateDialog = ref(false)
    const showEditDialog = ref(false)
    const showViewDialog = ref(false)
    
    // 搜索和筛选
    const searchQuery = ref('')
    const roleFilter = ref('')
    const statusFilter = ref('')
    
    // 表单数据
    const createForm = reactive({
      username: '',
      email: '',
      password: '',
      role: 'user'
    })
    
    const editForm = reactive({
      id: null,
      username: '',
      email: '',
      role: '',
      status: true,
      is_verified: false
    })
    const editMeta = reactive({ create_time: null, last_login: null })
    const editPwd = reactive({ new_password:'', confirm_password:'' })
    const resetLoading = ref(false)
    const quotas = ref([])
    const quotasLoading = ref(false)
    
    const selectedUser = ref(null)
    const currentUserId = ref(null) // 当前登录用户ID
    
    // 表单验证规则
    const createRules = {
      username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
      ],
      email: [
        { required: true, message: '请输入邮箱', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
      ],
      password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, message: '密码长度不能少于 6 个字符', trigger: 'blur' }
      ],
      role: [
        { required: true, message: '请选择角色', trigger: 'change' }
      ]
    }
    
    const editRules = {
      username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
      ],
      email: [
        { required: true, message: '请输入邮箱', trigger: 'blur' },
        { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
      ],
      role: [
        { required: true, message: '请选择角色', trigger: 'change' }
      ]
    }
    
    // 表单引用
    const createFormRef = ref()
    const editFormRef = ref()
    
    // 计算属性：过滤后的用户列表
    const filteredUsers = computed(() => {
      return users.value
    })
    
    // 获取用户列表
    const fetchUsers = async () => {
      try {
        loading.value = true
        const params = new URLSearchParams({
          skip: (currentPage.value - 1) * pageSize.value,
          limit: pageSize.value
        });
        if (searchQuery.value) {
          params.append('search', searchQuery.value);
        }
        if (roleFilter.value) {
          params.append('role', roleFilter.value);
        }
        if (statusFilter.value !== '' && statusFilter.value !== null) {
          params.append('status', statusFilter.value);
        }

        const response = await fetch(`/api/admin/users?${params.toString()}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          const data = await response.json()
          users.value = data.users
          totalUsers.value = data.total
        } else {
          ElMessage.error('获取用户列表失败')
        }
      } catch (error) {
        console.error('获取用户列表错误:', error)
        ElMessage.error('获取用户列表失败')
      } finally {
        loading.value = false
      }
    }
    
    // 创建用户
    const createUser = async () => {
      try {
        await createFormRef.value.validate()
        createLoading.value = true
        
        const response = await fetch('/api/admin/users', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(createForm)
        })
        
        if (response.ok) {
          ElMessage.success('用户创建成功')
          showCreateDialog.value = false
          resetCreateForm()
          fetchUsers()
        } else {
          const error = await response.json()
          ElMessage.error(error.detail || '用户创建失败')
        }
      } catch (error) {
        console.error('创建用户错误:', error)
        ElMessage.error('创建用户失败')
      } finally {
        createLoading.value = false
      }
    }
    
    // 编辑用户
    const editUser = (user) => {
      editForm.id = user.id
      editForm.username = user.username
      editForm.email = user.email || ''
      editForm.role = user.role
      editForm.status = user.status
      editForm.is_verified = user.is_verified
      editMeta.create_time = user.create_time
      editMeta.last_login = user.last_login
      editPwd.new_password = ''
      editPwd.confirm_password = ''
      showEditDialog.value = true
      fetchQuotas(user.id)
    }
    
    // 更新用户
    const updateUser = async () => {
      try {
        await editFormRef.value.validate()
        editLoading.value = true
        
        const response = await fetch(`/api/admin/users/${editForm.id}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(editForm)
        })
        
        if (response.ok) {
          ElMessage.success('用户更新成功')
          showEditDialog.value = false
          fetchUsers()
        } else {
          const error = await response.json()
          ElMessage.error(error.detail || '用户更新失败')
        }
      } catch (error) {
        console.error('更新用户错误:', error)
        ElMessage.error('更新用户失败')
      } finally {
        editLoading.value = false
      }
    }
    
    // 删除用户
    const deleteUser = async (user) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const response = await fetch(`/api/admin/users/${user.id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })
        
        if (response.ok) {
          ElMessage.success('用户删除成功')
          fetchUsers()
        } else {
          const error = await response.json()
          ElMessage.error(error.detail || '用户删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除用户错误:', error)
          ElMessage.error('删除用户失败')
        }
      }
    }
    
    // 查看用户详情
    const viewUser = (user) => {
      selectedUser.value = user
      showViewDialog.value = true
    }

    const submitResetInEdit = async () => {
      if(!editForm.id) return
      if(editPwd.new_password !== editPwd.confirm_password){ return ElMessage.error('两次输入的新密码不一致') }
      try{
        resetLoading.value = true
        const resp = await fetch(`/api/users/admin/users/${editForm.id}/reset-password`, {
          method:'POST',
          headers:{ 'Content-Type':'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
          body: JSON.stringify({ new_password: editPwd.new_password })
        })
        if(!resp.ok){ const e = await resp.json(); throw new Error(e.detail||'重置失败') }
        ElMessage.success(this.$t('users.passwordResetDone'))
        editPwd.new_password = ''
        editPwd.confirm_password = ''
      }catch(e){ ElMessage.error(e.message||'重置失败') }
      finally{ resetLoading.value = false }
    }

    const fetchQuotas = async (userId) => {
      if(!userId) return
      try{
        quotasLoading.value = true
        const resp = await fetch(`/api/admin/users/${userId}/quotas`, { headers:{ 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
        if(resp.ok){ quotas.value = await resp.json() }
      } finally { quotasLoading.value = false }
    }
    
    // 重置创建表单
    const resetCreateForm = () => {
      createForm.username = ''
      createForm.email = ''
      createForm.password = ''
      createForm.role = 'user'
      createFormRef.value?.resetFields()
    }
    
    // 搜索处理
    const handleSearch = () => {
      currentPage.value = 1
      fetchUsers()
    }
    
    // 刷新用户列表
    const refreshUsers = () => {
      fetchUsers()
    }
    
    // 分页处理
    const handleSizeChange = (val) => {
      pageSize.value = val
      currentPage.value = 1
      fetchUsers()
    }
    
    const handleCurrentChange = (val) => {
      currentPage.value = val
      fetchUsers()
    }
    
    // 获取角色标签类型
    const getRoleTagType = (role) => {
      const types = {
        admin: 'danger',
        moderator: 'warning',
        user: 'info'
      }
      return types[role] || 'info'
    }
    
    // 获取角色文本
    const getRoleText = (role) => {
      const texts = {
        admin: '管理员',
        moderator: '版主',
        user: '普通用户'
      }
      return texts[role] || role
    }
    
    // 格式化时间
    const formatTime = (time) => {
      return new Date(time).toLocaleString('zh-CN')
    }
    
    onMounted(() => {
      fetchUsers()
      // 获取当前用户ID（从localStorage或token中解析）
      // 这里需要根据实际情况实现
    })
    
    return {
      loading,
      createLoading,
      editLoading,
      users,
      totalUsers,
      currentPage,
      pageSize,
      showCreateDialog,
      showEditDialog,
      showViewDialog,
      searchQuery,
      roleFilter,
      statusFilter,
      createForm,
      editForm,
      editMeta,
      editPwd,
      resetLoading,
      quotas,
      quotasLoading,
      selectedUser,
      currentUserId,
      createRules,
      editRules,
      createFormRef,
      editFormRef,
      filteredUsers,
      fetchUsers,
      createUser,
      editUser,
      updateUser,
      deleteUser,
      viewUser,
      resetCreateForm,
      handleSearch,
      refreshUsers,
      handleSizeChange,
      handleCurrentChange,
      getRoleTagType,
      getRoleText,
      formatTime,
      submitResetInEdit,
      fetchQuotas
    }
  }
}
</script>

<style scoped>
.user-management {
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

.search-filters {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.user-table {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.pagination {
  margin-top: 20px;
  text-align: center;
}

.user-detail {
  padding: 20px 0;
}

.dialog-footer {
  text-align: right;
}
.hint{ margin-top:6px; font-size:12px; color:#909399; }

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }
  
  .search-filters .el-row {
    margin: 0;
  }
  
  .search-filters .el-col {
    margin-bottom: 15px;
  }
}
</style>

