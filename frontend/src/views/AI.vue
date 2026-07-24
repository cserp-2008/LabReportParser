<template>
  <div class="ai-page">
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="AI识别" name="recognize">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>AI化验单识别</span>
              <el-button type="primary" :loading="recognizing" @click="handleRecognize">
                开始识别
              </el-button>
            </div>
          </template>

          <el-upload
            class="upload-dragger"
            drag
            multiple
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :file-list="fileList"
            accept=".pdf,.jpg,.jpeg,.png,.bmp,.tif,.tiff"
            :disabled="recognizing"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF、JPG、PNG、BMP、TIF 等格式文件
              </div>
            </template>
          </el-upload>

          <div v-if="recognizeItems.length > 0" class="file-list">
            <div v-for="item in recognizeItems" :key="item.uid" class="file-item">
              <div class="file-header">
                <el-icon><Document /></el-icon>
                <span class="file-name" :title="item.name">{{ item.name }}</span>
                <span class="file-size">{{ formatSize(item.size) }}</span>
                <el-tag :type="getStatusType(item.status)" size="small">
                  {{ getStatusText(item.status) }}
                </el-tag>
              </div>
              <div v-if="item.progress > 0 && item.progress < 100" class="progress-row">
                <span class="progress-label">识别中</span>
                <el-progress
                  :percentage="item.progress"
                  :stroke-width="10"
                  status="success"
                  :show-text="true"
                />
              </div>
            </div>
          </div>

          <div v-if="recognizeResults.length > 0" class="result-summary">
            <el-divider content-position="left">识别结果汇总</el-divider>
            <el-table :data="recognizeResults" border>
              <el-table-column prop="fileName" label="文件名" />
              <el-table-column prop="patientName" label="患者" />
              <el-table-column prop="resultCount" label="指标数" />
              <el-table-column prop="pageCount" label="页数" />
              <el-table-column label="AI识别">
                <template #default="{ row }">
                  <el-tag :type="row.aiUsed ? 'success' : 'warning'">
                    {{ row.aiUsed ? '是' : '否（传统解析）' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="fallbackReason" label="备注" width="200">
                <template #default="{ row }">
                  <span v-if="row.fallbackReason" class="fallback-reason">
                    {{ row.fallbackReason }}
                  </span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
                    {{ row.status === 'success' ? '成功' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作">
                <template #default="{ row }">
                  <el-button v-if="row.status === 'success' && row.reportId" size="small" @click="goToReport(row.reportId)">
                    查看详情
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="AI配置" name="config">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>AI服务配置</span>
              <el-button type="primary" @click="saveConfig">保存配置</el-button>
            </div>
          </template>

          <el-form :model="configForm" label-width="100px">
            <el-form-item label="API Key">
              <el-input v-model="configForm.apiKey" type="password" show-password placeholder="请输入API Key" />
              <span class="form-hint">API Key用于访问火山方舟AI服务</span>
            </el-form-item>
            <el-form-item label="Base URL">
              <el-input v-model="configForm.baseUrl" placeholder="请输入API接入点地址" />
              <span class="form-hint">火山方舟官方地址: https://ark.cn-beijing.volces.com/api/v3</span>
            </el-form-item>
            <el-form-item label="模型名称">
              <el-input v-model="configForm.modelName" placeholder="请输入模型名称" />
              <span class="form-hint">如: doubao-3-256k、qwen-vl-plus等</span>
            </el-form-item>
            <el-form-item label="提示词">
              <el-input v-model="configForm.prompt" type="textarea" :rows="10" placeholder="请输入识别提示词" />
              <span class="form-hint">用于指导AI识别化验单内容的提示词</span>
            </el-form-item>
          </el-form>

          <div style="margin-top: 20px;">
            <el-button type="success" @click="testConfig" :loading="testing">
              测试连接
            </el-button>
            <el-button @click="resetPrompt" style="margin-left: 10px;">
              恢复默认提示词
            </el-button>
          </div>

          <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'error'">
            {{ testResult.message }}
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type UploadUserFile } from 'element-plus'
import { aiApi } from '../api'

const router = useRouter()
const activeTab = ref('recognize')
const fileList = ref<UploadUserFile[]>([])
const recognizing = ref(false)
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

interface RecognizeItem {
  uid: string
  name: string
  size: number
  status: 'pending' | 'recognizing' | 'success' | 'failed'
  progress: number
  reportId?: string
  patientName?: string
  resultCount?: number
  pageCount?: number
  aiUsed?: boolean
  fallbackReason?: string
  error?: string
}

const recognizeItems = ref<RecognizeItem[]>([])
const recognizeResults = ref<Array<{
  fileName: string
  patientName: string
  resultCount: number
  pageCount: number
  status: 'success' | 'failed'
  reportId?: string
}>>([])

const configForm = reactive({
  apiKey: '',
  baseUrl: 'https://ark.cn-beijing.volces.com/api/v3',
  modelName: '',
  prompt: ''
})

const formatSize = (bytes: number) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    recognizing: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待中',
    recognizing: '识别中',
    success: '成功',
    failed: '失败'
  }
  return map[status] || status
}

const handleFileChange = (file: UploadUserFile, files: UploadUserFile[]) => {
  fileList.value = files
}

const handleFileRemove = (file: UploadUserFile, files: UploadUserFile[]) => {
  fileList.value = files
}

const handleRecognize = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  recognizing.value = true
  recognizeItems.value = fileList.value.map(f => ({
    uid: f.uid || String(Math.random()),
    name: f.name,
    size: (f.raw as File)?.size || 0,
    status: 'pending' as const,
    progress: 0
  }))
  recognizeResults.value = []

  const results: Array<{
    fileName: string
    patientName: string
    resultCount: number
    pageCount: number
    status: 'success' | 'failed'
    reportId?: string
  }> = []

  for (let i = 0; i < fileList.value.length; i++) {
    const file = fileList.value[i]
    const item = recognizeItems.value[i]
    const rawFile = file.raw as File

    item.status = 'recognizing'
    item.progress = 10

    try {
      const res = await aiApi.recognizeFile(rawFile)
      const data = res.data?.data || res.data

      item.progress = 100
      item.status = 'success'
      item.reportId = data.report_id
      item.patientName = data.patient?.name || ''
      item.resultCount = data.result_count || 0
      item.pageCount = data.page_count || 0
      item.aiUsed = data.ai_used
      item.fallbackReason = data.fallback_reason

      results.push({
        fileName: file.name,
        patientName: data.patient?.name || '',
        resultCount: data.result_count || 0,
        pageCount: data.page_count || 0,
        status: 'success',
        reportId: data.report_id,
        aiUsed: data.ai_used,
        fallbackReason: data.fallback_reason
      })
    } catch (error: any) {
      item.progress = 100
      item.status = 'failed'
      item.error = error?.response?.data?.msg || error?.message || '识别失败'

      results.push({
        fileName: file.name,
        patientName: '',
        resultCount: 0,
        pageCount: 0,
        status: 'failed',
        aiUsed: false
      })
    }
  }

  recognizeResults.value = results
  recognizing.value = false

  const successCount = results.filter(r => r.status === 'success').length
  if (successCount > 0) {
    ElMessage.success(`成功识别 ${successCount} 个文件`)
  }
}

