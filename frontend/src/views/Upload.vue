<template>
  <div class="upload">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>上传报告</span>
        </div>
      </template>

      <el-upload
        class="upload-dragger"
        drag
        multiple
        action="#"
        :auto-upload="false"
        :on-change="handleChange"
        :on-remove="handleRemove"
        :file-list="fileList"
        accept=".pdf,.jpg,.jpeg,.png,.bmp,.tif,.tiff"
        :disabled="uploading"
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

      <div v-if="fileList.length > 0" style="margin-top: 20px;">
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          开始上传（{{ fileList.length }} 个文件）
        </el-button>
        <el-button @click="clearAll" :disabled="uploading">清空</el-button>
      </div>

      <!-- 文件列表及进度 -->
      <div v-if="uploadItems.length > 0" class="file-list">
        <div v-for="item in uploadItems" :key="item.uid" class="file-item">
          <div class="file-header">
            <el-icon><Document /></el-icon>
            <span class="file-name" :title="item.name">{{ item.name }}</span>
            <span class="file-size">{{ formatSize(item.size) }}</span>
            <el-tag :type="getStatusType(item.status)" size="small">
              {{ getStatusText(item.status) }}
            </el-tag>
            <el-button
              v-if="item.status === 'failed'"
              size="small"
              type="primary"
              @click="retryUpload(item)"
              :loading="item.retrying"
            >
              继续上传
            </el-button>
          </div>
          <!-- 上传进度（绿色） -->
          <div v-if="item.uploadProgress > 0 && item.uploadProgress < 100" class="progress-row">
            <span class="progress-label">上传中</span>
            <el-progress
              :percentage="item.uploadProgress"
              :stroke-width="10"
              status="success"
              :show-text="true"
            />
          </div>
          <!-- 解析进度（红色） -->
          <div v-if="item.parsing && item.parseProgress < 100" class="progress-row">
            <span class="progress-label">解析中</span>
            <el-progress
              :percentage="item.parseProgress"
              :stroke-width="10"
              status="exception"
              :show-text="true"
              :indeterminate="item.parseProgress === 0"
            />
          </div>
        </div>
      </div>
    </el-card>

    <!-- 过程日志 -->
    <el-card v-if="logs.length > 0" class="log-card">
      <template #header>
        <div class="card-header">
          <span>过程日志</span>
          <el-button size="small" @click="clearLogs">清空日志</el-button>
        </div>
      </template>
      <div class="log-container" ref="logContainer">
        <div
          v-for="(log, idx) in logs"
          :key="idx"
          class="log-line"
          :class="`log-${log.level}`"
        >
          <span class="log-time">{{ log.time }}</span>
          <span class="log-level">[{{ log.level }}]</span>
          <span class="log-msg">{{ log.message }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadUserFile } from 'element-plus'
import { uploadApi } from '../api'

const router = useRouter()
const fileList = ref<UploadUserFile[]>([])
const uploading = ref(false)
const logs = ref<Array<{ time: string; level: string; message: string }>>([])
const logContainer = ref<HTMLElement | null>(null)

interface UploadItem {
  uid: string
  name: string
  size: number
  status: 'pending' | 'uploading' | 'uploaded' | 'parsing' | 'success' | 'failed'
  uploadProgress: number
  parseProgress: number
  parsing: boolean
  retrying: boolean
  error?: string
  resultCount?: number
  qualityScore?: number
}

const uploadItems = ref<UploadItem[]>([])

const formatSize = (bytes: number) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    uploading: 'warning',
    uploaded: 'primary',
    parsing: 'warning',
    success: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '等待中',
    uploading: '上传中',
    uploaded: '已上传',
    parsing: '解析中',
    success: '完成',
    failed: '失败',
  }
  return map[status] || status
}

const handleChange = (file: UploadUserFile, files: UploadUserFile[]) => {
  fileList.value = files
}

const handleRemove = (file: UploadUserFile, files: UploadUserFile[]) => {
  fileList.value = files
}

const clearAll = () => {
  fileList.value = []
  uploadItems.value = []
}

