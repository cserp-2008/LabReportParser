<template>
  <div class="review-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>待审核报告</span>
          <div class="header-right">
            <el-button @click="loadReports(true)">
              <el-icon><Refresh /></el-icon>
              刷新
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
        
        <el-button type="primary" @click="loadReports">筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>

        <div class="status-info">
          <span>当前：第 {{ page }} / {{ totalPages }} 页</span>
          <span v-if="activeFilters.length > 0">| 筛选条件：{{ activeFilters.join('，') }}</span>
          <span>| 共 {{ total }} 条记录</span>
        </div>
      </div>

      <el-table :data="reports" v-loading="loading" :row-class-name="tableRowClassName">
        <el-table-column prop="report_id" label="报告ID" width="120" />
        <el-table-column prop="file_name" label="文件名" />
        <el-table-column prop="patient_name" label="患者姓名" width="100" />
        <el-table-column prop="hospital_name" label="医院" width="120" />
        <el-table-column prop="sample_time" label="采样时间" width="150">
          <template #default="{ row }">
            {{ row.sample_time ? formatDate(row.sample_time) : '-' }}
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
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button type="primary" link @click="$router.push(`/review/${row.report_id}`)">审核</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 20px; justify-content: flex-end;"
        @size-change="loadReports"
        @current-change="loadReports"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onActivated, computed, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

defineOptions({ name: 'ReviewList' })

const reports = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterReviewStatus = ref<number | undefined>()

const STORAGE_KEY = 'review_list_state'

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

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(total.value / pageSize.value))
})

const activeFilters = computed(() => {
  const filters: string[] = []
  if (keyword.value) {
    filters.push(`关键词: ${keyword.value}`)
  }
  if (filterReviewStatus.value !== undefined) {
    filters.push(`状态: ${getReviewStatusText(filterReviewStatus.value)}`)
  }
  return filters
})

const tableRowClassName = ({ rowIndex }: { rowIndex: number }) => {
  return rowIndex % 2 === 0 ? 'row-even' : 'row-odd'
}

const saveState = () => {
  const state = {
    keyword: keyword.value,
    page: page.value,
    pageSize: pageSize.value,
    filterReviewStatus: filterReviewStatus.value
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

const loadState = () => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const state = JSON.parse(saved)
      keyword.value = state.keyword || ''
      page.value = state.page || 1
      pageSize.value = state.pageSize || 20
      filterReviewStatus.value = state.filterReviewStatus
    } catch (e) {
      console.error('Failed to load state:', e)
    }
  }
}

const loadReports = async (force = false) => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const params: any = {
      page: page.value,
      page_size: pageSize.value
    }
    if (keyword.value) params.keyword = keyword.value
    if (filterReviewStatus.value !== undefined) params.review_status = filterReviewStatus.value
    
    const response = await axios.get('/api/v1/report/list', {
      params,
      headers: { Authorization: `Bearer ${token}` }
    })
    reports.value = response.data.data.list
    total.value = response.data.data.total
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  keyword.value = ''
  filterReviewStatus.value = undefined
  page.value = 1
  saveState()
  loadReports()
}

watch([keyword, page, pageSize, filterReviewStatus], () => {
  saveState()
})

onMounted(() => {
  loadState()
  loadReports()
})

onActivated(() => {
  loadReports()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.status-info {
  margin-left: auto;
  font-size: 14px;
  color: #606266;
}

.status-info span {
  margin-left: 10px;
}

:deep(.el-table th.el-table__cell) {
  background-color: #1a73e8;
  color: #ffffff;
  font-weight: bold;
}

:deep(.el-table .row-even) {
  background-color: #ffffff;
}

:deep(.el-table .row-odd) {
  background-color: #f8f9fa;
}

:deep(.el-table tr:hover > td.el-table__cell) {
  background-color: #e3f2fd !important;
}
</style>