const goToReport = (reportId: string) => {
  router.push(`/report/${reportId}`)
}

const loadConfig = async () => {
  try {
    const res = await aiApi.getConfig()
    const data = res.data?.data || res.data
    if (data) {
      configForm.apiKey = data.api_key || ''
      configForm.baseUrl = data.base_url || 'https://ark.cn-beijing.volces.com/api/v3'
      configForm.modelName = data.model_name || ''
      configForm.prompt = data.prompt || ''
    }
  } catch {
    const res = await aiApi.getDefaultPrompt()
    configForm.prompt = (res.data?.data || res.data)?.prompt || ''
  }
}

const saveConfig = async () => {
  if (!configForm.apiKey || !configForm.baseUrl || !configForm.modelName) {
    ElMessage.warning('请填写完整配置信息')
    return
  }

  try {
    await aiApi.saveConfig(configForm.apiKey, configForm.baseUrl, configForm.modelName, configForm.prompt)
    ElMessage.success('配置保存成功')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || '保存失败')
  }
}

const testConfig = async () => {
  testing.value = true
  try {
    const res = await aiApi.testConfig()
    const data = res.data?.data || res.data
    testResult.value = {
      success: data.success,
      message: data.message + (data.available_models ? `\n可用模型: ${data.available_models.join(', ')}` : '')
    }
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: error?.response?.data?.msg || '测试失败'
    }
  } finally {
    testing.value = false
  }
}

const resetPrompt = async () => {
  try {
    const res = await aiApi.getDefaultPrompt()
    configForm.prompt = (res.data?.data || res.data)?.prompt || ''
    ElMessage.success('已恢复默认提示词')
  } catch {
    ElMessage.error('获取默认提示词失败')
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-dragger {
  width: 100%;
}

.file-list {
  margin-top: 20px;
  max-height: 400px;
  overflow-y: auto;
}

.file-item {
  padding: 12px 16px;
  margin-bottom: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}

.file-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.file-name {
  flex: 1;
  font-weight: 500;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: #909399;
  font-size: 12px;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}

.progress-label {
  width: 50px;
  font-size: 12px;
  color: #606266;
  flex-shrink: 0;
}

.progress-row :deep(.el-progress) {
  flex: 1;
}

.result-summary {
  margin-top: 20px;
}

.form-hint {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.test-result {
  margin-top: 15px;
  padding: 12px;
  border-radius: 4px;
  font-size: 14px;
}

.test-result.success {
  background-color: #f0f9eb;
  color: #67c23a;
}

.test-result.error {
  background-color: #fef0f0;
  color: #f56c6c;
}
</style>