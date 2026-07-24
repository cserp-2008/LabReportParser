<template>
  <div class="user">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            新增用户
          </el-button>
        </div>
      </template>

      <el-input
        v-model="keyword"
        placeholder="搜索用户名或姓名"
        style="width: 300px; margin-bottom: 20px;"
        clearable
        @keyup.enter="loadUsers"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-table :data="users" v-loading="loading">
        <el-table-column prop="user_id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="real_name" label="真实姓名" />
        <el-table-column prop="is_enable" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_enable === 1 ? 'success' : 'danger'">
              {{ row.is_enable === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="roles" label="角色" width="150">
          <template #default="{ row }">
            <el-tag v-for="role in row.roles" :key="role" size="small" style="margin-right: 5px;">
              {{ role }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button type="primary" link @click="editUser(row)">编辑</el-button>
            <el-button type="success" link @click="editRoles(row)">角色</el-button>
            <el-button type="warning" link @click="resetPassword(row)">重置密码</el-button>
            <el-button type="danger" link @click="toggleEnable(row)">
              {{ row.is_enable === 1 ? '禁用' : '启用' }}
            </el-button>
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
        @size-change="loadUsers"
        @current-change="loadUsers"
      />
    </el-card>

    <el-dialog :title="isEdit ? '编辑用户' : '新增用户'" v-model="dialogVisible" width="450px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="form.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="密码" v-if="!isEdit" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog title="角色分配" v-model="roleDialogVisible" width="400px">
      <el-form :model="roleForm" label-width="80px">
        <el-form-item label="选择角色">
          <el-select v-model="roleForm.roles" multiple placeholder="请选择角色">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRoles">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog title="重置密码" v-model="pwdDialogVisible" width="400px">
      <el-form :model="pwdForm" :rules="pwdRules" ref="pwdFormRef" label-width="100px">
        <el-form-item label="新密码" prop="password">
          <el-input v-model="pwdForm.password" type="password" placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" placeholder="请再次输入密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="doResetPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const users = ref<any[]>([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const roleDialogVisible = ref(false)
const pwdDialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const pwdFormRef = ref()

const currentUserId = ref(0)

const form = reactive({
  user_id: null,
  username: '',
  real_name: '',
  password: ''
})

const roleForm = reactive({
  roles: [] as string[]
})

const pwdForm = reactive({
  password: '',
  confirm_password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  real_name: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不少于6位', trigger: 'blur' }
  ]
}

const pwdRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不少于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string, callback: any) => {
        if (value !== pwdForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadUsers = async () => {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await axios.get('/api/v1/user/list', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        keyword: keyword.value
      },
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    users.value = response.data.data.list
    total.value = response.data.data.total
  } catch (error) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  form.user_id = null
  form.username = ''
  form.real_name = ''
  form.password = ''
  dialogVisible.value = true
}

const editUser = (row: any) => {
  isEdit.value = true
  form.user_id = row.user_id
  form.username = row.username
  form.real_name = row.real_name || ''
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    
    try {
      const token = localStorage.getItem('token')
      if (isEdit.value) {
        await axios.put(`/api/v1/user/${form.user_id}`, form, {
          headers: { Authorization: `Bearer ${token}` }
        })
        ElMessage.success('编辑成功')
      } else {
        await axios.post('/api/v1/user/', form, {
          headers: { Authorization: `Bearer ${token}` }
        })
        ElMessage.success('新增成功')
      }
      dialogVisible.value = false
      loadUsers()
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  })
}

const editRoles = async (row: any) => {
  currentUserId.value = row.user_id
  roleForm.roles = row.roles || []
  roleDialogVisible.value = true
}

const saveRoles = async () => {
  try {
    const token = localStorage.getItem('token')
    await axios.post(`/api/v1/user/${currentUserId.value}/roles`, {
      roles: roleForm.roles
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success('保存成功')
    roleDialogVisible.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const resetPassword = (row: any) => {
  currentUserId.value = row.user_id
  pwdForm.password = ''
  pwdForm.confirm_password = ''
  pwdDialogVisible.value = true
}

const doResetPassword = async () => {
  if (!pwdFormRef.value) return
  await pwdFormRef.value.validate(async (valid: boolean) => {
    if (!valid) return
    
    try {
      const token = localStorage.getItem('token')
      await axios.post(`/api/v1/user/${currentUserId.value}/reset-password`, {
        password: pwdForm.password
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      
      ElMessage.success('密码重置成功')
      pwdDialogVisible.value = false
    } catch (error) {
      ElMessage.error('重置失败')
    }
  })
}

const toggleEnable = async (row: any) => {
  try {
    const token = localStorage.getItem('token')
    await axios.post(`/api/v1/user/${row.user_id}/toggle`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    
    ElMessage.success(row.is_enable === 1 ? '已禁用' : '已启用')
    loadUsers()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
