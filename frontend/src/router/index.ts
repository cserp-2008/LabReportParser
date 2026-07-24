import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/store/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/views/Layout.vue'),
    meta: { requiresAuth: true },
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '首页' }
      },
      {
        path: 'report/:id',
        name: 'ReportDetail',
        component: () => import('@/views/ReportDetail.vue'),
        meta: { title: '报告详情' }
      },
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('@/views/Upload.vue'),
        meta: { title: '上传中心' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/Reports.vue'),
        meta: { title: '报告管理' }
      },
      {
        path: 'review',
        name: 'ReviewList',
        component: () => import('@/views/ReviewList.vue'),
        meta: { title: '报告审核' }
      },
      {
        path: 'review/:id',
        name: 'Review',
        component: () => import('@/views/Review.vue'),
        meta: { title: '报告审核' }
      },
      {
        path: 'trend',
        name: 'Trend',
        component: () => import('@/views/Trend.vue'),
        meta: { title: '趋势分析' }
      },
      {
        path: 'hospital',
        name: 'Hospital',
        component: () => import('@/views/Hospital.vue'),
        meta: { title: '医院管理' }
      },
      {
        path: 'labitem',
        name: 'LabItem',
        component: () => import('@/views/LabItem.vue'),
        meta: { title: '指标管理' }
      },
      {
        path: 'user',
        name: 'User',
        component: () => import('@/views/User.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/System.vue'),
        meta: { title: '系统配置' }
      },
      {
        path: 'ai',
        name: 'AI',
        component: () => import('@/views/AI.vue'),
        meta: { title: 'AI识别' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

console.log('Registered routes:', router.getRoutes().map(r => ({ name: r.name, path: r.path })))

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.token) {
    next('/login')
  } else if (to.path === '/login' && userStore.token) {
    next('/')
  } else {
    next()
  }
})

export default router
