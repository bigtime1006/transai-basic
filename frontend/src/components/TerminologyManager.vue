<template>
  <div class="terminology-manager-container">
    <!-- 分类管理标签页 -->
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 术语管理标签页 -->
      <el-tab-pane :label="$t('term.termsTab')" name="terms">
        <div class="toolbar">
          <el-button type="primary" @click="openAddDialog" class="add-button">{{$t('term.addTerm')}}</el-button>
          <el-button @click="openCategoryFilter" class="filter-button">{{$t('term.categoryFilter')}}</el-button>
        </div>
        
        <!-- 分类过滤 -->
        <div v-if="showCategoryFilter" class="category-filter">
          <el-select 
            v-model="selectedCategoryId" 
            :placeholder="$t('term.selectCategoryFilter')" 
            clearable 
            @change="filterByCategory"
            style="width: 200px; margin-right: 10px;"
          >
            <el-option :label="$t('term.allCategories')" :value="null"></el-option>
            <el-option 
              v-for="category in categories" 
              :key="category.id" 
              :label="category.name" 
              :value="category.id"
            ></el-option>
          </el-select>
          <el-button @click="clearCategoryFilter" size="small">{{$t('term.clearFilter')}}</el-button>
        </div>
        
        <el-table :data="filteredTerms" style="width: 100%;" v-loading="loading" class="custom-table">
          <el-table-column prop="source_lang" :label="$t('term.sourceLang')" width="100"></el-table-column>
          <el-table-column prop="source_text" :label="$t('term.sourceText')"></el-table-column>
          <el-table-column prop="target_lang" :label="$t('term.targetLang')" width="100"></el-table-column>
          <el-table-column prop="target_text" :label="$t('term.targetText')"></el-table-column>
          <el-table-column :label="$t('term.category')" width="120">
            <template #default="scope">
              <el-tag v-if="scope.row.category_name" type="info" size="small">
                {{ scope.row.category_name }}
              </el-tag>
              <span v-else style="color: #999;">{{$t('term.uncategorized')}}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('term.ownership')" width="180">
            <template #default="scope">
              <div style="display:flex;align-items:center;gap:8px;">
                <el-tag :type="(scope.row.user_id===0||scope.row.user_id===null)?'success':'info'">
                  {{ (scope.row.user_id===0||scope.row.user_id===null) ? $t('term.public') : $t('term.private') }}
                </el-tag>
                <span v-if="scope.row.user_id && scope.row.user_id!==0" style="color:#666;">{{ scope.row.owner_username || ($t('common.user')+'#'+scope.row.user_id) }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="$t('term.status')" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'danger'" size="small">
                {{ scope.row.is_active ? $t('term.enabled') : $t('term.disabled') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('term.actions')" width="150">
            <template #default="scope">
              <el-button @click="openEditDialog(scope.row)" type="primary" size="small">{{$t('common.edit')}}</el-button>
              <el-button @click="handleDelete(scope.row.id)" type="danger" size="small">{{$t('common.delete')}}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      
      <!-- 分类管理标签页 -->
      <el-tab-pane :label="$t('term.categoryTab')" name="categories">
        <div class="toolbar">
          <el-button type="primary" @click="openAddCategoryDialog" class="add-button">{{$t('term.addCategory')}}</el-button>
        </div>
        
        <el-table :data="categories" style="width: 100%;" v-loading="categoriesLoading" class="custom-table">
          <el-table-column prop="name" :label="$t('term.categoryName')" width="200"></el-table-column>
          <el-table-column prop="description" :label="$t('term.description')"></el-table-column>
          <el-table-column :label="$t('term.owner')" width="120">
            <template #default="scope">
              <el-tag :type="scope.row.owner_type === 'public' ? 'success' : 'info'" size="small">
                {{ scope.row.owner_type === 'public' ? $t('term.public') : $t('term.private') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="term_count" :label="$t('term.termCount')" width="100" align="center"></el-table-column>
          <el-table-column :label="$t('term.status')" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'danger'" size="small">
                {{ scope.row.is_active ? $t('term.enabled') : $t('term.disabled') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="sort_order" :label="$t('term.sort')" width="80" align="center"></el-table-column>
          <el-table-column :label="$t('term.actions')" width="150">
            <template #default="scope">
              <el-button @click="openEditCategoryDialog(scope.row)" type="primary" size="small">{{$t('common.edit')}}</el-button>
              <el-button @click="handleDeleteCategory(scope.row.id)" type="danger" size="small">{{$t('common.delete')}}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 术语添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" label-width="80px" :rules="formRules" ref="formRef">
        <el-form-item :label="$t('term.sourceLang')" prop="source_lang">
          <el-select v-model="form.source_lang" placeholder="请选择">
            <el-option v-for="item in langOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('term.sourceText')" prop="source_text">
          <el-input v-model="form.source_text"></el-input>
        </el-form-item>
        <el-form-item :label="$t('term.targetLang')" prop="target_lang">
          <el-select v-model="form.target_lang" placeholder="请选择">
            <el-option v-for="item in langOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('term.targetText')" prop="target_text">
          <el-input v-model="form.target_text"></el-input>
        </el-form-item>
        <el-form-item :label="$t('term.category')" prop="category_id">
          <el-select v-model="form.category_id" :placeholder="$t('term.selectCategory')" clearable>
            <el-option :label="$t('term.uncategorized')" :value="-1"></el-option>
            <el-option 
              v-for="category in categories" 
              :key="category.id" 
              :label="category.name" 
              :value="category.id"
            ></el-option>
          </el-select>
          <div class="setting-description">{{$t('term.categoryTip')}}</div>
        </el-form-item>
        <el-form-item :label="$t('term.ownership')">
          <el-tag :type="ownershipTagType" size="small">{{ ownershipLabel }}</el-tag>
        </el-form-item>
        <el-form-item :label="$t('term.status')">
          <el-switch v-model="form.is_active" :active-text="$t('term.enabled')" :inactive-text="$t('term.disabled')"></el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">{{$t('common.close')}}</el-button>
          <el-button type="primary" @click="handleSubmit">{{$t('common.save')}}</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 分类添加/编辑对话框 -->
    <el-dialog v-model="categoryDialogVisible" :title="categoryDialogTitle" width="500px">
      <el-form :model="categoryForm" label-width="80px" :rules="categoryFormRules" ref="categoryFormRef">
        <el-form-item :label="$t('term.categoryName')" prop="name">
          <el-input v-model="categoryForm.name" :placeholder="$t('term.enterCategoryName')"></el-input>
        </el-form-item>
        <el-form-item :label="$t('term.description')" prop="description">
          <el-input 
            v-model="categoryForm.description" 
            type="textarea" 
            :rows="3"
            :placeholder="$t('term.enterCategoryDesc')"
          ></el-input>
        </el-form-item>
        <el-form-item :label="$t('term.ownerType')" prop="owner_type">
          <el-select v-model="categoryForm.owner_type" :placeholder="$t('term.selectOwnerType')">
            <el-option :label="$t('term.publicCategory')" value="public"></el-option>
            <el-option :label="$t('term.privateCategory')" value="user"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('term.sort')" prop="sort_order">
          <el-input-number v-model="categoryForm.sort_order" :min="0" :max="9999"></el-input-number>
        </el-form-item>
        <el-form-item :label="$t('term.status')">
          <el-switch v-model="categoryForm.is_active" :active-text="$t('term.enabled')" :inactive-text="$t('term.disabled')"></el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="categoryDialogVisible = false">{{$t('common.close')}}</el-button>
          <el-button type="primary" @click="handleCategorySubmit">{{$t('common.save')}}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';

const API_BASE_URL = '';

export default {
  name: 'TerminologyManager',
  computed: {
    isAdmin() {
      return (this.currentUserRole || this.currentRoleFromProp) === 'admin'
    }
  },
  props: {
    currentRole: {
      type: String,
      required: false,
      default: ''
    },
    langOptions: {
      type: Array,
      required: false,
      default: () => ([
        { value: 'zh', label: '中文' },
        { value: 'en', label: 'English' },
        { value: 'ja', label: '日本語' },
        { value: 'ko', label: '한국어' },
      ])
    }
  },
  data() {
    return {
      currentUserRole: '',
      currentRoleFromProp: '',
      activeTab: 'terms',
      terms: [],
      categories: [],
      loading: false,
      categoriesLoading: false,
      dialogVisible: false,
      categoryDialogVisible: false,
      dialogTitle: '',
      categoryDialogTitle: '',
      showCategoryFilter: false,
      selectedCategoryId: null,
      form: {
        id: null,
        source_lang: 'zh',
        source_text: '',
        target_lang: 'ja',
        target_text: '',
        category_id: null,
        is_active: true
      },
      categoryForm: {
        id: null,
        name: '',
        description: '',
        owner_type: 'user',
        is_active: true,
        sort_order: 0
      },
      formRules: {
        source_lang: [{ required: true, message: '请选择源语言', trigger: 'change' }],
        source_text: [{ required: true, message: '请输入原文', trigger: 'blur' }],
        target_lang: [{ required: true, message: '请选择目标语言', trigger: 'change' }],
        target_text: [{ required: true, message: '请输入译文', trigger: 'blur' }]
      },
      categoryFormRules: {
        name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }]
      }
    };
  },
  computed: {
    filteredTerms() {
      if (!this.selectedCategoryId) {
        return this.terms;
      }
      return this.terms.filter(term => term.category_id === this.selectedCategoryId);
    },
    selectedCategory() {
      return this.categories.find(c => c.id === this.form.category_id) || null;
    },
    ownershipLabel() {
      if (this.selectedCategory) {
        return this.selectedCategory.owner_type === 'public' ? '公共（随分类）' : '私有（随分类）';
      }
      return '私有（未分类）';
    },
    ownershipTagType() {
      if (this.selectedCategory) {
        return this.selectedCategory.owner_type === 'public' ? 'success' : 'info';
      }
      return 'info';
    }
  },
  created() {
    // 优先使用父组件传入的角色
    this.currentRoleFromProp = this.currentRole
    this.loadCurrentUserRole().then(() => {
      this.fetchTerms();
      this.fetchCategories();
    });
  },
  methods: {
    async loadCurrentUserRole(){
      try{
        const token = localStorage.getItem('token')
        if(!token){ this.currentUserRole=''; return }
        const resp = await fetch('/api/users/me', { headers: { 'Authorization': `Bearer ${token}` } })
        if(resp.ok){ const u = await resp.json(); this.currentUserRole = u.role || '' }
        else { this.currentUserRole = '' }
      }catch{ this.currentUserRole = '' }
    },
    // 术语相关方法
    fetchTerms() {
      this.loading = true;
      const token = localStorage.getItem('token');
      axios.get(`${API_BASE_URL}/api/terminology/`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
        .then(response => {
          this.terms = response.data;
        })
        .catch(error => {
          ElMessage.error('获取术语库失败');
          console.error(error);
        })
        .finally(() => {
          this.loading = false;
        });
    },
    
    openAddDialog() {
      this.dialogTitle = this.$t('term.addTerm');
      this.form = {
        id: null,
        source_lang: 'zh',
        source_text: '',
        target_lang: 'ja',
        target_text: '',
        category_id: null,
        is_active: true
      };
      this.dialogVisible = true;
    },
    
    openEditDialog(term) {
      this.dialogTitle = this.$t('term.editTerm');
      this.form = { ...term };
      this.dialogVisible = true;
    },
    
    handleSubmit() {
      this.$refs.formRef.validate((valid) => {
        if (valid) {
          const payload = { ...this.form };
          // 将 -1 归一化为 null 以兼容后端（未分类）
          if (payload.category_id === -1) payload.category_id = null;
          const token = localStorage.getItem('token');
          const method = this.form.id ? 'put' : 'post';
          const url = this.form.id ? 
            `${API_BASE_URL}/api/terminology/${this.form.id}` : 
            `${API_BASE_URL}/api/terminology/`;
          
          axios[method](url, payload, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
            .then(response => {
              ElMessage.success(this.form.id ? this.$t('term.termUpdated') : this.$t('term.termAdded'));
              if (this.form.id) {
                // 更新现有术语
                const index = this.terms.findIndex(t => t.id === this.form.id);
                if (index !== -1) {
                  this.terms[index] = response.data;
                }
              } else {
                // 添加新术语
                this.terms.unshift(response.data);
              }
              this.dialogVisible = false;
              this.fetchTerms(); // 刷新以获取完整数据
            })
            .catch(error => {
              ElMessage.error(error.response?.data?.detail || this.$t('common.actionFailed'));
              console.error(error);
            });
        }
      });
    },
    
    handleDelete(id) {
      ElMessageBox.confirm(this.$t('term.confirmDeleteTerm'), this.$t('common.confirm'), {
        confirmButtonText: this.$t('common.ok'),
        cancelButtonText: this.$t('common.cancel'),
        type: 'warning'
      }).then(() => {
        const token = localStorage.getItem('token');
        axios.delete(`${API_BASE_URL}/api/terminology/${id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
          .then(() => {
            ElMessage.success(this.$t('common.deleted'));
            this.terms = this.terms.filter(t => t.id !== id);
          })
          .catch(error => {
            ElMessage.error(error.response?.data?.detail || this.$t('common.deleteFailed'));
            console.error(error);
          });
      }).catch(() => {});
    },
    
    // 分类相关方法
    fetchCategories() {
      this.categoriesLoading = true;
      const token = localStorage.getItem('token');
      axios.get(`${API_BASE_URL}/api/terminology/categories`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      })
        .then(response => {
          this.categories = response.data;
        })
        .catch(error => {
          ElMessage.error(this.$t('term.fetchCategoriesFailed'));
          console.error(error);
        })
        .finally(() => {
          this.categoriesLoading = false;
        });
    },
    
    openAddCategoryDialog() {
      this.categoryDialogTitle = this.$t('term.addCategory');
      this.categoryForm = {
        id: null,
        name: '',
        description: '',
        owner_type: this.isAdmin ? 'public' : 'user',
        is_active: true,
        sort_order: 0
      };
      this.categoryDialogVisible = true;
    },
    
    openEditCategoryDialog(category) {
      this.categoryDialogTitle = this.$t('term.editCategory');
      this.categoryForm = { ...category };
      this.categoryDialogVisible = true;
    },
    
    handleCategorySubmit() {
      this.$refs.categoryFormRef.validate((valid) => {
        if (valid) {
          const payload = { ...this.categoryForm };
          const token = localStorage.getItem('token');
          const method = this.categoryForm.id ? 'put' : 'post';
          const url = this.categoryForm.id ? 
            `${API_BASE_URL}/api/terminology/categories/${this.categoryForm.id}` : 
            `${API_BASE_URL}/api/terminology/categories`;
          
          axios[method](url, payload, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
            .then(response => {
              ElMessage.success(this.categoryForm.id ? this.$t('term.categoryUpdated') : this.$t('term.categoryAdded'));
              this.categoryDialogVisible = false;
              this.fetchCategories(); // 刷新分类列表
            })
            .catch(error => {
              ElMessage.error(error.response?.data?.detail || this.$t('common.actionFailed'));
              console.error(error);
            });
        }
      });
    },
    
    handleDeleteCategory(id) {
      ElMessageBox.confirm(this.$t('term.confirmDeleteCategory'), this.$t('common.confirm'), {
        confirmButtonText: this.$t('common.ok'),
        cancelButtonText: this.$t('common.cancel'),
        type: 'warning'
      }).then(() => {
        const token = localStorage.getItem('token');
        axios.delete(`${API_BASE_URL}/api/terminology/categories/${id}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
          .then(() => {
            ElMessage.success(this.$t('common.deleted'));
            this.categories = this.categories.filter(c => c.id !== id);
          })
          .catch(error => {
            ElMessage.error(error.response?.data?.detail || this.$t('common.deleteFailed'));
            console.error(error);
          });
      }).catch(() => {});
    },
    
    // 分类过滤方法
    openCategoryFilter() {
      this.showCategoryFilter = true;
    },
    
    filterByCategory() {
      // 过滤逻辑在computed中处理
    },
    
    clearCategoryFilter() {
      this.selectedCategoryId = null;
      this.showCategoryFilter = false;
    }
  }
};
</script>

<style scoped>
.terminology-manager-container {
  padding: 15px 20px 20px 20px;
  background-color: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.toolbar {
  margin-bottom: 20px;
  text-align: left;
}

.add-button {
  background-color: #4285f4;
  border-color: #4285f4;
}

.filter-button {
  margin-left: 10px;
}

.category-filter {
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.custom-table {
  margin-top: 20px;
}

.setting-description {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
</style>