const addLog = (level: string, message: string) => {
  const now = new Date()
  const time = now.toLocaleTimeString('zh-CN', { hour12: false }) + '.' +
    String(now.getMilliseconds()).padStart(3, '0')
  logs.value.push({ time, level, message })
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

const clearLogs = () => {
  logs.value = []
}

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

const handleUpload = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true

  // 初始化上传项
  uploadItems.value = fileList.value.map(f => ({
    uid: f.uid || String(Math.random()),
    name: f.name,
    size: (f.raw as File)?.size || 0,
    status: 'pending',
    uploadProgress: 0,
    parseProgress: 0,
    parsing: false,
    retrying: false,
  }))

  addLog('info', `开始并行上传 ${fileList.value.length} 个文件`)

  // 单个文件的完整处理流程：上传 + 解析
  const processFile = async (index: number, overwrite: boolean = false): Promise<{ success: boolean; duplicate: boolean }> => {
    const file = fileList.value[index]
    const item = uploadItems.value[index]
    const rawFile = file.raw as File
    const tag = `[${index + 1}/${fileList.value.length}]`

    addLog('info', `${tag} 开始上传: ${file.name}`)
    item.status = 'uploading'
    item.uploadProgress = 0

    try {
      const res = await uploadApi.uploadFile(rawFile, (progress) => {
        item.uploadProgress = progress
      }, overwrite)

      const data = res.data?.data || res.data

      // 检查是否重复
      if (data?.duplicate) {
        item.status = 'pending'
        item.uploadProgress = 0
        addLog('warning', `${tag} 文件已存在: ${file.name}（上传于 ${data.existing_create_time || '未知时间'}）`)
        return { success: false, duplicate: true }
      }

      item.uploadProgress = 100
      item.status = 'uploaded'
      addLog('success', `${tag} 上传完成: ${file.name}`)

      // 解析阶段
      item.parsing = true
      item.status = 'parsing'
      item.parseProgress = 10
      addLog('info', `${tag} 开始解析: ${file.name}`)

      const parseSteps = data?.parse_steps || []
      const parseError = data?.parse_error
      const parseResult = data?.parse_result

      // 逐步显示解析进度
      for (let s = 0; s < parseSteps.length; s++) {
        await sleep(150)
        item.parseProgress = 10 + Math.round((s + 1) / parseSteps.length * 80)
        addLog('info', `  ${tag} → ${parseSteps[s]}`)
      }

      if (parseError) {
        item.parseProgress = 100
        item.status = 'failed'
        item.error = parseError
        addLog('error', `${tag} 解析失败: ${parseError}`)
        return { success: false, duplicate: false }
      }

      item.parseProgress = 100
      item.parsing = false
      item.status = 'success'
      item.resultCount = parseResult?.result_count
      item.qualityScore = parseResult?.quality_score
      addLog('success', `${tag} 解析完成: 指标 ${item.resultCount || 0} 个，质量分 ${item.qualityScore || 0}`)
      return { success: true, duplicate: false }
    } catch (error: any) {
      item.status = 'failed'
      item.error = error?.response?.data?.detail || error?.message || '上传失败'
      addLog('error', `${tag} 上传失败: ${item.error}`)
      return { success: false, duplicate: false }
    }
  }

  // 第一轮：并行上传所有文件（不覆盖）
  const results = await Promise.all(
    fileList.value.map((_, idx) => processFile(idx, false))
  )

  let successCount = results.filter(r => r.success).length
  const duplicateIndices = results.map((r, idx) => r.duplicate ? idx : -1).filter(idx => idx >= 0)

  // 如果有重复文件，弹出确认框
  if (duplicateIndices.length > 0) {
    const duplicateFiles = duplicateIndices.map(idx => fileList.value[idx].name).join('、')
    addLog('warning', `检测到 ${duplicateIndices.length} 个重复文件：${duplicateFiles}`)

    try {
      await ElMessageBox.confirm(
        `以下 ${duplicateIndices.length} 个文件已存在：\n${duplicateFiles}\n\n是否覆盖已存在的报告？`,
        '文件重复提示',
        {
          confirmButtonText: '覆盖上传',
          cancelButtonText: '跳过重复文件',
          type: 'warning',
        }
      )

      // 用户选择覆盖，重新上传重复文件
      addLog('info', `开始覆盖上传 ${duplicateIndices.length} 个重复文件`)
      const overwriteResults = await Promise.all(
        duplicateIndices.map(idx => processFile(idx, true))
      )
      const overwriteSuccess = overwriteResults.filter(r => r.success).length
      successCount += overwriteSuccess
      addLog('success', `覆盖上传完成：成功 ${overwriteSuccess} 个`)
    } catch {
      // 用户选择跳过
      addLog('info', `已跳过 ${duplicateIndices.length} 个重复文件`)
      duplicateIndices.forEach(idx => {
        uploadItems.value[idx].status = 'failed'
        uploadItems.value[idx].error = '已跳过（文件已存在）'
      })
    }
  }

  const failCount = fileList.value.length - successCount
  addLog('info', `全部完成：成功 ${successCount} 个，跳过/失败 ${failCount} 个`)
  uploading.value = false

  if (successCount > 0) {
    ElMessage.success(`成功上传并解析 ${successCount} 个文件`)
  }
}

