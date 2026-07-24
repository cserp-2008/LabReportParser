import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const service = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  paramsSerializer: {
    serialize: (params) => {
      const parts = []
      const encode = (val) => {
        return encodeURIComponent(val).replace(/%5B/g, '[').replace(/%5D/g, ']')
      }
      Object.keys(params).forEach(key => {
        const val = params[key]
        if (val === null || val === undefined) return
        if (Array.isArray(val)) {
          val.forEach(v => {
            parts.push(`${encode(key)}=${encode(v)}`)
          })
        } else {
          parts.push(`${encode(key)}=${encode(val)}`)
        }
      })
      return parts.join('&')
    }
  }
})

service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

service.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 0) {
      ElMessage.error(res.msg || '请求失败')
      if (res.code === 10001) {
        localStorage.removeItem('token')
        router.push('/login')
      }
      return Promise.reject(new Error(res.msg || '请求失败'))
    }
    return res
  },
  (error) => {
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default service
