<template>
  <div class="review-detail">
    <div class="review-header">
      <el-page-header @back="$router.back()" content="报告审核" style="margin-bottom: 20px;" />
      <div class="nav-buttons">
        <el-button type="primary" plain size="small" :disabled="!prevReportId" @click="goPrevReport">
          <el-icon><ArrowLeft /></el-icon> 上一报告
        </el-button>
        <span v-if="prevReportId || nextReportId" class="nav-info">
          {{ prevReportId ? prevFileName : '无' }} | {{ nextReportId ? nextFileName : '无' }}
        </span>
        <el-button type="primary" plain size="small" :disabled="!nextReportId" @click="goNextReport">
          下一报告 <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <el-card v-if="report">
      <el-descriptions :column="4" border>
        <el-descriptions-item label="文件名">{{ report.file_name }}</el-descriptions-item>
        <el-descriptions-item label="患者姓名">{{ report.patient_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ report.gender || '-' }}</el-descriptions-item>
        <el-descriptions-item label="年龄">{{ report.age || '-' }}</el-descriptions-item>
        <el-descriptions-item label="医院">{{ report.hospital_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="采样时间">{{ report.sample_time ? formatDate(report.sample_time) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="报告时间">{{ report.report_time ? formatDate(report.report_time) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getReviewStatusType(report.review_status)">
            {{ getReviewStatusText(report.review_status) }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>化验信息</span>
              <div class="header-actions">
                <el-button type="primary" size="small" @click="saveAll" :disabled="!isEditing">保存所有修改</el-button>
                <el-button type="success" size="small" @click="addRow" :disabled="!isEditing">新增指标</el-button>
                <el-button type="warning" size="small" @click="toggleEdit">{{ isEditing ? '退出编辑' : '编辑' }}</el-button>
              </div>
            </div>
          </template>
          <el-table :data="results" v-loading="loading" :row-key="(row) => row.result_id || row._temp_id" size="small">
            <el-table-column prop="raw_item_name" label="指标名称" min-width="150">
              <template #default="{ row }">
                <el-input
                  v-if="isEditing || row._temp_id"
                  v-model="row.raw_item_name"
                  size="small"
                  placeholder="请输入指标名称"
                />
                <span v-else>{{ row.raw_item_name || row.item_name }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="raw_value" label="化验结果" min-width="80">
              <template #default="{ row }">
                <el-input
                  v-if="isEditing || row._temp_id"
                  v-model="row.raw_value"
                  size="small"
                  placeholder="请输入结果"
                />
                <span v-else>{{ row.raw_value || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="70">
              <template #default="{ row }">
                <el-input
                  v-if="isEditing || row._temp_id"
                  v-model="row.unit"
                  size="small"
                  placeholder="单位"
                />
                <span v-else>{{ row.unit || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="reference_text" label="参考区间" min-width="140">
              <template #default="{ row }">
                <el-input
                  v-if="isEditing || row._temp_id"
                  v-model="row.reference_text"
                  size="small"
                  placeholder="参考区间"
                />
                <span v-else>{{ row.reference_text || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="flag" label="是否正常" width="80">
              <template #default="{ row }">
                <el-select
                  v-if="isEditing || row._temp_id"
                  v-model="row.flag"
                  size="small"
                  style="width: 70px;"
                >
                  <el-option label="正常" value="" />
                  <el-option label="↑" value="↑" />
                  <el-option label="↓" value="↓" />
                </el-select>
                <el-tag v-else-if="row.flag === '↑'" type="danger" size="small">↑</el-tag>
                <el-tag v-else-if="row.flag === '↓'" type="warning" size="small">↓</el-tag>
                <span v-else>正常</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" v-if="isEditing">
              <template #default="{ row }">
                <template v-if="row._temp_id">
                  <el-button type="success" link size="small" @click="saveNewRow(row)">保存</el-button>
                  <el-button type="danger" link size="small" @click="removeNewRow(row)">删除</el-button>
                </template>
                <template v-else>
                  <el-button
                    type="danger"
                    link
                    size="small"
                    @click="deleteRow(row)"
                  >删除</el-button>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>报告预览</span>
              <div class="header-actions">
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
                <el-button type="warning" size="small" @click="reparseReport">
                  <el-icon><Refresh /></el-icon>
                  重新识别
                </el-button>
              </div>
            </div>
          </template>
          <div class="preview-container">
            <el-skeleton v-if="pdfLoading" animated />
            <div v-else-if="pdfUrl" class="pdf-wrapper">
              <iframe
                :src="pdfUrl"
                width="100%"
                height="550px"
                class="pdf-preview"
              />
            </div>
            <div v-else class="image-error">
              <el-icon><Picture /></el-icon>
              <p>暂无预览</p>
            </div>
          </div>
        </el-card>

        <el-card style="margin-top: 20px;">
          <template #header>
            <span>操作</span>
          </template>
          <div class="action-buttons">
            <el-button type="success" @click="markReviewed">标记已复核</el-button>
            <el-button type="info" @click="markManual">标记人工修改</el-button>
            <el-button type="warning" @click="markPending">标记未复核</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const reportId = ref(route.params.id as string)

const report = ref<any>(null)
const results = ref<any[]>([])
const loading = ref(false)
const pdfLoading = ref(false)
const pdfUrl = ref<string>('')
const isEditing = ref(false)
const hospitalList = ref<any[]>([])
const selectedHospital = ref<number | null>(null)
let tempIdCounter = 0

const prevReportId = ref<string | null>(null)
const nextReportId = ref<string | null>(null)
const prevFileName = ref<string>('')
const nextFileName = ref<string>('')

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const getReviewStatusType = (status: number) => {
  switch (status) {
    case 0: return 'warning'
    case 1: return 'success'
    case 2: return 'info'
    default: return 'default'
  }
}

const getReviewStatusText = (status: number) => {
  switch (status) {
    case 0: return '未复核'
    case 1: return '已复核'
    case 2: return '人工修改'
    default: return '未知'
  }
}

const loadReport = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/v1/report/${reportId.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    report.value = response.data.data
    results.value = response.data.data.results.map((item: any) => ({
      ...item,
      item_name: item.item_name || item.raw_item_name
    }))
    await loadPdf()
    selectedHospital.value = report.value?.hospital_id || null
    await loadNeighbors()
  } catch (error) {
    ElMessage.error('加载报告失败')
  } finally {
    loading.value = false
  }
}

const loadNeighbors = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/v1/report/${reportId.value}/neighbors`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const data = response.data.data
    prevReportId.value = data.prev_report_id
    prevFileName.value = data.prev_file_name || ''
    nextReportId.value = data.next_report_id
    nextFileName.value = data.next_file_name || ''
  } catch (error) {
    console.error('loadNeighbors error:', error)
  }
}

const goPrevReport = () => {
  if (!prevReportId.value) return
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = ''
  }
  isEditing.value = false
  reportId.value = prevReportId.value
  router.replace(`/review/${prevReportId.value}`)
  loadReport()
}

const goNextReport = () => {
  if (!nextReportId.value) return
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = ''
  }
  isEditing.value = false
  reportId.value = nextReportId.value
  router.replace(`/review/${nextReportId.value}`)
  loadReport()
}

const loadPdf = async () => {
  if (!report.value?.report_id) return
  
  pdfLoading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/v1/preview/original/${report.value.report_id}`, {
      responseType: 'blob',
      headers: { Authorization: `Bearer ${token}` }
    })
    
    const blob = new Blob([response.data], { type: 'application/pdf' })
    pdfUrl.value = URL.createObjectURL(blob)
  } catch (error) {
    console.error('Load PDF error:', error)
  } finally {
    pdfLoading.value = false
  }
}

const toggleEdit = () => {
  if (isEditing.value) {
    isEditing.value = false
    loadReport()
  } else {
    isEditing.value = true
  }
}

const deleteRow = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该指标吗？', '提示', { type: 'warning' })
    
    const token = localStorage.getItem('token')
    await axios.delete(`/api/v1/review/${row.result_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('删除成功')
    results.value = results.value.filter(r => r.result_id !== row.result_id)
  } catch (error) {
    ElMessage.info('已取消删除')
  }
}

const addRow = () => {
  tempIdCounter++
  results.value.push({
    _temp_id: tempIdCounter,
    result_id: null,
    raw_item_name: '',
    raw_value: '',
    unit: '',
    reference_text: '',
    flag: ''
  })
}

const saveNewRow = async (row: any) => {
  if (!row.raw_item_name) {
    ElMessage.warning('请输入指标名称')
    return
  }
  
  try {
    const token = localStorage.getItem('token')
    await axios.put(`/api/v1/review/0`, {
      raw_item_name: row.raw_item_name,
      raw_value: row.raw_value,
      unit: row.unit,
      reference_text: row.reference_text,
      flag: row.flag,
      report_id: reportId.value
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('新增成功')
    loadReport()
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message || '未知错误'
    ElMessage.error('新增失败: ' + detail)
  }
}

const removeNewRow = (row: any) => {
  results.value = results.value.filter(r => r._temp_id !== row._temp_id)
}

const saveAll = async () => {
  try {
    const token = localStorage.getItem('token')
    for (const row of results.value) {
      if (row._temp_id) {
        if (row.raw_item_name) {
          await axios.put(`/api/v1/review/0`, {
            raw_item_name: row.raw_item_name,
            raw_value: row.raw_value,
            unit: row.unit,
            reference_text: row.reference_text,
            flag: row.flag,
            report_id: reportId.value
          }, { headers: { Authorization: `Bearer ${token}` } })
        }
      } else {
        await axios.put(`/api/v1/review/${row.result_id}`, {
          raw_item_name: row.raw_item_name,
          raw_value: row.raw_value,
          unit: row.unit,
          reference_text: row.reference_text,
          flag: row.flag
        }, { headers: { Authorization: `Bearer ${token}` } })
      }
    }
    ElMessage.success('全部保存成功')
    isEditing.value = false
    loadReport()
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message || '未知错误'
    ElMessage.error('保存失败: ' + detail)
  }
}

const reparseReport = async () => {
  try {
    await ElMessageBox.confirm('重新识别将删除当前所有化验结果并重新解析，确定继续吗？', '提示', { type: 'warning' })
    
    const token = localStorage.getItem('token')
    const params: any = {}
    if (selectedHospital.value) {
      params.hospital_id = selectedHospital.value
    }
    await axios.post(`/api/v1/report/${reportId.value}/reparse`, null, {
      params,
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('重新识别完成')
    loadReport()
  } catch (error) {
    ElMessage.info('已取消')
  }
}

const markReviewed = async () => {
  await updateReviewStatus(1)
}

const markManual = async () => {
  await updateReviewStatus(2)
}

const markPending = async () => {
  await updateReviewStatus(0)
}

const updateReviewStatus = async (status: number) => {
  try {
    const token = localStorage.getItem('token')
    await axios.put(`/api/v1/review/report/${reportId.value}/status?status=${status}`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('状态更新成功')
    report.value.review_status = status
  } catch (error) {
    ElMessage.error('更新失败')
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

onMounted(() => {
  loadReport()
  loadHospitalList()
})

onUnmounted(() => {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value)
  }
})

watch(route.params, () => {
  if (route.params.id && route.params.id !== reportId.value) {
    reportId.value = route.params.id as string
    if (pdfUrl.value) {
      URL.revokeObjectURL(pdfUrl.value)
    }
    loadReport()
  }
})
</script>

<style scoped>
.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.nav-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-info {
  font-size: 12px;
  color: #909399;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.preview-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 550px;
}

.pdf-wrapper {
  width: 100%;
  height: 550px;
}

.pdf-preview {
  border: none;
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

.action-buttons {
  display: flex;
  gap: 15px;
}
</style>
