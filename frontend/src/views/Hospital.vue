<template>
  <div class="hospital">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>医院模板管理</span>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            新增医院
          </el-button>
        </div>
      </template>

      <el-input
        v-model="keyword"
        placeholder="搜索医院名称"
        style="width: 300px; margin-bottom: 20px;"
        clearable
        @keyup.enter="loadHospitals"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-table :data="hospitals" v-loading="loading">
        <el-table-column prop="hospital_id" label="ID" width="80" />
        <el-table-column prop="hospital_name" label="医院名称" />
        <el-table-column prop="province" label="省份" width="100" />
        <el-table-column prop="city" label="城市" width="100" />
        <el-table-column prop="parser_code" label="解析代码" width="150" />
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button type="primary" link @click="editHospital(row)">编辑</el-button>
            <el-button type="success" link @click="viewTemplate(row)">学习特征</el-button>
            <el-button type="danger" link @click="deleteHospital(row)">删除</el-button>
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
        @size-change="loadHospitals"
        @current-change="loadHospitals"
      />
    </el-card>

    <el-dialog :title="isEdit ? '编辑医院' : '新增医院'" v-model="dialogVisible" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="医院名称" prop="hospital_name">
          <el-input v-model="form.hospital_name" placeholder="请输入医院名称" />
        </el-form-item>
        <el-form-item label="省份" prop="province">
          <el-input v-model="form.province" placeholder="请输入省份" />
        </el-form-item>
        <el-form-item label="城市" prop="city">
          <el-input v-model="form.city" placeholder="请输入城市" />
        </el-form-item>
        <el-form-item label="解析代码" prop="parser_code">
          <el-input v-model="form.parser_code" placeholder="请输入解析代码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog :title="`学习特征 - ${currentHospitalName}`" v-model="templateDialogVisible" width="800px">
      <div v-loading="templateLoading">
        <el-descriptions :column="2" border style="margin-bottom: 20px;">
          <el-descriptions-item label="学习次数">{{ templateData.learn_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="最后更新">{{ templateData.last_updated || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-tabs>
          <el-tab-pane :label="`指标名称映射 (${Object.keys(templateData.item_mappings || {}).length})`">
            <el-table :data="itemMappingList" max-height="300" empty-text="暂无学习数据">
              <el-table-column prop="raw" label="原始指标名称" />
              <el-table-column prop="standard" label="标准化名称" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane :label="`单位映射 (${Object.keys(templateData.unit_mappings || {}).length})`">
            <el-table :data="unitMappingList" max-height="300" empty-text="暂无学习数据">
              <el-table-column prop="raw" label="指标名称" />
              <el-table-column prop="unit" label="单位" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane :label="`参考区间格式 (${Object.keys(templateData.reference_formats || {}).length})`">
            <el-table :data="refFormatList" max-height="300" empty-text="暂无学习数据">
              <el-table-column prop="raw" label="指标名称" />
              <el-table-column prop="format" label="参考区间格式" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
      <template #footer>
        <el-button type="danger" @click="clearTemplate">清除学习特征</el-button>
        <el-button @click="templateDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import request from '@/utils/request'
import { ElMessage, ElMessageBox } from 'element-plus'

const hospitals = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()

const form = reactive({
  hospital_id: null,
  hospital_name: '',
  province: '',
  city: '',
  parser_code: 'common'
})

const rules = {
  hospital_name: [
    { required: true, message: '请输入医院名称', trigger: 'blur' }
  ],
  parser_code: [
    { required: true, message: '请输入解析代码', trigger: 'blur' }
  ]
}

// 学习特征相关
const templateDialogVisible = ref(false)
const templateLoading = ref(false)
const currentHospitalId = ref<number | null>(null)
const currentHospitalName = ref('')
const templateData = ref<any>({})

const itemMappingList = computed(() => {
  const mappings = templateData.value.item_mappings || {}
  return Object.entries(mappings).map(([raw, standard]) => ({ raw, standard }))
})

const unitMappingList = computed(() => {
  const mappings = templateData.value.unit_mappings || {}
  return Object.entries(mappings).map(([raw, unit]) => ({ raw, unit }))
})

const refFormatList = computed(() => {
  const mappings = templateData.value.reference_formats || {}
  return Object.entries(mappings).map(([raw, format]) => ({ raw, format }))
})

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadHospitals = async () => {
  loading.value = true
  try {
    const response = await request.get('/hospital/list', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        keyword: keyword.value
      }
    })
    hospitals.value = response.data.list
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  form.hospital_id = null
  form.hospital_name = ''
  form.province = ''
  form.city = ''
  form.parser_code = 'common'
  dialogVisible.value = true
}

const editHospital = (row: any) => {
  isEdit.value = true
  form.hospital_id = row.hospital_id
  form.hospital_name = row.hospital_name
  form.province = row.province || ''
  form.city = row.city || ''
  form.parser_code = row.parser_code
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    
    try {
      if (isEdit.value) {
        await request.put(`/hospital/${form.hospital_id}`, form)
        ElMessage.success('编辑成功')
      } else {
        await request.post('/hospital/', form)
        ElMessage.success('新增成功')
      }
      dialogVisible.value = false
      loadHospitals()
    } catch (error: any) {
      ElMessage.error('操作失败')
    }
  })
}

const deleteHospital = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该医院吗？', '提示', {
      type: 'warning'
    })
    
    await request.delete(`/hospital/${row.hospital_id}`)
    
    ElMessage.success('删除成功')
    loadHospitals()
  } catch (error) {
    ElMessage.info('已取消删除')
  }
}

const viewTemplate = async (row: any) => {
  currentHospitalId.value = row.hospital_id
  currentHospitalName.value = row.hospital_name
  templateDialogVisible.value = true
  templateLoading.value = true
  try {
    const response = await request.get(`/hospital/${row.hospital_id}/template`)
    templateData.value = response.data
  } catch (error) {
    ElMessage.error('加载学习特征失败')
  } finally {
    templateLoading.value = false
  }
}

const clearTemplate = async () => {
  try {
    await ElMessageBox.confirm('确定要清除该医院的所有学习特征吗？', '提示', {
      type: 'warning'
    })
    
    await request.delete(`/hospital/${currentHospitalId.value}/template`)
    
    ElMessage.success('学习特征已清除')
    templateData.value = { item_mappings: {}, unit_mappings: {}, reference_formats: {}, learn_count: 0 }
  } catch (error) {
    ElMessage.info('已取消')
  }
}

onMounted(() => {
  loadHospitals()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
