<template>
  <div class="category-selector">
    <div class="selector-header">
      <span class="selector-label">{{ label }}</span>
      <el-button 
        v-if="showHelp" 
        type="text" 
        size="small" 
        @click="showHelpDialog = true"
        class="help-button"
      >
        <el-icon><QuestionFilled /></el-icon>
      </el-button>
    </div>
    
    <el-select
      v-model="selectedCategories"
      multiple
      :placeholder="placeholder"
      :disabled="disabled"
      :multiple-limit="maxCategories"
      collapse-tags
      collapse-tags-tooltip
      style="width: 100%;"
      @change="handleChange"
      @clear="handleClear"
    >
      <el-option
        v-for="category in availableCategories"
        :key="category.id"
        :label="category.name"
        :value="category.id"
        :disabled="!category.is_active"
      >
        <div class="category-option">
          <span class="category-name">{{ category.name }}</span>
          <span class="category-count" v-if="category.term_count">
            ({{ category.term_count }})
          </span>
          <el-tag 
            v-if="category.owner_type === 'public'" 
            size="small" 
            type="success"
            class="category-tag"
          >
            公共
          </el-tag>
          <el-tag 
            v-else 
            size="small" 
            type="info"
            class="category-tag"
          >
            私有
          </el-tag>
        </div>
      </el-option>
    </el-select>
    
    <div class="selector-info" v-if="showInfo">
      <el-text size="small" type="info">
        已选择 {{ selectedCategories.length }}/{{ maxCategories }} 个分类
        <span v-if="selectedCategories.length > 0">
          • 共 {{ totalTerms }} 个术语
        </span>
      </el-text>
    </div>
    
    <!-- 帮助对话框 -->
    <el-dialog v-model="showHelpDialog" title="术语分类使用说明" width="500px">
      <div class="help-content">
        <h4>什么是术语分类？</h4>
        <p>术语分类是按业务场景、文档类型等维度组织的术语集合，帮助您在翻译时选择最相关的术语。</p>
        
        <h4>如何使用？</h4>
        <ul>
          <li>选择与当前翻译内容相关的术语分类</li>
          <li>系统会自动加载选中分类的术语进行翻译</li>
          <li>可以选择多个分类，系统会合并所有术语</li>
          <li>最多可选择 {{ maxCategories }} 个分类</li>
        </ul>
        
        <h4>分类类型</h4>
        <ul>
          <li><el-tag size="small" type="success">公共分类</el-tag>：所有用户可见，管理员维护</li>
          <li><el-tag size="small" type="info">私有分类</el-tag>：仅创建者可见和管理</li>
        </ul>
        
        <h4>建议</h4>
        <p>根据文档类型选择合适的分类，如技术文档选择"技术文档"分类，商务合同选择"商务合同"分类。</p>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { QuestionFilled } from '@element-plus/icons-vue'

export default {
  name: 'CategorySelector',
  components: {
    QuestionFilled
  },
  props: {
    modelValue: {
      type: Array,
      default: () => []
    },
    label: {
      type: String,
      default: '术语分类'
    },
    placeholder: {
      type: String,
      default: '选择术语分类'
    },
    disabled: {
      type: Boolean,
      default: false
    },
    maxCategories: {
      type: Number,
      default: 10
    },
    showInfo: {
      type: Boolean,
      default: true
    },
    showHelp: {
      type: Boolean,
      default: true
    },
    categories: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      selectedCategories: [],
      showHelpDialog: false
    }
  },
  computed: {
    availableCategories() {
      return this.categories.filter(cat => cat.is_active)
    },
    totalTerms() {
      if (!this.selectedCategories.length) return 0
      return this.categories
        .filter(cat => this.selectedCategories.includes(cat.id))
        .reduce((sum, cat) => sum + (cat.term_count || 0), 0)
    }
  },
  watch: {
    modelValue: {
      immediate: true,
      handler(newVal) {
        this.selectedCategories = [...(newVal || [])]
      }
    }
  },
  methods: {
    handleChange(value) {
      this.$emit('update:modelValue', value)
      this.$emit('change', value)
    },
    handleClear() {
      this.$emit('update:modelValue', [])
      this.$emit('change', [])
    }
  }
}
</script>

<style scoped>
.category-selector {
  margin-bottom: 16px;
}

.selector-header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.selector-label {
  font-weight: 500;
  color: #303133;
  margin-right: 8px;
}

.help-button {
  color: #909399;
  padding: 0;
}

.help-button:hover {
  color: #409eff;
}

.selector-info {
  margin-top: 8px;
}

.category-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.category-name {
  flex: 1;
}

.category-count {
  color: #909399;
  font-size: 12px;
}

.category-tag {
  margin-left: auto;
}

.help-content h4 {
  margin: 16px 0 8px 0;
  color: #303133;
  font-size: 14px;
}

.help-content h4:first-child {
  margin-top: 0;
}

.help-content p {
  margin: 8px 0;
  color: #606266;
  line-height: 1.5;
}

.help-content ul {
  margin: 8px 0;
  padding-left: 20px;
  color: #606266;
  line-height: 1.5;
}

.help-content li {
  margin: 4px 0;
}
</style>


