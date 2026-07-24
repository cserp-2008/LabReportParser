<template>
  <div class="reports">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>报告列表</span>
          <div class="header-right">
            <el-button type="primary" @click="showBatchActions">
              <el-icon><Check /></el-icon>
              批量操作
            </el-button>
            <el-button @click="exportReports">
              <el-icon><Download /></el-icon>
              导出
            </el-button>
            <el-button @click="$router.push('/upload')">
              <el-icon><Plus /></el-icon>
              上传
            </el-button>
          </div>
        </div>
      </template>

      <div class="filter-bar">
        <el-input
          v-model="keyword"
          placeholder="搜索文件名或患者"
          style="width: 200px; margin-right: 10px;"
          clearable
          @keyup.enter="loadReports"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-select v-model="filterReviewStatus" placeholder="复核状态" style="width: 120px; margin-right: 10px;" clearable>
          <el-option :value="0" label="未复核" />
          <el-option :value="1" label="已复核" />
          <el-option :value="2" label="人工修改" />
        </el-select>
        
        <el-select v-model="filterFileType" placeholder="文件类型" style="width: 120px; margin-right: 10px;" clearable>
          <el-option value="pdf" label="PDF" />
        </el-select>
        
        <el-date-picker
          v-model="filterDateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 300px; margin-right: 10px;"
        />
        
        <el-button type="primary" @click="loadReports">筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <el-table :data="reports" v-loading="loading" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="file_name" label="文件名" />
        <el-table-column prop="hospital_name" label="医院" width="120" />
        <el-table-column prop="patient_name" label="患者姓名" width="100" />
        <el-table-column prop="sample_time" label="采样时间" width="150">
          <template #default="{ row }">
            {{ row.sample_time ? formatDate(row.sample_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="quality_score" label="质量分" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.quality_score" :type="row.quality_score >= 85 ? 'success' : 'warning'">
              {{ row.quality_score }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="review_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getReviewStatusType(row.review_status)">
              {{ getReviewStatusText(row.review_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/report/${row.report_id}`)">查看</el-button>
            <el-button type="success" link @click="updateReviewStatus(row.report_id, 1)" v-if="row.review_status !== 1">标记已复核</el-button>
            <el-button type="danger" link @click="deleteReport(row.report_id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end;"
        @size-change="loadReports"
        @current-change="loadReports"
      />
    </el-card>

    <el-dialog title="批量操作" v-model="batchDialogVisible" width="400px">
      <el-form :model="batchForm" label-width="100px">
        <el-form-item label="选择操作">
          <el-select v-model="batchForm.action" placeholder="请选择操作">
            <el-option :value="1" label="批量标记已复核" />
            <el-option :value="0" label="批量标记未复核" />
            <el-option :value="2" label="批量标记人工修改" />
            <el-option :value="9" label="批量删除" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="doBatchAction">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { reportApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'

const reports = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const filterReviewStatus = ref<number | undefined>()
const filterFileType = ref<string>('')
const filterDateRange = ref<Date[]>([])

const selectedIds = ref<string[]>([])
const batchDialogVisible = ref(false)
const batchForm = reactive({
  action: 1
})

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

const handleSelectionChange = (val: any[]) => {
  selectedIds.value = val.map(item => item.report_id)
}

const resetFilters = () => {
  keyword.value = ''
  filterReviewStatus.value = undefined
  filterFileType.value = ''
  filterDateRange.value = []
  page.value = 1
  loadReports()
}

const loadReports = async () => {
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value
    }
    
    if (filterReviewStatus.value !== undefined) {
      params.review_status = filterReviewStatus.value
    }
    if (filterFileType.value) {
      params.file_type = filterFileType.value
    }
    if (filterDateRange.value.length === 2) {
      params.start_date = filterDateRange.value[0].toISOString().split('T')[0]
      params.end_date = filterDateRange.value[1].toISOString().split('T')[0]
    }
    
    const res = await reportApi.getList(params)
    reports.value = res.data.list
    total.value = res.data.total
  } catch (error) {
    ElMessage.error('加载失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const showBatchActions = () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择报告')
    return
  }
  batchDialogVisible.value = true
}

const doBatchAction = async () => {
  const token = localStorage.getItem('token')
  const headers = { Authorization: `Bearer ${token}` }

  try {
    if (batchForm.action === 9) {
      try {
        await ElMessageBox.confirm(
          `确定要删除选中的 ${selectedIds.value.length} 个报告吗？此操作不可恢复！`,
          '批量删除确认',
          { type: 'warning' }
        )
      } catch {
        return
      }

      await axios.post('/api/v1/report/batch/delete', {
        report_ids: selectedIds.value
      }, { headers })
      ElMessage.success('批量删除成功')
    } else {
      await axios.post('/api/v1/report/batch/review', {
        report_ids: selectedIds.value,
        review_status: batchForm.action
      }, { headers })
      ElMessage.success('批量操作成功')
    }

    batchDialogVisible.value = false
    selectedIds.value = []
    loadReports()
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '批量操作失败'
    ElMessage.error(msg)
  }
}

const updateReviewStatus = async (reportId: string, status: number) => {
  try {
    const token = localStorage.getItem('token')
    await axios.post('/api/v1/report/batch/review', {
      report_ids: [reportId],
      review_status: status
    }, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    ElMessage.success('状态更新成功')
    loadReports()
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const deleteReport = async (reportId: string) => {
  try {
    await ElMessageBox.confirm('确定要删除该报告吗？', '提示', {
      type: 'warning'
    })
  } catch (e) {
    ElMessage.info('已取消删除')
    return
  }

  try {
    const token = localStorage.getItem('token')
    await axios.delete(`/api/v1/report/${reportId}`, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    ElMessage.success('删除成功')
    loadReports()
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '删除失败'
    ElMessage.error(msg)
  }
}

const exportReports = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/v1/report/export', {
      responseType: 'blob',
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    
    const blob = new Blob([response.data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `reports_${new Date().getTime()}.json`
    a.click()
    URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
</style>
