import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import wsClient from './api/websocket'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')

// ponytail: WebSocket is the primary live-update channel; REST polling is the
// fallback. Stores subscribe to topics in their own setup; we just need to
// open the socket once at app boot.
wsClient.connect()

// ─── DEBUG: WebSocket + EventBus trace ────────────────────────────────
// 临时调试用 — 把 WS 收到的事件 + 状态写到 localStorage 方便 F12 console 看。
// 加 `?_debug=ws` 到 URL 启用详细日志；无参数时只输出摘要。
const DEBUG_KEY = 'msr_debug_ws'
const urlParams = new URLSearchParams(window.location.search)
const verbose = urlParams.has('_debug')

function debugLog(msg: string, payload?: unknown) {
  const ts = new Date().toISOString().substring(11, 19)
  const line = payload !== undefined
    ? `[${ts}] ${msg} ${JSON.stringify(payload).slice(0, 200)}`
    : `[${ts}] ${msg}`
  // eslint-disable-next-line no-console
  console.log('%c[MSR-WS]', 'color:#0ff;font-weight:bold', line)
  // 也写到 localStorage 方便关掉 devtools 后看
  try {
    const hist = JSON.parse(localStorage.getItem(DEBUG_KEY) || '[]') as string[]
    hist.push(line)
    if (hist.length > 100) hist.splice(0, hist.length - 100)
    localStorage.setItem(DEBUG_KEY, JSON.stringify(hist))
  } catch { /* ignore */ }
}

debugLog('App booted, connecting WebSocket...')

wsClient.subscribe('*', (msg: { topic: string; payload: any }) => {
  if (verbose) debugLog(`evt ${msg.topic}`, msg.payload)
  else if (msg.topic === 'data.fetch.complete') {
    const src = msg.payload?.source
    debugLog(`fetch.complete: ${src}`)
  }
})

// 把 WS 状态写到 window 方便 console 抓
;(window as any).__msrWs = wsClient
;(window as any).__msrDebugLog = debugLog
;(window as any).__msrGetDebugLog = () => {
  try { return JSON.parse(localStorage.getItem(DEBUG_KEY) || '[]') } catch { return [] }
}
debugLog('Subscribed. Open F12 console for [MSR-WS] logs. Use `__msrGetDebugLog()` to read history.')
