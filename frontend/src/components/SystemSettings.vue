<template>
  <div class="system-settings">
    <h3>{{ $t('settings.title') }}</h3>
    <el-alert type="info" show-icon :closable="false" style="margin-bottom: 12px;">
      <template #title>
        {{ $t('settings.notesTitle') }}
      </template>
      <ul style="margin-left: 16px;">
        <li>{{ $t('settings.note1') }}</li>
        <li>{{ $t('settings.note2') }}</li>
        <li>{{ $t('settings.note3') }}</li>
        <li>{{ $t('settings.note4') }}</li>
      </ul>
    </el-alert>

    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>{{ $t('settings.strategy') }}</span>
          <el-button size="small" @click="loadStrategies">{{ $t('common.refresh') }}</el-button>
        </div>
      </template>
      <el-table :data="strategies" v-loading="loadingStrategies" style="width:100%">
        <el-table-column prop="display_name" :label="$t('settings.name')" width="180" />
        <el-table-column prop="strategy_name" :label="$t('settings.key')" width="180" />
        <el-table-column :label="$t('settings.formats')">
          <template #default="scope">
            <el-tag v-for="fmt in scope.row.supported_formats" :key="fmt" style="margin-right:6px;">{{ fmt }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" :label="$t('settings.priority')" width="100" />
        <el-table-column :label="$t('common.status')" width="120">
          <template #default="scope">
            <el-switch :model-value="scope.row.status" @change="val => toggleStrategy(scope.row, val)" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-card shadow="never" style="margin-top:16px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>{{ $t('settings.terminology') }}</span>
          <div>
            <el-button size="small" @click="loadTerminology" style="margin-right:8px;">{{ $t('common.refresh') }}</el-button>
            <el-button size="small" type="primary" :loading="savingTerminology" @click="saveTerminology">{{ $t('common.save') }}</el-button>
          </div>
        </div>
      </template>
      <div v-loading="terminologyLoading">
        <el-form label-width="200px" style="max-width:640px;">
          <el-form-item :label="$t('settings.termEnable')">
            <el-switch v-model="terminology.enabled" />
            <div class="setting-description">{{ $t('settings.termEnableDesc') }}</div>
          </el-form-item>
          <el-form-item :label="$t('settings.caseSensitive')">
            <el-switch v-model="terminology.caseSensitive" />
            <div class="setting-description">{{ $t('settings.caseSensitiveDesc') }}</div>
          </el-form-item>
          <el-form-item :label="$t('settings.categoryEnable')">
            <el-switch v-model="terminology.categoriesEnabled" />
            <div class="setting-description">{{ $t('settings.categoryEnableDesc') }}</div>
          </el-form-item>
          <el-form-item :label="$t('settings.maxCategories')" v-if="terminology.categoriesEnabled">
            <el-input-number v-model="terminology.maxCategories" :min="1" :max="20" />
            <div class="setting-description">{{ $t('settings.maxCategoriesDesc') }}</div>
          </el-form-item>
          <el-form-item :label="$t('settings.defaultCategories')" v-if="terminology.categoriesEnabled">
            <el-select 
              v-model="terminology.defaultCategories" 
              multiple 
              :placeholder="$t('settings.selectDefaultCategories')"
              style="width: 100%;"
            >
              <el-option 
                v-for="category in availableCategories" 
                :key="category.id" 
                :label="category.name" 
                :value="category.id"
              ></el-option>
            </el-select>
            <div class="setting-description">{{ $t('settings.defaultCategoriesDesc') }}</div>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    <el-card shadow="never" style="margin-top:16px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>{{ $t('settings.history') }}</span>
          <div>
            <el-button size="small" @click="loadHistoryLimits" style="margin-right:8px;">{{ $t('common.refresh') }}</el-button>
            <el-button size="small" type="primary" :loading="savingLimits" @click="saveHistoryLimits">{{ $t('common.save') }}</el-button>
          </div>
        </div>
      </template>
      <div v-loading="limitsLoading">
        <el-form label-width="200px" style="max-width:640px;">
          <el-form-item :label="$t('settings.maxTextPerUser')">
            <el-input-number v-model="historyLimits.maxText" :min="1" :max="100000" />
            <div class="setting-description">{{ $t('settings.maxTextDesc') }}</div>
          </el-form-item>
          <el-form-item :label="$t('settings.maxDocPerUser')">
            <el-input-number v-model="historyLimits.maxDoc" :min="1" :max="100000" />
          </el-form-item>
          <el-form-item :label="$t('settings.frontendDeletePermanent')">
            <el-switch v-model="historyLimits.permDelete" />
            <div class="setting-description">{{ $t('settings.frontendDeletePermanentDesc') }}</div>
          </el-form-item>
          <el-form-item :label="$t('settings.textRetentionDays')">
            <el-input-number v-model="historyLimits.textRetention" :min="1" :max="3650" />
          </el-form-item>
          <el-form-item :label="$t('settings.docRetentionDays')">
            <el-input-number v-model="historyLimits.docRetention" :min="1" :max="3650" />
            <div class="setting-description">{{ $t('settings.docRetentionDaysDesc') }}</div>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
    <el-card shadow="never" style="margin-top:16px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>{{ $t('settings.engineMgmt') }}</span>
          <div>
            <el-button size="small" @click="loadEngines" style="margin-right:8px;">{{ $t('common.refresh') }}</el-button>
            <el-button size="small" type="primary" @click="showCreateDialog = true">{{ $t('settings.addEngine') }}</el-button>
          </div>
        </div>
      </template>
      <el-table :data="engines" v-loading="loadingEngines" style="width:100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="display_name" :label="$t('settings.name')" width="160" />
        <el-table-column prop="engine_name" :label="$t('settings.key')" width="140" />
        <el-table-column prop="status" :label="$t('common.status')" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.status==='active'?'success':(scope.row.status==='maintenance'?'warning':'danger')">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" :label="$t('settings.priority')" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.priority<=10?'success':(scope.row.priority<=30?'warning':'danger')">{{ scope.row.priority }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rate_limit" :label="$t('settings.rateLimit')" width="120">
          <template #default="scope">{{ scope.row.rate_limit }}/{{$t('settings.perMinute')}}</template>
        </el-table-column>
        <el-table-column prop="cost_per_token" :label="$t('settings.costPerToken')" width="100">
          <template #default="scope">{{ Number(scope.row.cost_per_token||0).toFixed(6) }}</template>
        </el-table-column>
        <el-table-column prop="is_default" :label="$t('settings.default')" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.is_default" type="success">{{ $t('settings.default') }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('common.actions')" width="320" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="viewEngine(scope.row)">{{ $t('common.view') }}</el-button>
            <el-button size="small" type="primary" @click="openEdit(scope.row)">{{ $t('common.edit') }}</el-button>
            <el-button size="small" :type="scope.row.status==='active' ? 'warning' : 'success'" @click="toggleEngine(scope.row)">
              {{ scope.row.status==='active' ? $t('common.disable') : $t('common.enable') }}
            </el-button>
            <el-button size="small" type="danger" :disabled="scope.row.is_default" @click="deleteEngine(scope.row)">{{ $t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 查看引擎详情 -->
      <el-dialog v-model="showViewDialog" :title="$t('settings.engineDetail')" width="700px">
        <div v-if="selectedEngine">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="ID">{{ selectedEngine.id }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.key')">{{ selectedEngine.engine_name }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.name')">{{ selectedEngine.display_name }}</el-descriptions-item>
            <el-descriptions-item :label="$t('common.status')">
              <el-tag :type="selectedEngine.status==='active'?'success':(selectedEngine.status==='maintenance'?'warning':'danger')">{{ selectedEngine.status }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('settings.priority')">{{ selectedEngine.priority }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.rateLimit')">{{ selectedEngine.rate_limit }}/{{$t('settings.perMinute')}}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.costPerToken')">{{ Number(selectedEngine.cost_per_token||0).toFixed(6) }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.default')">
              <el-tag v-if="selectedEngine.is_default" type="success">{{ $t('settings.default') }}</el-tag>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('common.description')" :span="2">{{ selectedEngine.description || '-' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('settings.supportedLanguages')" :span="2">
              <el-tag v-for="lang in (selectedEngine.supported_languages||[])" :key="lang" style="margin-right:6px;">{{ lang }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('settings.features')" :span="2">
              <el-tag v-for="f in (selectedEngine.features||[])" :key="f" style="margin-right:6px;">{{ f }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('settings.apiConfig')" :span="2">
              <pre style="white-space:pre-wrap;word-break:break-all;">{{ JSON.stringify(selectedEngine.api_config||{}, null, 2) }}</pre>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-dialog>

      <!-- 创建引擎 -->
      <el-dialog v-model="showCreateDialog" :title="$t('settings.addEngine')" width="600px" :close-on-click-modal="false">
        <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="120px">
          <el-form-item :label="$t('settings.engineKey')" prop="engine_name">
            <el-input v-model="createForm.engine_name" :placeholder="$t('settings.engineKeyPh')" />
          </el-form-item>
          <el-form-item :label="$t('settings.name')" prop="display_name">
            <el-input v-model="createForm.display_name" />
          </el-form-item>
          <el-form-item :label="$t('common.description')" prop="description">
            <el-input v-model="createForm.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item :label="$t('common.status')" prop="status">
            <el-select v-model="createForm.status" :placeholder="$t('common.select')">
              <el-option :label="$t('settings.active')" value="active" />
              <el-option :label="$t('settings.maintenance')" value="maintenance" />
              <el-option :label="$t('settings.inactive')" value="inactive" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('settings.priority')" prop="priority"><el-input-number v-model="createForm.priority" :min="0" :max="100" /></el-form-item>
          <el-form-item :label="$t('settings.rateLimit')" prop="rate_limit"><el-input-number v-model="createForm.rate_limit" :min="1" :max="10000" /></el-form-item>
          <el-form-item :label="$t('settings.costPerToken')" prop="cost_per_token"><el-input-number v-model="createForm.cost_per_token" :min="0" :precision="6" :step="0.000001" /></el-form-item>
          <el-form-item :label="$t('settings.supportedLanguages')" prop="supported_languages">
            <el-select v-model="createForm.supported_languages" multiple filterable allow-create>
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
          <el-form-item :label="$t('settings.features')" prop="features">
            <el-select v-model="createForm.features" multiple filterable allow-create>
              <el-option :label="$t('settings.featureText')" value="text_translation" />
              <el-option :label="$t('settings.featureDoc')" value="document_translation" />
              <el-option label="JSON格式" value="json_format" />
              <el-option :label="$t('settings.featureBatch')" value="batch_translation" />
              <el-option :label="$t('menu.terminology')" value="terminology" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('settings.setDefault')" prop="is_default"><el-switch v-model="createForm.is_default" /></el-form-item>
          <el-form-item :label="$t('settings.apiConfig')" prop="api_config">
            <el-input v-model="createForm.api_config_text" type="textarea" :rows="4" :placeholder="$t('settings.apiConfigPh')" @input="updateApiConfig" />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showCreateDialog=false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" :loading="createLoading" @click="createEngine">{{ $t('common.create') }}</el-button>
          </span>
        </template>
      </el-dialog>

      <!-- 编辑引擎 -->
      <el-dialog v-model="showEditDialog" :title="$t('settings.editEngine')" width="600px" :close-on-click-modal="false">
        <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="120px">
          <el-form-item :label="$t('settings.engineKey')" prop="engine_name"><el-input v-model="editForm.engine_name" disabled /></el-form-item>
          <el-form-item :label="$t('settings.name')" prop="display_name"><el-input v-model="editForm.display_name" /></el-form-item>
          <el-form-item :label="$t('common.description')" prop="description"><el-input v-model="editForm.description" type="textarea" :rows="3" /></el-form-item>
          <el-form-item :label="$t('common.status')" prop="status">
            <el-select v-model="editForm.status">
              <el-option :label="$t('settings.active')" value="active" />
              <el-option :label="$t('settings.maintenance')" value="maintenance" />
              <el-option :label="$t('settings.inactive')" value="inactive" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('settings.priority')" prop="priority"><el-input-number v-model="editForm.priority" :min="0" :max="100" /></el-form-item>
          <el-form-item :label="$t('settings.rateLimit')" prop="rate_limit"><el-input-number v-model="editForm.rate_limit" :min="1" :max="10000" /></el-form-item>
          <el-form-item :label="$t('settings.costPerToken')" prop="cost_per_token"><el-input-number v-model="editForm.cost_per_token" :min="0" :precision="6" :step="0.000001" /></el-form-item>
          <el-form-item :label="$t('settings.supportedLanguages')" prop="supported_languages">
            <el-select v-model="editForm.supported_languages" multiple filterable allow-create>
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
          <el-form-item v-if="editForm.engine_name==='qwen3'" :label="$t('settings.qwenModel')">
            <el-select v-model="qwen3Model" style="width:100%">
              <el-option :label="$t('settings.qwenMtTurbo')" value="qwen-mt-turbo" />
              <el-option :label="$t('settings.qwenMtPlus')" value="qwen-mt-plus" />
            </el-select>
          </el-form-item>
          <!-- Qwen3 专用：细粒度配置（与后端联动） -->
          <template v-if="editForm.engine_name==='qwen3'">
            <el-form-item label="Qwen3 max_workers">
              <el-input-number v-model="qwen3Extras.max_workers" :min="1" :max="50" />
            </el-form-item>
            <el-form-item label="Qwen3 batch_size">
              <el-input-number v-model="qwen3Extras.batch_size" :min="1" :max="200" />
            </el-form-item>
            <el-form-item label="Qwen3 timeout(s)">
              <el-input-number v-model="qwen3Extras.timeout" :min="5" :max="120" />
            </el-form-item>
            <el-form-item label="Qwen3 retry_max">
              <el-input-number v-model="qwen3Extras.retry_max" :min="1" :max="10" />
            </el-form-item>
            <el-form-item label="Qwen3 sleep_between_requests(s)">
              <el-input-number v-model="qwen3Extras.sleep_between_requests" :min="0" :max="1" :step="0.05" />
            </el-form-item>
          </template>
          <el-form-item :label="$t('settings.features')" prop="features">
            <el-select v-model="editForm.features" multiple filterable allow-create>
              <el-option :label="$t('settings.featureText')" value="text_translation" />
              <el-option :label="$t('settings.featureDoc')" value="document_translation" />
              <el-option label="JSON格式" value="json_format" />
              <el-option :label="$t('settings.featureBatch')" value="batch_translation" />
              <el-option :label="$t('menu.terminology')" value="terminology" />
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('settings.setDefault')" prop="is_default"><el-switch v-model="editForm.is_default" /></el-form-item>
          <el-form-item :label="$t('settings.apiConfig')" prop="api_config"><el-input v-model="editForm.api_config_text" type="textarea" :rows="4" @input="updateEditApiConfig" /></el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="showEditDialog=false">{{ $t('common.cancel') }}</el-button>
            <el-button type="primary" :loading="editLoading" @click="updateEngine">{{ $t('common.update') }}</el-button>
          </span>
        </template>
      </el-dialog>
    </el-card>
    <el-card shadow="never" style="margin-top:16px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>{{ $t('settings.ooxml') }}</span>
          <div>
            <el-button size="small" @click="loadOoxmlSettings" style="margin-right:8px;">{{ $t('common.refresh') }}</el-button>
            <el-button size="small" type="primary" :loading="savingOoxml" @click="saveOoxmlSettings">{{ $t('common.save') }}</el-button>
          </div>
        </div>
      </template>
      <div v-loading="ooxmlLoading">
        <el-form label-width="200px" style="max-width:640px;">
          <el-form-item :label="$t('settings.pptxOoxml')">
            <el-switch v-model="ooxml.pptx" />
          </el-form-item>
          <el-form-item :label="$t('settings.xlsxOoxml')">
            <el-switch v-model="ooxml.xlsx" />
          </el-form-item>
          <el-form-item :label="$t('settings.docxWorkers')">
            <el-input-number v-model="ooxml.docxWorkers" :min="1" :max="32" />
          </el-form-item>
          <el-form-item label="DOCX 精确Tokens(顺序)">
            <el-switch v-model="ooxml.docxCollectTokens" />
            <div class="setting-description">
              开启后，DOCX 翻译改为顺序模式以精确统计 tokens（较慢）。关闭则使用并行，性能更好但 tokens 可能不精确。
              示例（同一 DOCX 实测）：开启时 耗时约 114.96 秒，Tokens ≈ 7662；关闭时 耗时约 99.53 秒，Tokens ≈ 3895。
            </div>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <el-card shadow="never" style="margin-top:16px;">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span>{{ $t('settings.passwordPolicy') }}</span>
          <div>
            <el-button size="small" @click="loadPasswordPolicy" style="margin-right:8px;">{{ $t('common.refresh') }}</el-button>
            <el-button size="small" type="primary" :loading="savingPassword" @click="savePasswordPolicy">{{ $t('common.save') }}</el-button>
          </div>
        </div>
      </template>
      <div v-loading="passwordLoading">
        <el-form label-width="220px" style="max-width:640px;">
          <el-form-item :label="$t('settings.minLength')">
            <el-input-number v-model="passwordPolicy.minLength" :min="6" :max="128" />
          </el-form-item>
          <el-form-item :label="$t('settings.requireUpper')">
            <el-switch v-model="passwordPolicy.requireUppercase" />
          </el-form-item>
          <el-form-item :label="$t('settings.requireLower')">
            <el-switch v-model="passwordPolicy.requireLowercase" />
          </el-form-item>
          <el-form-item :label="$t('settings.requireDigit')">
            <el-switch v-model="passwordPolicy.requireDigit" />
          </el-form-item>
          <el-form-item :label="$t('settings.requireSpecial')">
            <el-switch v-model="passwordPolicy.requireSpecial" />
          </el-form-item>
        </el-form>
      </div>
    </el-card>
  </div>
  
</template>

<script>
export default {
  name: 'SystemSettings',
  data(){
    return {
      strategies: [],
      loadingStrategies: false,
      terminologyLoading: false,
      savingTerminology: false,
      terminology: {
        enabledId: null,
        enabled: true,
        caseId: null,
        caseSensitive: false,
        categoriesEnabledId: null,
        categoriesEnabled: false,
        maxCategoriesId: null,
        maxCategories: 5,
        defaultCategoriesId: null,
        defaultCategories: []
      },
      availableCategories: [], // 可用的术语分类列表
      engines: [],
      // OOXML
      ooxmlLoading: false,
      savingOoxml: false,
      ooxml: { pptx: true, xlsx: true, docxWorkers: 6, docxCollectTokens: false, ids: { pptx:null, xlsx:null, workers:null, collect:null } },
      // 密码策略
      passwordLoading: false,
      savingPassword: false,
      passwordPolicy: { minLength: 8, requireUppercase: true, requireLowercase: true, requireDigit: true, requireSpecial: false, ids: { min:null, up:null, low:null, dig:null, spec:null } },
      loadingEngines: false,
      // 历史上限
      limitsLoading: false,
      savingLimits: false,
      historyLimits: { maxText: 1000, maxDoc: 1000, permDelete: true, textRetention: 30, docRetention: 30 },
      showViewDialog: false,
      showCreateDialog: false,
      showEditDialog: false,
      createLoading: false,
      editLoading: false,
      selectedEngine: null,
      createForm: {
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
      },
      editForm: {
        id: null,
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
      },
      // Qwen3 细粒度配置（与后端联动）
      qwen3Extras: { max_workers: 12, batch_size: 50, timeout: 60, retry_max: 3, sleep_between_requests: 0 },
      createRules: {
        engine_name: [
          { required: true, message: '请输入标识符', trigger: 'blur' },
          { min: 2, max: 50, message: '长度 2-50', trigger: 'blur' }
        ],
        display_name: [
          { required: true, message: '请输入显示名称', trigger: 'blur' }
        ]
      },
      editRules: {
        display_name: [
          { required: true, message: '请输入显示名称', trigger: 'blur' }
        ]
      },
      qwen3Model: 'qwen-mt-turbo'
    }
  },
  mounted(){ 
    // 先加载与“显示初值”强相关的配置，避免需要手动刷新
    this.loadHistoryLimits();
    this.loadOoxmlSettings();
    this.loadPasswordPolicy();
    // 其余次序不敏感
    this.loadStrategies(); 
    this.loadEngines(); 
    this.loadTerminology();
    this.loadAvailableCategories();
  },
  methods:{
    async loadOoxmlSettings(){
      try{
        this.ooxmlLoading = true
        const token = localStorage.getItem('token')
        const hdrs = token ? { 'Authorization': `Bearer ${token}` } : {}
        const resp = await fetch('/api/admin/settings?category=ooxml', { headers: hdrs })
        if(resp.ok){
          const items = await resp.json()
          const find = k => items.find(i => i.key===k)
          const toBool = v => String(v).toLowerCase() === 'true'
          const pptx = find('pptx_use_ooxml');
          const xlsx = find('xlsx_use_ooxml');
          const workers = find('docx_parallel_workers');
          const collect = find('docx_collect_tokens');
          if(pptx){ this.ooxml.ids.pptx = pptx.id; this.ooxml.pptx = toBool(pptx.value) }
          if(xlsx){ this.ooxml.ids.xlsx = xlsx.id; this.ooxml.xlsx = toBool(xlsx.value) }
          if(workers){ this.ooxml.ids.workers = workers.id; this.ooxml.docxWorkers = parseInt(workers.value||6,10) }
          if(collect){ this.ooxml.ids.collect = collect.id; this.ooxml.docxCollectTokens = toBool(collect.value) }
        }
      } finally { this.ooxmlLoading = false }
    },
    async saveOoxmlSettings(){
      try{
        this.savingOoxml = true
        const token = localStorage.getItem('token')
        const hdrs = { 'Content-Type':'application/json', 'Authorization': `Bearer ${token}` }
        const reqs = []
        if(this.ooxml.ids.pptx){ reqs.push(fetch(`/api/admin/settings/${this.ooxml.ids.pptx}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.ooxml.pptx) }) })) }
        if(this.ooxml.ids.xlsx){ reqs.push(fetch(`/api/admin/settings/${this.ooxml.ids.xlsx}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.ooxml.xlsx) }) })) }
        if(this.ooxml.ids.workers){ reqs.push(fetch(`/api/admin/settings/${this.ooxml.ids.workers}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.ooxml.docxWorkers) }) })) }
        if(this.ooxml.ids.collect){ reqs.push(fetch(`/api/admin/settings/${this.ooxml.ids.collect}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.ooxml.docxCollectTokens) }) })) }
        const res = await Promise.all(reqs)
        if(!res.length || res.some(r => !r.ok)) throw new Error('保存失败')
        this.$message && this.$message.success ? this.$message.success(this.$t('settings.ooxmlSaved')) : null
        await this.loadOoxmlSettings()
      } catch(e){ this.$message && this.$message.error ? this.$message.error(e.message||this.$t('common.saveFailed')) : null }
      finally { this.savingOoxml = false }
    },
    async loadHistoryLimits(){
      try{
        this.limitsLoading = true
        const token = localStorage.getItem('token')
        const hdrs = token ? { 'Authorization': `Bearer ${token}` } : {}
        const resp = await fetch('/api/admin/settings?category=history', { headers: hdrs })
        if(resp.ok){
          const items = await resp.json()
          const get = (k, d) => {
            const row = items.find(i => i.key === k)
            return row ? parseInt(row.value || d, 10) : d
          }
          this.historyLimits.maxText = get('max_text_items_per_user', 1000)
          this.historyLimits.maxDoc = get('max_doc_items_per_user', 1000)
          const perm = items.find(i => i.key==='frontend_delete_permanent')
          this.historyLimits.permDelete = perm ? String(perm.value).toLowerCase() === 'true' : true
          this.historyLimits.textRetention = get('text_retention_days', 30)
          this.historyLimits.docRetention = get('doc_retention_days', 30)
        }
      } finally { this.limitsLoading = false }
    },
    async saveHistoryLimits(){
      try{
        this.savingLimits = true
        const token = localStorage.getItem('token')
        const hdrs = { 'Content-Type':'application/json', 'Authorization': `Bearer ${token}` }
        // 获取当前设置以拿到各自的ID
        const listResp = await fetch('/api/admin/settings?category=history', { headers: { 'Authorization': `Bearer ${token}` } })
        const items = listResp.ok ? await listResp.json() : []
        const byKey = k => items.find(i => i.key===k)
        const idText = (byKey('max_text_items_per_user')||{}).id
        const idDoc = (byKey('max_doc_items_per_user')||{}).id
        const idPerm = (byKey('frontend_delete_permanent')||{}).id
        const idTextRet = (byKey('text_retention_days')||{}).id
        const idDocRet = (byKey('doc_retention_days')||{}).id
        const reqs = []
        if(idText){ reqs.push(fetch(`/api/admin/settings/${idText}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.historyLimits.maxText) }) })) }
        if(idDoc){ reqs.push(fetch(`/api/admin/settings/${idDoc}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.historyLimits.maxDoc) }) })) }
        if(idPerm){ reqs.push(fetch(`/api/admin/settings/${idPerm}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.historyLimits.permDelete) }) })) }
        if(idTextRet){ reqs.push(fetch(`/api/admin/settings/${idTextRet}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.historyLimits.textRetention) }) })) }
        if(idDocRet){ reqs.push(fetch(`/api/admin/settings/${idDocRet}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.historyLimits.docRetention) }) })) }
        // 若某项不存在，则创建
        const create = async (key, value, value_type, description) => {
          return fetch('/api/admin/settings', { method:'POST', headers: hdrs, body: JSON.stringify({ category:'history', key, value: String(value), value_type, description }) })
        }
        if(!idPerm) reqs.push(create('frontend_delete_permanent', this.historyLimits.permDelete, 'bool', '小历史删除是否等同后台删除'))
        if(!idTextRet) reqs.push(create('text_retention_days', this.historyLimits.textRetention, 'int', '文本历史保留天数'))
        if(!idDocRet) reqs.push(create('doc_retention_days', this.historyLimits.docRetention, 'int', '文档历史保留天数（含文件）'))
        const res = await Promise.all(reqs)
        if(!res.length || res.some(r => !r.ok)) throw new Error(this.$t('common.saveFailed'))
        this.$message && this.$message.success ? this.$message.success(this.$t('settings.historySaved')) : null
        await this.loadHistoryLimits()
      } catch(e){ this.$message && this.$message.error ? this.$message.error(e.message||this.$t('common.saveFailed')) : null }
      finally{ this.savingLimits = false }
    },
    async loadTerminology(){
      try{
        this.terminologyLoading = true
        const resp = await fetch('/api/admin/settings?category=terminology', { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
        if(resp.ok){
          const items = await resp.json()
          const toBool = (v) => {
            if(v === null || v === undefined) return false
            const s = String(v).trim().toLowerCase()
            return ['1','true','yes','on'].includes(s)
          }
          const enabled = items.find(i => i.key === 'terminology_enabled')
          const caseSens = items.find(i => i.key === 'terminology_case_sensitive')
          const categoriesEnabled = items.find(i => i.key === 'terminology_categories_enabled')
          const maxCategories = items.find(i => i.key === 'terminology_max_categories_per_translation')
          const defaultCategories = items.find(i => i.key === 'terminology_default_categories')

          if(enabled){ this.terminology.enabledId = enabled.id; this.terminology.enabled = toBool(enabled.value) }
          if(caseSens){ this.terminology.caseId = caseSens.id; this.terminology.caseSensitive = toBool(caseSens.value) }
          if(categoriesEnabled){ this.terminology.categoriesEnabledId = categoriesEnabled.id; this.terminology.categoriesEnabled = toBool(categoriesEnabled.value) }
          if(maxCategories){ this.terminology.maxCategoriesId = maxCategories.id; this.terminology.maxCategories = parseInt(maxCategories.value || 5, 10) }
          if(defaultCategories){ this.terminology.defaultCategoriesId = defaultCategories.id; this.terminology.defaultCategories = JSON.parse(defaultCategories.value || '[]') }
        }
      } finally { this.terminologyLoading = false }
    },
    
    async loadAvailableCategories(){
      try{
        const resp = await fetch('/api/terminology/categories', { 
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } 
        })
        if(resp.ok){
          this.availableCategories = await resp.json()
        }
      } catch(e) {
        console.error('Failed to load categories:', e)
      }
    },
    
    async saveTerminology(){
      try{
        this.savingTerminology = true
        const reqs = []
        const hdrs = { 'Content-Type':'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        
        if(this.terminology.enabledId){
          reqs.push(fetch(`/api/admin/settings/${this.terminology.enabledId}`, { 
            method:'PUT', 
            headers: hdrs, 
            body: JSON.stringify({ value: String(this.terminology.enabled) }) 
          }))
        }
        
        if(this.terminology.caseId){
          reqs.push(fetch(`/api/admin/settings/${this.terminology.caseId}`, { 
            method:'PUT', 
            headers: hdrs, 
            body: JSON.stringify({ value: String(this.terminology.caseSensitive) }) 
          }))
        }
        
        if(this.terminology.categoriesEnabledId){
          reqs.push(fetch(`/api/admin/settings/${this.terminology.categoriesEnabledId}`, { 
            method:'PUT', 
            headers: hdrs, 
            body: JSON.stringify({ value: String(this.terminology.categoriesEnabled) }) 
          }))
        }
        
        if(this.terminology.maxCategoriesId){
          reqs.push(fetch(`/api/admin/settings/${this.terminology.maxCategoriesId}`, { 
            method:'PUT', 
            headers: hdrs, 
            body: JSON.stringify({ value: String(this.terminology.maxCategories) }) 
          }))
        }
        
        if(this.terminology.defaultCategoriesId){
          reqs.push(fetch(`/api/admin/settings/${this.terminology.defaultCategoriesId}`, { 
            method:'PUT', 
            headers: hdrs, 
            body: JSON.stringify({ value: JSON.stringify(this.terminology.defaultCategories) }) 
          }))
        }
        
        const res = await Promise.all(reqs)
        if(res.length && res.every(r => r.ok)){
          this.$message && this.$message.success ? this.$message.success(this.$t('settings.terminologySaved')) : null
          await this.loadTerminology()
        } else {
          this.$message && this.$message.error ? this.$message.error(this.$t('common.saveFailed')) : null
        }
      } finally { this.savingTerminology = false }
    },
    async loadStrategies(){
      try{
        this.loadingStrategies = true
        const resp = await fetch('/api/admin/settings/strategies', { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
        if(resp.ok){ this.strategies = await resp.json() }
      } finally { this.loadingStrategies = false }
    },
    async toggleStrategy(row, enable){
      const resp = await fetch(`/api/admin/settings/strategies/${row.strategy_name}`,{
        method:'PUT',
        headers:{ 'Content-Type':'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify({ status: enable })
      })
      if(!resp.ok){ this.$message.error(this.$t('common.updateFailed')); this.loadStrategies() } else { this.$message.success(this.$t('common.updated')) }
    },
    async loadEngines(){
      try{
        this.loadingEngines = true
        const resp = await fetch('/api/admin/engines', { headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
        if(resp.ok){ this.engines = await resp.json() }
      } finally { this.loadingEngines = false }
    },
    async toggleEngine(row){
      const resp = await fetch(`/api/admin/engines/${row.id}/toggle`,{ method:'POST', headers:{ 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
      if(resp.ok){ this.$message.success(this.$t('common.updated')); this.loadEngines() } else { this.$message.error(this.$t('common.updateFailed')) }
    },
    viewEngine(row){ this.selectedEngine = row; this.showViewDialog = true },
    openEdit(row){
      Object.assign(this.editForm, {
        id: row.id,
        engine_name: row.engine_name,
        display_name: row.display_name,
        description: row.description || '',
        status: row.status,
        priority: row.priority,
        rate_limit: row.rate_limit,
        cost_per_token: row.cost_per_token || 0,
        supported_languages: row.supported_languages || [],
        features: row.features || [],
        is_default: row.is_default,
        api_config: row.api_config || {},
        api_config_text: JSON.stringify(row.api_config || {}, null, 2)
      })
      this.showEditDialog = true
      // 载入 Qwen3 模型
      if(row.engine_name==='qwen3'){
        this.loadQwenModel()
        // 载入 qwen3 专用配置
        try{
          const cfg = row.api_config || {}
          this.qwen3Extras.max_workers = Number(cfg.max_workers ?? this.qwen3Extras.max_workers)
          this.qwen3Extras.batch_size = Number(cfg.batch_size ?? this.qwen3Extras.batch_size)
          this.qwen3Extras.timeout = Number(cfg.timeout ?? this.qwen3Extras.timeout)
          this.qwen3Extras.retry_max = Number(cfg.retry_max ?? this.qwen3Extras.retry_max)
          this.qwen3Extras.sleep_between_requests = Number(cfg.sleep_between_requests ?? this.qwen3Extras.sleep_between_requests)
        }catch{}
      }
    },
    async loadQwenModel(){
      try{
        const token = localStorage.getItem('token')
        const resp = await fetch('/api/admin/settings?category=engine_qwen3', { headers:{ 'Authorization': `Bearer ${token}` } })
        if(resp.ok){
          const arr = await resp.json()
          const m = arr.find(x=>x.key==='qwen3_model')
          this.qwen3Model = (m && (m.value||'')).toString() || 'qwen-mt-turbo'
        }
      }catch{}
    },
    async createEngine(){
      try{
        this.createLoading = true
        if(this.createForm.api_config_text && this.createForm.api_config_text.trim()){
          try{ this.createForm.api_config = JSON.parse(this.createForm.api_config_text) }catch{}
        } else {
          this.createForm.api_config = {}
        }
        const resp = await fetch('/api/admin/engines', {
          method:'POST',
          headers:{ 'Content-Type':'application/json','Authorization': `Bearer ${localStorage.getItem('token')}` },
          body: JSON.stringify(this.createForm)
        })
        if(resp.ok){ this.$message.success(this.$t('common.created')); this.showCreateDialog=false; this.resetCreateForm(); this.loadEngines() } else { const e=await resp.json(); this.$message.error(e.detail||this.$t('common.createFailed')) }
      } finally{ this.createLoading=false }
    },
    async updateEngine(){
      try{
        this.editLoading = true
        if(this.editForm.api_config_text && this.editForm.api_config_text.trim()){
          try{ this.editForm.api_config = JSON.parse(this.editForm.api_config_text) }catch{}
        }
        // 合并 Qwen3 专用配置到 api_config，以系统设置为准
        if(this.editForm.engine_name==='qwen3'){
          this.editForm.api_config = Object.assign({}, this.editForm.api_config || {}, {
            max_workers: this.qwen3Extras.max_workers,
            batch_size: this.qwen3Extras.batch_size,
            timeout: this.qwen3Extras.timeout,
            retry_max: this.qwen3Extras.retry_max,
            sleep_between_requests: this.qwen3Extras.sleep_between_requests,
            model: this.qwen3Model
          })
          // 同步文本视图，便于用户直接看到
          try{ this.editForm.api_config_text = JSON.stringify(this.editForm.api_config, null, 2) }catch{}
        }
        const resp = await fetch(`/api/admin/engines/${this.editForm.id}`, {
          method:'PUT',
          headers:{ 'Content-Type':'application/json','Authorization': `Bearer ${localStorage.getItem('token')}` },
          body: JSON.stringify(this.editForm)
        })
        if(resp.ok){
          // 若为 qwen3，则保存模型设置到系统设置
          if(this.editForm.engine_name==='qwen3'){
            const token = localStorage.getItem('token')
            // 读取是否已存在
            const list = await fetch('/api/admin/settings?category=engine_qwen3', { headers:{ 'Authorization': `Bearer ${token}` } })
            const items = list.ok ? await list.json() : []
            const row = items.find(i=>i.key==='qwen3_model')
            const hdrs = { 'Content-Type':'application/json','Authorization': `Bearer ${token}` }
            if(row && row.id){
              await fetch(`/api/admin/settings/${row.id}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: this.qwen3Model }) })
            }else{
              await fetch('/api/admin/settings', { method:'POST', headers: hdrs, body: JSON.stringify({ category:'engine_qwen3', key:'qwen3_model', value:this.qwen3Model, value_type:'string', description:'Qwen3 model' }) })
            }
          }
          this.$message.success(this.$t('common.updated'))
          this.showEditDialog=false; this.loadEngines()
        } else { const e=await resp.json(); this.$message.error(e.detail||this.$t('common.updateFailed')) }
      } finally{ this.editLoading=false }
    },
    async deleteEngine(row){
      try{
        if(this.$confirm){
          await this.$confirm(this.$t('settings.confirmDeleteEngine', { name: row.display_name }), this.$t('common.confirm'), { type:'warning' })
        } else {
          const ok = window.confirm(this.$t('settings.confirmDeleteEngine', { name: row.display_name }))
          if(!ok) return
        }
        const resp = await fetch(`/api/admin/engines/${row.id}`, { method:'DELETE', headers:{ 'Authorization': `Bearer ${localStorage.getItem('token')}` } })
        if(resp.ok){ this.$message && this.$message.success ? this.$message.success(this.$t('common.deleted')) : null; this.loadEngines() } else { const e=await resp.json(); this.$message && this.$message.error ? this.$message.error(e.detail||this.$t('common.deleteFailed')) : null }
      }catch(err){ /* 用户取消 */ }
    },
    resetCreateForm(){
      Object.assign(this.createForm, {engine_name:'',display_name:'',description:'',status:'active',priority:0,rate_limit:100,cost_per_token:0.0,supported_languages:[],features:[],is_default:false,api_config:{},api_config_text:''})
    },
    updateApiConfig(){
      try{ if(this.createForm.api_config_text.trim()){ this.createForm.api_config = JSON.parse(this.createForm.api_config_text) } else { this.createForm.api_config = {} } }catch{}
    },
    updateEditApiConfig(){
      try{ if(this.editForm.api_config_text.trim()){ this.editForm.api_config = JSON.parse(this.editForm.api_config_text) } else { this.editForm.api_config = {} } }catch{}
    },
    async loadPasswordPolicy(){
      try{
        this.passwordLoading = true
        const token = localStorage.getItem('token')
        const resp = await fetch('/api/admin/settings?category=security', { headers: { 'Authorization': `Bearer ${token}` } })
        if(resp.ok){
          const items = await resp.json()
          const byKey = k => items.find(i => i.key===k)
          const toBool = v => String(v).toLowerCase()==='true'
          const toInt = (v,d)=>{ const n=parseInt(v||d,10); return isNaN(n)?d:n }
          const min = byKey('password_min_length');
          const up = byKey('password_require_uppercase');
          const low = byKey('password_require_lowercase');
          const dig = byKey('password_require_digit');
          const spec = byKey('password_require_special');
          if(min){ this.passwordPolicy.ids.min = min.id; this.passwordPolicy.minLength = toInt(min.value,8) }
          if(up){ this.passwordPolicy.ids.up = up.id; this.passwordPolicy.requireUppercase = toBool(up.value) }
          if(low){ this.passwordPolicy.ids.low = low.id; this.passwordPolicy.requireLowercase = toBool(low.value) }
          if(dig){ this.passwordPolicy.ids.dig = dig.id; this.passwordPolicy.requireDigit = toBool(dig.value) }
          if(spec){ this.passwordPolicy.ids.spec = spec.id; this.passwordPolicy.requireSpecial = toBool(spec.value) }
        }
      } finally { this.passwordLoading = false }
    },
    async savePasswordPolicy(){
      try{
        this.savingPassword = true
        const token = localStorage.getItem('token')
        const hdrs = { 'Content-Type':'application/json', 'Authorization': `Bearer ${token}` }
        // 先尝试更新存在的
        const reqs = []
        const ids = this.passwordPolicy.ids
        if(ids.min){ reqs.push(fetch(`/api/admin/settings/${ids.min}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.passwordPolicy.minLength) }) })) }
        if(ids.up){ reqs.push(fetch(`/api/admin/settings/${ids.up}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.passwordPolicy.requireUppercase) }) })) }
        if(ids.low){ reqs.push(fetch(`/api/admin/settings/${ids.low}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.passwordPolicy.requireLowercase) }) })) }
        if(ids.dig){ reqs.push(fetch(`/api/admin/settings/${ids.dig}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.passwordPolicy.requireDigit) }) })) }
        if(ids.spec){ reqs.push(fetch(`/api/admin/settings/${ids.spec}`, { method:'PUT', headers: hdrs, body: JSON.stringify({ value: String(this.passwordPolicy.requireSpecial) }) })) }
        const res = await Promise.all(reqs)
        // 创建缺失的项
        const create = (key, value, value_type, description) => fetch('/api/admin/settings', { method:'POST', headers: hdrs, body: JSON.stringify({ category:'security', key, value:String(value), value_type, description }) })
        if(!ids.min) await create('password_min_length', this.passwordPolicy.minLength, 'int', '密码最小长度')
        if(!ids.up) await create('password_require_uppercase', this.passwordPolicy.requireUppercase, 'bool', '是否要求包含大写字母')
        if(!ids.low) await create('password_require_lowercase', this.passwordPolicy.requireLowercase, 'bool', '是否要求包含小写字母')
        if(!ids.dig) await create('password_require_digit', this.passwordPolicy.requireDigit, 'bool', '是否要求包含数字')
        if(!ids.spec) await create('password_require_special', this.passwordPolicy.requireSpecial, 'bool', '是否要求包含特殊字符')
        this.$message && this.$message.success ? this.$message.success(this.$t('settings.passwordSaved')) : null
        await this.loadPasswordPolicy()
      } catch(e){ this.$message && this.$message.error ? this.$message.error(e.message||this.$t('common.saveFailed')) : null }
      finally { this.savingPassword = false }
    }
  }
}
</script>

<style scoped>
.system-settings {
  padding: 20px;
}

.system-settings h3 {
  margin-bottom: 10px;
  color: #2c3e50;
}

.system-settings p {
  color: #7f8c8d;
}

.setting-description {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}
</style>