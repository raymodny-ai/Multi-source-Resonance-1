export interface WSMessage {
  topic: string
  payload: Record<string, any>
  timestamp: string
}

type WSHandler = (msg: WSMessage) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private handlers: Map<string, Set<WSHandler>> = new Map()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectInterval = 3000
  private maxReconnectInterval = 30000
  private currentInterval = this.reconnectInterval
  private shouldReconnect = true

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = window.location.port || '8524'
    const url = `${protocol}//${host}:${port}/ws`

    this.shouldReconnect = true
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('[WS] Connected')
      this.currentInterval = this.reconnectInterval
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
      if (this.shouldReconnect) {
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = (error) => {
      console.error('[WS] Error:', error)
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
}

// Singleton instance
export const wsClient = new WebSocketClient()
export default wsClient
