<template>
  <div class="engine-selector">
    <el-select 
      v-model="selectedEngine" 
      placeholder="选择AI翻译引擎"
      @change="handleEngineChange"
      class="engine-select"
      :disabled="disabled"
    >
      <el-option
        v-for="engine in availableEngines"
        :key="engine.value"
        :label="engine.label"
        :value="engine.value"
        :disabled="!engine.available"
      >
        <div class="engine-option">
          <span class="engine-name">{{ engine.label }}</span>
          <span class="engine-status" :class="engine.available ? 'available' : 'unavailable'">
            {{ engine.available ? $t('common.available') : $t('common.unavailable') }}
          </span>
        </div>
      </el-option>
    </el-select>
  </div>
</template>

<script>
export default {
  name: 'EngineSelector',
  props: {
    value: {
      type: String,
      default: 'deepseek'
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      selectedEngine: this.value,
      availableEngines: []
    }
  },
  computed: {
    selectedEngineInfo() {
      return this.availableEngines.find(engine => engine.value === this.selectedEngine)
    }
  },
  watch: {
    value(newVal) {
      this.selectedEngine = newVal
    }
  },
  async mounted() {
    await this.loadAvailableEngines()
  },
  methods: {
    handleEngineChange(value) {
      this.$emit('input', value)
      this.$emit('change', value)
    },
    
    getEngineTagType(engine) {
      const types = {
        'deepseek': 'primary',
        'tencent': 'success',
        'kimi': 'warning',
        'youdao': 'info'
      }
      return types[engine] || 'default'
    },
    
    async loadAvailableEngines() {
      try {
        const response = await fetch('/api/engines/available')
        if (response.ok) {
          const data = await response.json()
          this.availableEngines = data.map(e => ({
            value: e.engine_name,
            label: e.display_name,
            available: true,
            isDefault: !!e.is_default
          }))
          // 以后端默认为准
          const def = data.find(e => e.is_default) || data[0]
          if (def) {
            this.selectedEngine = def.engine_name
            this.handleEngineChange(this.selectedEngine)
          }
        }
      } catch (e) {
        console.log('Failed to load engines, using fallback deepseek')
        this.availableEngines = [{ value: 'deepseek', label: 'DeepSeek', available: true, isDefault: true }]
      }
    }
  }
}
</script>

<style scoped>
.engine-selector {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.engine-select {
  width: 100%;
}

.engine-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.engine-name {
  font-weight: 500;
}

.engine-status {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 3px;
}

.engine-status.available {
  background-color: #f0f9ff;
  color: #0369a1;
}

.engine-status.unavailable {
  background-color: #fef2f2;
  color: #dc2626;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .engine-selector {
    width: 100%;
  }
}
</style>
