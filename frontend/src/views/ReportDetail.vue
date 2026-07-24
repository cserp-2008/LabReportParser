<template>
  <div class="report-detail">
    <el-page-header @back="$router.back()" style="margin-bottom: 20px;">
      <template #content>
        <div class="header-content">
          <span>报告详情</span>
          <div class="nav-buttons">
            <el-button
              :disabled="!prevReportId"
              @click="goToPrev"
              size="small"
              icon="ArrowLeft"
            >
              上一张化验单
            </el-button>
            <el-button
              :disabled="!nextReportId"
              @click="goToNext"
              size="small"
              icon="ArrowRight"
            >
              下一张化验单
            </el-button>
          </div>
        </div>
      </template>
    </el-page-header>
    
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card>
          <el-descriptions :column="4" border>
            <el-descriptions-item label="文件名">{{ report?.file_name }}</el-descriptions-item>
            <el-descriptions-item label="患者姓名">{{ report?.patient_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="性别">{{ report?.gender || '-' }}</el-descriptions-item>
            <el-descriptions-item label="年龄">{{ report?.age || '-' }}</el-descriptions-item>
            <el-descriptions-item label="医院">{{ report?.hospital_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="采样时间">{{ report?.sample_time ? formatDate(report.sample_time) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="质量分">
              <el-tag v-if="report?.quality_score" :type="report.quality_score >= 85 ? 'success' : 'warning'">
                {{ report.quality_score }}
              </el-tag>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="report?.review_status === 0 ? 'warning' : 'success'">
                {{ report?.review_status === 0 ? '未复核' : '已复核' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card style="height: 600px;">
          <template #header>
            <div class="card-header">
              <span>检验指标</span>
              <div>
                <el-button size="small" @click="clearHighlight">清除高亮</el-button>
              </div>
            </div>
          </template>
          <div class="results-container">
            <el-table :data="report?.results || []" height="500" @row-click="handleResultClick" highlight-current-row>
              <el-table-column prop="item_name" label="项目名称" width="150">
                <template #default="{ row }">
                  {{ row.item_name || row.raw_item_name }}
                </template>
              </el-table-column>
              <el-table-column prop="raw_value" label="结果" width="100" />
              <el-table-column prop="unit" label="单位" width="80" />
              <el-table-column label="参考范围" width="150">
                <template #default="{ row }">
                  {{ row.reference_text || (row.reference_low && row.reference_high ? `${row.reference_low}-${row.reference_high}` : '-') }}
                </template>
              </el-table-column>
              <el-table-column prop="flag" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag v-if="row.flag" type="danger" size="small">{{ row.flag }}</el-tag>
                  <span v-else>正常</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card style="height: 600px;">
          <template #header>
            <div class="card-header">
              <span>预览</span>
              <div class="reparse-controls">
                <el-select
                  v-model="selectedHospital"
                  placeholder="选择医院"
                  style="width: 220px; margin-right: 10px;"
                  size="small"
                >
                  <el-option
                    v-for="hospital in hospitalList"
                    :key="hospital.hospital_id"
                    :label="`${hospital.hospital_name} (${hospital.parser_code || '通用'})`"
                    :value="hospital.hospital_id"
                  />
                </el-select>
                <el-select
                  v-model="selectedParser"
                  placeholder="选择解析引擎"
                  style="width: 150px; margin-right: 10px;"
                  size="small"
                >
                  <el-option
                    v-for="parser in parserList"
                    :key="parser.code"
                    :label="parser.name"
                    :value="parser.code"
                  />
                </el-select>
                <el-button
                  size="small"
                  type="primary"
                  @click="handleReparse"
                  :loading="reparsing"
                >
                  重新识别
                </el-button>
              </div>
              <div v-if="highlightedResult" class="highlight-info">
                <span>高亮: {{ highlightedResult.item_name || highlightedResult.raw_item_name }}</span>
              </div>
            </div>
          </template>
          <div class="preview-container" ref="previewContainer">
            <el-skeleton v-if="pdfLoading" animated />
            <div v-else-if="pdfUrl" class="pdf-wrapper" ref="pdfWrapper">
              <iframe
                :src="pdfUrl"
                width="100%"
                height="500px"
                class="pdf-preview"
              />
              <canvas
                ref="highlightCanvas"
                class="highlight-canvas"
              />
            </div>
            <div v-else class="image-error">
              <el-icon><Picture /></el-icon>
              <p>暂无预览</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { reportApi, type ReportDetail as ReportDetailType, type LabResultItem } from '@/api'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const reportId = route.params.id as string
const report = ref<ReportDetailType | null>(null)
const currentResult = ref<any>(null)
const highlightedResult = ref<LabResultItem | null>(null)
const pdfUrl = ref<string>('')
const pdfLoading = ref<boolean>(false)
const previewContainer = ref<HTMLElement>()
const pdfWrapper = ref<HTMLElement>()
const highlightCanvas = ref<HTMLCanvasElement>()

const prevReportId = ref<string | null>(null)
const nextReportId = ref<string | null>(null)
const parserList = ref<any[]>([])
const hospitalList = ref<any[]>([])
const selectedParser = ref<string>('')
const selectedHospital = ref<number | null>(null)
const reparsing = ref<boolean>(false)

const currentPage = computed(() => {
  if (!report.value?.pages || report.value.pages.length === 0) return null
  return report.value.pages[0]
})

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const drawHighlight = () => {
  if (!highlightedResult.value || !highlightCanvas.value || !pdfWrapper.value) return
  
  const canvas = highlightCanvas.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  
  const wrapperRect = pdfWrapper.value.getBoundingClientRect()
  canvas.width = wrapperRect.width
  canvas.height = wrapperRect.height
  
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  const result = highlightedResult.value
  if (result.bbox_left !== undefined && result.bbox_top !== undefined && 
      result.bbox_right !== undefined && result.bbox_bottom !== undefined) {
    
    const scaleX = canvas.width / 595
    const scaleY = canvas.height / 842
    
    const left = result.bbox_left * scaleX
    const top = result.bbox_top * scaleY
    const width = (result.bbox_right - result.bbox_left) * scaleX
    const height = (result.bbox_bottom - result.bbox_top) * scaleY
    
    ctx.strokeStyle = '#FF0000'
    ctx.lineWidth = 2
    ctx.fillStyle = 'rgba(255, 0, 0, 0.1)'
    
    ctx.fillRect(left, top, width, height)
    ctx.strokeRect(left, top, width, height)
  }
}

const handleResultClick = (row: LabResultItem) => {
  currentResult.value = row
  highlightedResult.value = row
  
  nextTick(() => {
    drawHighlight()
  })
}

const clearHighlight = () => {
  highlightedResult.value = null
  if (highlightCanvas.value) {
    const ctx = highlightCanvas.value.getContext('2d')
    if (ctx) {
      ctx.clearRect(0, 0, highlightCanvas.value.width, highlightCanvas.value.height)
    }
  }
}

const loadPdf = async () => {
  if (!report.value?.report_id) return
  
  pdfLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/v1/preview/original/${report.value.report_id}`, {
      responseType: 'blob',
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    
    const blob = new Blob([response.data], { type: 'application/pdf' })
    pdfUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    console.error('Load PDF error:', error)
    ElMessage.error('加载PDF预览失败')
  } finally {
    pdfLoading.value = false
  }
}

const loadNeighbors = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/v1/report/${reportId}/neighbors`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    const data = response.data.data
    prevReportId.value = data.prev_report_id || null
    nextReportId.value = data.next_report_id || null
  } catch (error) {
    console.error('loadNeighbors error:', error)
  }
}

const goToPrev = () => {
  if (prevReportId.value) {
    router.push(`/report/${prevReportId.value}`)
  }
}

const goToNext = () => {
  if (nextReportId.value) {
    router.push(`/report/${nextReportId.value}`)
  }
}

const loadReport = async () => {
  try {
    const res = await reportApi.getDetail(reportId)
    report.value = res.data
    await loadPdf()
    await loadNeighbors()
  } catch (error) {
    console.error('loadReport error:', error)
    ElMessage.error('加载失败')
  }
}

const loadParserList = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/v1/report/parser/list', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    parserList.value = response.data.data || []
  } catch (error) {
    console.error('loadParserList error:', error)
  }
}

const loadHospitalList = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/v1/hospital/list', {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    hospitalList.value = response.data.data?.list || response.data.data || []
  } catch (error) {
    console.error('loadHospitalList error:', error)
  }
}

const handleReparse = async () => {
  if (!report.value?.report_id) return
  
  reparsing.value = true
  try {
    const token = localStorage.getItem('token')
    const params: any = {}
    if (selectedParser.value) {
      params.parser_code = selectedParser.value
    }
    if (selectedHospital.value) {
      params.hospital_id = selectedHospital.value
    }
    
    const response = await axios.post(`/api/v1/report/${reportId}/reparse`, null, {
      params,
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    
    ElMessage.success(`重新识别完成，识别 ${response.data.data?.result_count || 0} 个指标`)
    await loadReport()
  } catch (error) {
    console.error('reparse error:', error)
    ElMessage.error('重新识别失败')
  } finally {
    reparsing.value = false
  }
}

onMounted(() => {
  loadReport()
  loadParserList()
  loadHospitalList()
  
  const resizeObserver = new ResizeObserver(() => {
    if (highlightedResult.value) {
      drawHighlight()
    }
  })
  
  if (pdfWrapper.value) {
    resizeObserver.observe(pdfWrapper.value)
  }
})

onUnmounted(() => {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
  }
})

watch(highlightedResult, () => {
  nextTick(() => {
    drawHighlight()
  })
})
</script>

<style scoped>
.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.nav-buttons {
  display: flex;
  gap: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.reparse-controls {
  display: flex;
  align-items: center;
  margin-right: 10px;
}

.highlight-info {
  font-size: 12px;
  color: #F56C6C;
}

.results-container {
  overflow: auto;
}

.preview-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 500px;
}

.pdf-wrapper {
  position: relative;
  width: 100%;
  height: 500px;
}

.pdf-preview {
  border: none;
}

.highlight-canvas {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

.image-error {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #999;
  height: 100%;
}

.image-error .el-icon {
  font-size: 48px;
  margin-bottom: 10px;
}
</style>
