<template>
  <el-container class="layout-container">
    <el-aside 
      :style="{ width: isCollapse ? '64px' : sidebarWidth + 'px' }" 
      class="aside"
      :class="{ collapsed: isCollapse }"
    >
      <div class="logo">
        <el-icon v-if="isCollapse" size="24"><Document /></el-icon>
        <h2 v-else>LabReportParser</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409EFF"
        :collapse="isCollapse"
        :collapse-transition="false"
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/upload">
          <el-icon><Upload /></el-icon>
          <span>上传中心</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <span>报告管理</span>
        </el-menu-item>
        <el-menu-item index="/review">
          <el-icon><CircleCheck /></el-icon>
          <span>报告审核</span>
        </el-menu-item>
        <el-menu-item index="/trend">
          <el-icon><TrendCharts /></el-icon>
          <span>趋势分析</span>
        </el-menu-item>
        <el-sub-menu index="/manage">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/hospital">医院管理</el-menu-item>
          <el-menu-item index="/labitem">指标管理</el-menu-item>
          <el-menu-item index="/user">用户管理</el-menu-item>
          <el-menu-item index="/ai">AI识别</el-menu-item>
          <el-menu-item index="/system">系统配置</el-menu-item>
        </el-sub-menu>
      </el-menu>
      <div class="collapse-btn" @click="toggleCollapse">
        <el-icon v-if="isCollapse"><Expand /></el-icon>
        <el-icon v-else><Fold /></el-icon>
      </div>
    </el-aside>
    <div 
      class="sidebar-resizer" 
      @mousedown="startResize"
      :class="{ collapsed: isCollapse }"
    ></div>
    <el-container :style="{ marginLeft: isCollapse ? '64px' : sidebarWidth + 'px' }">
      <el-header class="header">
        <div class="header-left">
          <span class="title">医学检验报告解析系统</span>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              {{ userStore.userInfo?.real_name || userStore.userInfo?.username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <keep-alive :include="cachedViews">
          <router-view v-slot="{ Component }">
            <component :is="Component" />
          </router-view>
        </keep-alive>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'
import { authApi } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  HomeFilled, 
  Upload, 
  Document, 
  CircleCheck, 
  TrendCharts, 
  Setting, 
  User,
  Fold,
  Expand
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const sidebarWidth = ref(240)
const isResizing = ref(false)
const cachedViews = ref<string[]>(['ReviewList'])

const activeMenu = computed(() => route.path)

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const startResize = (e: MouseEvent) => {
  if (isCollapse.value) return
  isResizing.value = true
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

const onResize = (e: MouseEvent) => {
  if (!isResizing.value) return
  const newWidth = e.clientX
  if (newWidth >= 180 && newWidth <= 500) {
    sidebarWidth.value = newWidth
  }
}

const stopResize = () => {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

const handleCommand = async (command: string) => {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      userStore.logout()
      router.push('/login')
      ElMessage.success('已退出登录')
    } catch {
    }
  }
}

onMounted(async () => {
  if (userStore.token && !userStore.userInfo) {
    try {
      const res = await authApi.getCurrentUser()
      userStore.setUserInfo(res.data)
    } catch (error) {
      console.error(error)
    }
  }
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
})
</script>

<style scoped>
.layout-container {
  height: 100%;
}

.aside {
  background-color: #001529;
  height: 100%;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
  transition: width 0.2s ease;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #1f2937;
}

.logo h2 {
  color: white;
  font-size: 18px;
  margin: 0;
}

.collapse-btn {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #1f2937;
  border-radius: 4px;
  cursor: pointer;
  color: #fff;
  transition: all 0.2s;
}

.collapse-btn:hover {
  background-color: #374151;
}

.sidebar-resizer {
  position: fixed;
  left: 240px;
  top: 0;
  width: 4px;
  height: 100%;
  background-color: #e5e7eb;
  cursor: col-resize;
  z-index: 101;
  transition: left 0.2s ease;
}

.sidebar-resizer:hover {
  background-color: #9ca3af;
}

.sidebar-resizer.collapsed {
  left: 64px;
}

.header {
  background-color: white;
  border-bottom: 1px solid #ddd;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left .title {
  font-size: 18px;
  font-weight: 500;
  color: #333;
}

.header-right .user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  color: #333;
}

.main {
  background-color: #f5f7fa;
  padding: 20px;
}
</style>
