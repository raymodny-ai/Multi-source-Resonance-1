import axios from 'axios'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export function login(username: string, password: string) {
  return axios.post<TokenResponse>('/api/auth/login', { username, password })
}

export function refresh(refreshToken: string) {
  return axios.post<TokenResponse>('/api/auth/refresh', { refresh_token: refreshToken })
}

export function logout(token?: string) {
  const accessToken = localStorage.getItem('access_token')
  return axios.post('/api/auth/logout', { token }, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem('access_token')
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

export function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}
