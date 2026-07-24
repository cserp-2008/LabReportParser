import request from '../utils/request'

export const authApi = {
  login: (data) => {
    return request.post('/auth/login', data)
  },
  getCurrentUser: () => {
    return request.get('/auth/me')
  }
}

export const reportApi = {
  getList: (params) => {
    return request.get('/report/list', { params })
  },
  getDetail: (reportId) => {
    return request.get(`/report/${reportId}`)
  }
}

export const uploadApi = {
  uploadFile: (file, onProgress, overwrite = false) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/upload/file', formData, {
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
  uploadFiles: (files, overwrite = false) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return request.post('/upload/files', formData, {
      timeout: 0,
      params: { overwrite }
    })
  }
}

export const trendApi = {
  getItems: (keyword) => {
    return request.get('/trend/items', { params: keyword ? { keyword } : {} })
  },
  getAnalysis: (itemIds, params) => {
    return request.get('/trend/analysis', { params: { ...params, item_ids: itemIds } })
  }
}

export const aiApi = {
  getConfig: () => {
    return request.get('/ai/config')
  },
  saveConfig: (apiKey, baseUrl, modelName, prompt) => {
    const formData = new FormData()
    formData.append('api_key', apiKey)
    formData.append('base_url', baseUrl)
    formData.append('model_name', modelName)
    if (prompt) {
      formData.append('prompt', prompt)
    }
    return request.post('/ai/config', formData)
  },
  testConfig: () => {
    return request.get('/ai/config/test')
  },
  getDefaultPrompt: () => {
    return request.get('/ai/default-prompt')
  },
  recognizeFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/ai/recognize/file', formData, {
      timeout: 0
    })
  },
  recognizeFiles: (files) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return request.post('/ai/recognize/files', formData, {
      timeout: 0
    })
  }
}
