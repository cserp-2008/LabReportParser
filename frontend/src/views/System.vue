<template>
  <div class="system">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统配置</span>
          <el-button type="primary" @click="saveConfig">
            <el-icon><Save /></el-icon>
            保存配置
          </el-button>
        </div>
      </template>

      <el-form :model="config" label-width="150px">
        <el-divider content-position="left">解析配置</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="OCR引擎">
              <el-select v-model="config.ocr_engine" placeholder="请选择OCR引擎">
                <el-option label="PaddleOCR" value="paddle" />
                <el-option label="Tesseract" value="tesseract" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="图片质量阈值">
              <el-input-number v-model="config.quality_threshold" :min="0" :max="100" />
              <span style="margin-left: 10px;">分</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大文件大小">
              <el-input-number v-model="config.max_file_size" :min="1" :max="50" />
              <span style="margin-left: 10px;">MB</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大页数">
              <el-input-number v-model="config.max_pages" :min="1" :max="100" />
              <span style="margin-left: 10px;">页</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="自动解析">
          <el-switch v-model="config.auto_parse" />
        </el-form-item>

        <el-divider content-position="left">存储配置</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="存储类型">
              <el-select v-model="config.storage_type" placeholder="请选择存储类型">
                <el-option label="本地存储" value="local" />
                <el-option label="云存储" value="cloud" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="存储路径">
              <el-input v-model="config.storage_path" placeholder="文件存储路径" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="保留原始文件">
          <el-switch v-model="config.keep_original" />
        </el-form-item>

        <el-divider content-position="left">安全配置</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="会话超时时间">
              <el-input-number v-model="config.session_timeout" :min="15" :max="1440" />
              <span style="margin-left: 10px;">分钟</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码最小长度">
              <el-input-number v-model="config.min_password_length" :min="6" :max="32" />
              <span style="margin-left: 10px;">位</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="失败重试次数">
          <el-input-number v-model="config.max_retry_count" :min="0" :max="10" />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const config = reactive({
  ocr_engine: 'paddle',
  quality_threshold: 80,
  max_file_size: 20,
  max_pages: 20,
  auto_parse: true,
  storage_type: 'local',
  storage_path: './data/uploads',
  keep_original: true,
  session_timeout: 120,
  min_password_length: 6,
  max_retry_count: 3
})

const loadConfig = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/v1/system/config', {
      headers: { Authorization: `Bearer ${token}` }
    })
    Object.assign(config, response.data.data)
  } catch (error) {
    console.error('加载配置失败:', error)
  }
}

const saveConfig = async () => {
  try {
    const token = localStorage.getItem('token')
    await axios.post('/api/v1/system/config', config, {
      headers: { Authorization: `Bearer ${token}` }
    })
    ElMessage.success('配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
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
</style>
