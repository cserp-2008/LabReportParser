<template>
  <div class="labitem">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>标准指标库管理</span>
          <div>
            <el-button type="success" :loading="syncing" @click="syncFromReports">
              <el-icon><Refresh /></el-icon>
              从报告同步
            </el-button>
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon>
              新增指标
            </el-button>
            <el-button type="info" @click="exportItems">
              <el-icon><Download /></el-icon>
              导出指标库
            </el-button>
          </div>
        </div>
      </template>

      <el-input
        v-model="keyword"
        placeholder="搜索指标名称或缩写"
        style="width: 300px; margin-bottom: 20px;"
        clearable
        @keyup.enter="loadItems"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-table :data="items" v-loading="loading">
        <el-table-column prop="item_id" label="ID" width="80" />
        <el-table-column prop="item_name" label="项目名称" />
        <el-table-column prop="abbr" label="缩写" width="100" />
        <el-table-column prop="english_name" label="英文名称" width="200" />
        <el-table-column prop="category" label="分类" width="120" />
        <el-table-column prop="standard_unit" label="标准单位" width="120" />
        <el-table-column prop="reference_range" label="参考范围" width="200" show-overflow-tooltip />
        <el-table-column prop="alias_count" label="别名数" width="80" />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button type="primary" link @click="editItem(row)">编辑</el-button>
            <el-button type="success" link @click="editAliases(row)">别名</el-button>
            <el-button type="danger" link @click="deleteItem(row)">删除</el-button>
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
        @size-change="loadItems"
        @current-change="loadItems"
      />
    </el-card>

    <el-dialog :title="isEdit ? '编辑指标' : '新增指标'" v-model="dialogVisible" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="项目名称" prop="item_name">
          <el-input v-model="form.item_name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="缩写" prop="abbr">
          <el-input v-model="form.abbr" placeholder="请输入缩写" />
        </el-form-item>
        <el-form-item label="英文名称" prop="english_name">
          <el-input v-model="form.english_name" placeholder="请输入英文名称" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择分类">
            <el-option label="血常规" value="血常规" />
            <el-option label="肝功能" value="肝功能" />
            <el-option label="肾功能" value="肾功能" />
            <el-option label="血糖" value="血糖" />
            <el-option label="血脂" value="血脂" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="标准单位" prop="standard_unit">
          <el-input v-model="form.standard_unit" placeholder="请输入标准单位" />
        </el-form-item>
        <el-form-item label="参考范围" prop="reference_range">
          <el-input v-model="form.reference_range" placeholder="如 3.5-9.5 或 男:57-97;女:41-73" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" rows="3" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog title="别名管理" v-model="aliasDialogVisible" width="450px">
      <div class="alias-list">
        <div v-for="(alias, index) in aliases" :key="index" class="alias-item">
          <el-input v-model="alias.alias_name" placeholder="别名名称" />
          <el-button type="danger" link @click="removeAlias(index)">删除</el-button>
        </div>
        <el-button type="success" link @click="addAlias">+ 添加别名</el-button>
      </div>
      <template #footer>
        <el-button @click="aliasDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAliases">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Download } from '@element-plus/icons-vue'

const items = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const syncing = ref(false)

const dialogVisible = ref(false)
const aliasDialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()

const currentItemId = ref(0)
const aliases = ref<any[]>([])

const form = reactive({
  item_id: null,
  item_name: '',
  abbr: '',
  english_name: '',
  category: '',
  standard_unit: '',
  reference_range: '',
  description: ''
})

const rules = {
  item_name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' }
  ],
  standard_unit: [
    { required: true, message: '请输入标准单位', trigger: 'blur' }
  ]
}

const loadItems = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/v1/labitem/list', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        keyword: keyword.value
      },
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    items.value = response.data.data.list
    total.value = response.data.data.total
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  form.item_id = null
  form.item_name = ''
  form.abbr = ''
  form.english_name = ''
  form.category = ''
  form.standard_unit = ''
  form.reference_range = ''
  form.description = ''
  dialogVisible.value = true
}

const editItem = (row: any) => {
  isEdit.value = true
  form.item_id = row.item_id
  form.item_name = row.item_name
  form.abbr = row.abbr || ''
  form.english_name = row.english_name || ''
  form.category = row.category || ''
  form.standard_unit = row.standard_unit
  form.reference_range = row.reference_range || ''
  form.description = row.description || ''
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    
    try {
      const token = localStorage.getItem('token')
      if (isEdit.value) {
        await axios.put(`/api/v1/labitem/${form.item_id}`, form, {
          headers: { Authorization: `Bearer ${token}` }
        })
        ElMessage.success('编辑成功')
      } else {
        await axios.post('/api/v1/labitem/', form, {
          headers: { Authorization: `Bearer ${token}` }
        })
        ElMessage.success('新增成功')
      }
      dialogVisible.value = false
      loadItems()
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  })
}

const deleteItem = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该指标吗？', '提示', {
      type: 'warning'
    })
    
    const token = localStorage.getItem('token')
    await axios.delete(`/api/v1/labitem/${row.item_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('删除成功')
    loadItems()
  } catch (error) {
    ElMessage.info('已取消删除')
  }
}

const editAliases = async (row: any) => {
  currentItemId.value = row.item_id
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get(`/api/v1/labitem/${row.item_id}/aliases`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    aliases.value = response.data.data.map((a: any) => ({ alias_name: a.alias_name }))
  } catch (error) {
    aliases.value = []
  }
  aliasDialogVisible.value = true
}

const addAlias = () => {
  aliases.value.push({ alias_name: '' })
}

const removeAlias = (index: number) => {
  aliases.value.splice(index, 1)
}

const saveAliases = async () => {
  try {
    const token = localStorage.getItem('token')
    await axios.post(`/api/v1/labitem/${currentItemId.value}/aliases`, {
      aliases: aliases.value.map((a: any) => a.alias_name)
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('保存成功')
    aliasDialogVisible.value = false
    loadItems()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const syncFromReports = async () => {
  try {
    await ElMessageBox.confirm(
      '将扫描所有已解析的报告，自动新增缺失的指标并补全参考范围。是否继续？',
      '从报告同步指标库',
      { type: 'info' }
    )
  } catch {
    return
  }

  syncing.value = true
  try {
    const token = localStorage.getItem('token')
    const resp = await axios.post('/api/v1/labitem/sync', {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const d = resp.data.data
    ElMessage.success(
      `同步完成：新增指标 ${d.new_items} 个，新增别名 ${d.new_aliases} 个，` +
      `补全参考范围 ${d.updated_ref} 个，补全单位 ${d.updated_unit} 个`
    )
    loadItems()
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '同步失败'
    ElMessage.error(msg)
  } finally {
    syncing.value = false
  }
}

const exportItems = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/v1/labitem/export', {
      headers: {
        Authorization: `Bearer ${token}`
      },
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '标准指标库.csv')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  loadItems()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alias-list {
  padding: 10px;
}

.alias-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.alias-item .el-input {
  flex: 1;
}
</style>