const retryUpload = async (item: UploadItem) => {
  const index = uploadItems.value.findIndex(i => i.uid === item.uid)
  if (index === -1) return

  const file = fileList.value[index]
  const rawFile = file.raw as File
  const tag = `[重试 ${index + 1}/${fileList.value.length}]`

  addLog('info', `${tag} 开始重试上传: ${file.name}`)
  item.retrying = true
  item.status = 'uploading'
  item.uploadProgress = 0
  item.error = undefined

  try {
    const res = await uploadApi.uploadFile(rawFile, (progress) => {
      item.uploadProgress = progress
    }, false)

    const data = res.data?.data || res.data

    if (data?.duplicate) {
      item.status = 'pending'
      item.uploadProgress = 0
      item.retrying = false
      addLog('warning', `${tag} 文件已存在: ${file.name}（上传于 ${data.existing_create_time || '未知时间'}）`)
      return
    }

    item.uploadProgress = 100
    item.status = 'uploaded'
    item.retrying = false
    addLog('success', `${tag} 上传完成: ${file.name}`)

    item.parsing = true
    item.status = 'parsing'
    item.parseProgress = 10
    addLog('info', `${tag} 开始解析: ${file.name}`)

    const parseSteps = data?.parse_steps || []
    const parseError = data?.parse_error
    const parseResult = data?.parse_result

    for (let s = 0; s < parseSteps.length; s++) {
      await sleep(150)
      item.parseProgress = 10 + Math.round((s + 1) / parseSteps.length * 80)
      addLog('info', `  ${tag} → ${parseSteps[s]}`)
    }

    if (parseError) {
      item.parseProgress = 100
      item.status = 'failed'
      item.error = parseError
      addLog('error', `${tag} 解析失败: ${parseError}`)
      return
    }

    item.parseProgress = 100
    item.parsing = false
    item.status = 'success'
    item.resultCount = parseResult?.result_count
    item.qualityScore = parseResult?.quality_score
    addLog('success', `${tag} 解析完成: 指标 ${item.resultCount || 0} 个，质量分 ${item.qualityScore || 0}`)
    ElMessage.success(`文件 ${file.name} 重试成功`)
  } catch (error: any) {
    item.status = 'failed'
    item.error = error?.response?.data?.detail || error?.message || '上传失败'
    item.retrying = false
    addLog('error', `${tag} 重试失败: ${item.error}`)
    ElMessage.error(`文件 ${file.name} 重试失败，请稍后再试`)
  }
}
</script>

<style scoped>
.upload-dragger {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.log-card {
  margin-top: 20px;
}

.log-container {
  max-height: 300px;
  overflow-y: auto;
  background-color: #1e1e1e;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-line {
  display: flex;
  gap: 8px;
  color: #d4d4d4;
}

.log-time {
  color: #858585;
  flex-shrink: 0;
}

.log-level {
  flex-shrink: 0;
  width: 60px;
}

.log-info .log-level {
  color: #569cd6;
}

.log-success .log-level {
  color: #4ec9b0;
}

.log-error .log-level {
  color: #f44747;
}

.log-error .log-msg {
  color: #f44747;
}

.log-success .log-msg {
  color: #b5cea8;
}
</style>
