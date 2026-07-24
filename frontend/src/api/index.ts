import request from '@/utils/request'

export interface LoginParams {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface UserInfo {
  user_id: number
  username: string
  real_name?: string
}

export interface ReportListItem {
  report_id: string
  file_name: string
  file_type: string
  patient_name?: string
  sample_time?: string
  quality_score?: number
  review_status: number
  create_time: string
}

export interface ReportListResponse {
  total: number
  page: number
  page_size: number
  list: ReportListItem[]
}

export interface LabResultItem {
  result_id: number
  raw_item_name: string
  item_name?: string
  abbr?: string
  raw_value?: string
  value_numeric?: number
  unit?: string
  reference_low?: number
  reference_high?: number
  reference_text?: string
  flag?: string
  review_status: number
  page_no: number
  bbox_left?: number
  bbox_top?: number
  bbox_right?: number
  bbox_bottom?: number
}

export interface ReportPageData {
  page_no: number
  preview_url: string
  width?: number
  height?: number
}

export interface ReportDetail {
  report_id: string
  patient_name?: string
  gender?: string
  age?: string
  sample_time?: string
  report_time?: string
  hospital_name?: string
  file_name: string
  quality_score?: number
  review_status: number
  page_count: number
  results: LabResultItem[]
  pages: ReportPageData[]
}

export interface TrendItem {
  item_id: number
  item_name: string
  abbr?: string
  category?: string
  standard_unit?: string
}

export interface TrendDataPoint {
  time: string
  value?: number
  hospital?: string
  flag?: string
  trend?: string
  report_id?: string
}

export interface TrendAnalysisResponse {
  item_id: number
  item_name: string
  abbr: string
  unit?: string
  data: TrendDataPoint[]
}

export const authApi = {
  login: (data: LoginParams) => {
    return request.post<LoginResponse>('/auth/login', data)
  },
  getCurrentUser: () => {
    return request.get<UserInfo>('/auth/me')
  }
}

export const reportApi = {
  getList: (params: { page?: number; page_size?: number; keyword?: string }) => {
    return request.get<ReportListResponse>('/report/list', { params })
  },
  getDetail: (reportId: string) => {
    return request.get<ReportDetail>(`/report/${reportId}`)
  }
}

export const uploadApi = {
  uploadFile: (file: File, onProgress?: (progress: number) => void, overwrite: boolean = false) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/upload/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
      params: { overwrite },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      }
    })
  },
  uploadFiles: (files: File[], overwrite: boolean = false) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return request.post('/upload/files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
      params: { overwrite }
    })
  }
}

export const trendApi = {
  getItems: (keyword?: string) => {
    return request.get<TrendItem[]>('/trend/items', { params: keyword ? { keyword } : {} })
  },
  getAnalysis: (itemIds: number[], params?: { start_date?: string; end_date?: string }) => {
    return request.get<TrendAnalysisResponse[]>('/trend/analysis', { params: { ...params, item_ids: itemIds } })
  }
}

export const aiApi = {
  getConfig: () => {
    return request.get('/ai/config')
  },
  saveConfig: (apiKey: string, baseUrl: string, modelName: string, prompt?: string) => {
    const formData = new FormData()
    formData.append('api_key', apiKey)
    formData.append('base_url', baseUrl)
    formData.append('model_name', modelName)
    if (prompt) {
      formData.append('prompt', prompt)
    }
    return request.post('/ai/config', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  testConfig: () => {
    return request.get('/ai/config/test')
  },
  getDefaultPrompt: () => {
    return request.get('/ai/default-prompt')
  },
  recognizeFile: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/ai/recognize/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0
    })
  },
  recognizeFiles: (files: File[]) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return request.post('/ai/recognize/files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0
    })
  }
}
