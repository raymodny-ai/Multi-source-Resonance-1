import axios, { AxiosError, AxiosResponse } from 'axios'

// ponytail: long-running endpoints (collect-manual, full backfill) need
// a higher timeout than the default 30s. 60s covers the typical GEX
// + multi-symbol collection cycle.
const client = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: attach JWT token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: handle 401 + token refresh + global error broadcast
client.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post('/api/auth/refresh', {
            refresh_token: refreshToken,
          })
          localStorage.setItem('access_token', data.access_token)
          localStorage.setItem('refresh_token', data.refresh_token)
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`
          return client(originalRequest)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }

    // ponytail: broadcast a global API error so the toast layer (ErrorToast.vue)
    // can surface user-visible feedback. Use request URL as a key.
    try {
      const url = (originalRequest?.url as string) || ''
      const status = error.response?.status
      const detail =
        (error.response?.data as any)?.detail ||
        (error.response?.data as any)?.message ||
        error.message ||
        'Request failed'
      window.dispatchEvent(
        new CustomEvent('msr-api-error', {
          detail: { url, status, message: detail },
        }),
      )
    } catch {
      // Best-effort: never let the broadcast break the rejection path.
    }

    return Promise.reject(error)
  },
)

export default client

