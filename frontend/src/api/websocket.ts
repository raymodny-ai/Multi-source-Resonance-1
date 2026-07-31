export interface WSMessage {
  topic: string
  payload: Record<string, any>
  timestamp: string
  /** Optional severity for the UI to colour-code toasts / banners. */
  level?: 'info' | 'warning' | 'error' | 'success'
}

type WSHandler = (msg: WSMessage) => void
type WSStateHandler = (state: { connected: boolean }) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private handlers: Map<string, Set<WSHandler>> = new Map()
  private stateHandlers: Set<WSStateHandler> = new Set()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectInterval = 3000
  private maxReconnectInterval = 30000
  private currentInterval = this.reconnectInterval
  private shouldReconnect = true
  private _connectionState: 'idle' | 'connecting' | 'open' | 'closed' = 'idle'

  get connectionState(): 'idle' | 'connecting' | 'open' | 'closed' {
    return this._connectionState
  }

  get isConnected(): boolean {
    return this._connectionState === 'open'
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    // ponytail: WS port fallback — reads VITE_WS_PORT at build time.
    // 8524 was the legacy MSR port (server dead since 7-25); 8525 is MSR-1 v3.1.
    // Override with VITE_WS_PORT=xxxx in frontend/.env if backend moves.
    // When Vite dev proxy is in front (default at :5173), this is unused —
    // vite.config.ts routes /ws to ws://localhost:8525.
    const port =
      window.location.port ||
      (import.meta.env.VITE_WS_PORT as string | undefined) ||
      '8525'
    const url = `${protocol}//${host}:${port}/ws`

    this.shouldReconnect = true
    this._connectionState = 'connecting'
    this.emitStatusChange()
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('[WS] Connected')
      this.currentInterval = this.reconnectInterval
      this._connectionState = 'open'
      this.emitStatusChange()
    }

    this.ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        this.dispatch(msg)
      } catch (e) {
        console.warn('[WS] Failed to parse message:', e)
      }
    }

    this.ws.onclose = () => {
      console.log('[WS] Disconnected')
      this._connectionState = 'closed'
      this.emitStatusChange()
      if (this.shouldReconnect) {
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WS] Error:', error)
      this._connectionState = 'closed'
      this.emitStatusChange()
      this.ws?.close()
    }
  }

  disconnect() {
    this.shouldReconnect = false
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.ws?.close()
    this.ws = null
    this._connectionState = 'closed'
    this.emitStatusChange()
  }

  subscribe(topic: string, handler: WSHandler) {
    if (!this.handlers.has(topic)) {
      this.handlers.set(topic, new Set())
    }
    this.handlers.get(topic)!.add(handler)
  }

  unsubscribe(topic: string, handler: WSHandler) {
    this.handlers.get(topic)?.delete(handler)
  }

  onConnectionStateChange(handler: WSStateHandler) {
    this.stateHandlers.add(handler)
    // Fire once with current state so the subscriber is in sync.
    handler({ connected: this.isConnected })
  }

  offConnectionStateChange(handler: WSStateHandler) {
    this.stateHandlers.delete(handler)
  }

  send(data: Record<string, any>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  private dispatch(msg: WSMessage) {
    // Dispatch to topic-specific handlers
    this.handlers.get(msg.topic)?.forEach((h) => h(msg))
    // Dispatch to wildcard handlers
    this.handlers.get('*')?.forEach((h) => h(msg))
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      console.log(`[WS] Reconnecting (interval: ${this.currentInterval}ms)`)
      this.connect()
    }, this.currentInterval)
    this.currentInterval = Math.min(this.currentInterval * 1.5, this.maxReconnectInterval)
  }

  private emitStatusChange() {
    const connected = this.isConnected
    this.stateHandlers.forEach((h) => h({ connected }))
    try {
      window.dispatchEvent(
        new CustomEvent('msr-ws-status', { detail: { connected } }),
      )
    } catch {
      // best-effort
    }
  }
}

// Singleton instance
export const wsClient = new WebSocketClient()
export default wsClient

