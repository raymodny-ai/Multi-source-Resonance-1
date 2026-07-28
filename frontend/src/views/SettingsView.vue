<template>
  <div class="settings-view">
    <div class="settings-grid">
      <!-- System Config -->
      <div class="glass-card">
        <h3 class="section-title">系统参数</h3>
        <div class="config-list">
          <div v-for="cfg in configs" :key="cfg.key" class="config-row">
            <div class="config-info">
              <span class="config-key">{{ cfg.key }}</span>
              <span class="config-desc">{{ cfg.description || '—' }}</span>
            </div>
            <div class="config-edit">
              <input v-model="editValues[cfg.key]" class="config-input" :placeholder="cfg.value" />
              <button class="save-btn" @click="saveConfig(cfg.key)">保存</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Data Source Config -->
      <div class="glass-card">
        <h3 class="section-title">数据源配置</h3>
        <div class="source-list">
          <div v-for="src in sources" :key="src.name" class="source-row">
            <span class="source-name">{{ src.name }}</span>
            <div class="source-badges">
              <span class="badge" :class="src.has_api_key ? 'badge-green' : 'badge-amber'">
                {{ src.has_api_key ? '有 Key' : '无 Key' }}
              </span>
              <span class="badge" :class="src.mock_mode ? 'badge-amber' : 'badge-green'">
                {{ src.mock_mode ? 'Mock' : 'Live' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Defaults -->
      <div class="glass-card">
        <h3 class="section-title">默认配置</h3>
        <div class="defaults-list" v-if="defaults">
          <div v-for="(val, key) in defaults" :key="key" class="default-row">
            <span class="default-key">{{ key }}</span>
            <span class="default-val">{{ val }}</span>
          </div>
        </div>
        <button class="restore-btn" @click="handleRestore">恢复默认配置</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getConfig, updateConfig, getConfigDefaults, getConfigSources, restoreDefaults } from '@/api/config'

const configs = ref<any[]>([])
const sources = ref<any[]>([])
const defaults = ref<Record<string, any>>({})
const editValues = reactive<Record<string, string>>({})

async function saveConfig(key: string) {
  const value = editValues[key]
  if (value !== undefined && value !== '') {
    await updateConfig(key, value)
  }
}

async function handleRestore() {
  await restoreDefaults()
  await loadConfigs()
}

async function loadConfigs() {
  const [cfgResp, srcResp, defResp] = await Promise.all([
    getConfig(),
    getConfigSources(),
    getConfigDefaults(),
  ])
  configs.value = cfgResp.data.configs
  sources.value = srcResp.data
  defaults.value = defResp.data
  configs.value.forEach((c: any) => { editValues[c.key] = c.value })
}

onMounted(loadConfigs)
</script>

<style scoped>
.settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-md); }
.section-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-sm); text-transform: uppercase; }
.config-list { display: flex; flex-direction: column; gap: 16px; }
.config-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.config-info { display: flex; flex-direction: column; gap: 2px; }
.config-key { font-size: 13px; font-weight: 600; }
.config-desc { font-size: 11px; color: var(--text-muted); }
.config-edit { display: flex; gap: 6px; }
.config-input { background: var(--bg-tertiary); border: 1px solid var(--glass-border); color: var(--text-primary); padding: 4px 8px; border-radius: 6px; font-size: 13px; width: 120px; }
.save-btn { background: rgba(99,102,241,0.2); color: var(--accent-indigo); border: none; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.source-list { display: flex; flex-direction: column; gap: 12px; }
.source-row { display: flex; justify-content: space-between; align-items: center; }
.source-name { font-size: 14px; font-weight: 600; }
.source-badges { display: flex; gap: 6px; }
.defaults-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
.default-row { display: flex; justify-content: space-between; font-size: 13px; }
.default-key { color: var(--text-muted); }
.default-val { font-weight: 600; }
.restore-btn { background: rgba(239,68,68,0.15); color: var(--accent-red); border: 1px solid rgba(239,68,68,0.3); padding: 8px 20px; border-radius: 8px; cursor: pointer; font-size: 13px; width: 100%; }
.restore-btn:hover { background: rgba(239,68,68,0.25); }
</style>
