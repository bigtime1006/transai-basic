<template>
  <div class="admin-engine-settings">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <span>AI引擎设置管理</span>
          <el-button type="primary" @click="refreshSettings" :loading="loading">
            刷新设置
          </el-button>
        </div>
      </template>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="6" animated />
      </div>

      <div v-else>
        <!-- DeepSeek设置 -->
        <el-card class="engine-card" shadow="hover">
          <template #header>
            <div class="engine-header">
              <span class="engine-title">DeepSeek 设置</span>
              <el-tag :type="deepseekSettings.use_json_format ? 'success' : 'info'">
                {{ deepseekSettings.use_json_format ? 'JSON格式' : '文本格式' }}
              </el-tag>
            </div>
          </template>

          <el-form :model="deepseekSettings" label-width="120px" size="small">
            <el-form-item label="JSON格式">
              <el-switch
                v-model="deepseekSettings.use_json_format"
                @change="updateDeepSeekSettings"
                active-text="启用"
                inactive-text="禁用"
              />
              <div class="setting-description">
                启用JSON格式可提高大批量翻译效率，批次大小从20提升到50
              </div>
            </el-form-item>

            <el-form-item label="JSON批次大小">
              <el-input-number
                v-model="deepseekSettings.json_batch_size"
                :min="10"
                :max="100"
                :step="5"
                @change="updateDeepSeekSettings"
                :disabled="!deepseekSettings.use_json_format"
              />
              <div class="setting-description">
                建议范围：10-100，数值越大效率越高但可能增加API错误率
              </div>
            </el-form-item>

            <el-form-item label="文本批次大小">
              <el-input-number
                v-model="deepseekSettings.batch_size"
                :min="5"
                :max="50"
                :step="5"
                @change="updateDeepSeekSettings"
                :disabled="deepseekSettings.use_json_format"
              />
              <div class="setting-description">
                文本格式的批次大小，当JSON格式禁用时生效
              </div>
            </el-form-item>

            <el-form-item label="最大工作线程">
              <el-input-number
                v-model="deepseekSettings.max_workers"
                :min="1"
                :max="20"
                @change="updateDeepSeekSettings"
              />
              <div class="setting-description">
                并发翻译的最大工作线程数
              </div>
            </el-form-item>

            <el-form-item label="超时时间(秒)">
              <el-input-number
                v-model="deepseekSettings.timeout"
                :min="30"
                :max="300"
                :step="10"
                @change="updateDeepSeekSettings"
              />
              <div class="setting-description">
                API请求的超时时间
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- Kimi设置 -->
        <el-card class="engine-card" shadow="hover">
          <template #header>
            <div class="engine-header">
              <span class="engine-title">Kimi 设置</span>
              <el-tag type="warning">只读</el-tag>
            </div>
          </template>

          <el-form :model="kimiSettings" label-width="120px" size="small" disabled>
            <el-form-item label="批次大小">
              <el-input-number v-model="kimiSettings.batch_size" :min="1" :max="20" />
            </el-form-item>

            <el-form-item label="最大工作线程">
              <el-input-number v-model="kimiSettings.max_workers" :min="1" :max="10" />
            </el-form-item>

            <el-form-item label="超时时间(秒)">
              <el-input-number v-model="kimiSettings.timeout" :min="30" :max="300" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- Youdao设置 -->
        <el-card class="engine-card" shadow="hover">
          <template #header>
            <div class="engine-header">
              <span class="engine-title">Youdao 设置</span>
              <el-tag type="warning">只读</el-tag>
            </div>
          </template>

          <el-form :model="youdaoSettings" label-width="120px" size="small" disabled>
            <el-form-item label="批次大小">
              <el-input-number v-model="youdaoSettings.batch_size" :min="1" :max="20" />
            </el-form-item>

            <el-form-item label="最大工作线程">
              <el-input-number v-model="youdaoSettings.max_workers" :min="1" :max="10" />
            </el-form-item>

            <el-form-item label="最大批次大小">
              <el-input-number v-model="youdaoSettings.max_batch_size" :min="1" :max="10" />
            </el-form-item>

            <el-form-item label="每批次最大字符数">
              <el-input-number v-model="youdaoSettings.max_chars_per_batch" :min="100" :max="5000" :step="100" />
            </el-form-item>

            <el-form-item label="超时时间(秒)">
              <el-input-number v-model="youdaoSettings.timeout" :min="30" :max="300" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- Tencent设置 -->
        <el-card class="engine-card" shadow="hover">
          <template #header>
            <div class="engine-header">
              <span class="engine-title">Tencent 设置</span>
              <el-tag type="warning">只读</el-tag>
            </div>
          </template>

          <el-form :model="tencentSettings" label-width="120px" size="small" disabled>
            <el-form-item label="批次大小">
              <el-input-number v-model="tencentSettings.batch_size" :min="1" :max="30" />
            </el-form-item>

            <el-form-item label="最大工作线程">
              <el-input-number v-model="tencentSettings.max_workers" :min="1" :max="10" />
            </el-form-item>

            <el-form-item label="超时时间(秒)">
              <el-input-number v-model="tencentSettings.timeout" :min="30" :max="300" />
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'AdminEngineSettings',
  setup() {
    const loading = ref(false)
    const deepseekSettings = ref({
      use_json_format: true,
      json_batch_size: 50,
      batch_size: 20,
      max_workers: 10,
      timeout: 60
    })
    const kimiSettings = ref({
      batch_size: 8,
      max_workers: 2,
      timeout: 60
    })
    const youdaoSettings = ref({
      batch_size: 10,
      max_workers: 3,
      timeout: 60,
      max_batch_size: 5,
      max_chars_per_batch: 1000
    })
    const tencentSettings = ref({
      batch_size: 15,
      max_workers: 5,
      timeout: 60
    })

    const API_BASE_URL = window.location.hostname === 'localhost' 
      ? 'http://localhost:8000' 
      : `http://${window.location.hostname}:8000`

    const fetchSettings = async () => {
      try {
        loading.value = true
        const response = await fetch(`${API_BASE_URL}/api/admin/settings/engines`)
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        
        const settings = await response.json()
        
        if (settings.deepseek && !settings.deepseek.error) {
          deepseekSettings.value = settings.deepseek
        }
        if (settings.kimi && !settings.kimi.error) {
          kimiSettings.value = settings.kimi
        }
        if (settings.youdao && !settings.youdao.error) {
          youdaoSettings.value = settings.youdao
        }
        if (settings.tencent && !settings.tencent.error) {
          tencentSettings.value = settings.tencent
        }
        
        ElMessage.success('设置加载成功')
      } catch (error) {
        console.error('Failed to fetch settings:', error)
        ElMessage.error(`加载设置失败: ${error.message}`)
      } finally {
        loading.value = false
      }
    }

    const updateDeepSeekSettings = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/admin/settings/deepseek`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(deepseekSettings.value)
        })
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }
        
        const result = await response.json()
        ElMessage.success('DeepSeek设置更新成功')
        
        // 重新获取设置以确保同步
        await fetchSettings()
      } catch (error) {
        console.error('Failed to update DeepSeek settings:', error)
        ElMessage.error(`更新设置失败: ${error.message}`)
        
        // 恢复原始设置
        await fetchSettings()
      }
    }

    const refreshSettings = () => {
      fetchSettings()
    }

    onMounted(() => {
      fetchSettings()
    })

    return {
      loading,
      deepseekSettings,
      kimiSettings,
      youdaoSettings,
      tencentSettings,
      updateDeepSeekSettings,
      refreshSettings
    }
  }
}
</script>

<style scoped>
.admin-engine-settings {
  padding: 20px;
}

.settings-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.loading-container {
  padding: 20px;
}

.engine-card {
  margin-bottom: 20px;
}

.engine-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.engine-title {
  font-weight: bold;
  font-size: 16px;
}

.setting-description {
  font-size: 12px;
  color: #666;
  margin-top: 5px;
  line-height: 1.4;
}

.el-form-item {
  margin-bottom: 18px;
}

.el-input-number {
  width: 120px;
}
</style>

