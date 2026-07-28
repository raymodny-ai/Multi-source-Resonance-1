import client from './client'

export interface ConfigItem {
  key: string
  value: string
  description: string | null
  updated_at: string | null
}

export function getConfig() {
  return client.get<{ configs: ConfigItem[]; count: number }>('/config')
}

export function updateConfig(key: string, value: string, description?: string) {
  return client.put('/config', { key, value, description })
}

export function getConfigDefaults() {
  return client.get<Record<string, any>>('/config/defaults')
}

export function getConfigSources() {
  return client.get('/config/sources')
}

export function updateSourceConfig(name: string, enabled: boolean) {
  return client.put(`/config/sources/${name}`, { enabled })
}

export function getConfigAudit() {
  return client.get('/config/audit')
}

export function restoreDefaults() {
  return client.post('/config/restore')
}
