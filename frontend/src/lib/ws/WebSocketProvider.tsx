/**
 * WebSocket 客户端 + Provider
 *
 * 功能：
 * - 单连接 /ws
 * - 自动重连（指数退避，1s → 2s → 4s → 8s → 15s 上限）
 * - 订阅回调（每条消息 fan-out 给所有 subscriber）
 * - 连接状态暴露给 UI store + 全局 `msr-ws-status` CustomEvent
 * - WS URL：dev 用 same-origin（Vite proxy /ws），standalone 用 VITE_WS_PORT 拼
 */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from 'react';
import { useUIStore, type WSConnectionState } from '@/lib/stores/ui';
import type { WSMessage } from '@/lib/api/types';

export const wsStatusEventName = 'msr-ws-status';

export type WSHandler = (msg: WSMessage) => void;

export interface WSContextValue {
  subscribe: (handler: WSHandler) => () => void;
  send: (msg: WSMessage) => void;
  state: WSConnectionState;
}

const WSContext = createContext<WSContextValue | null>(null);

/** 计算 WS URL */
function resolveWsUrl(): string {
  // 浏览器 API：window.location.protocol === 'http:' → ws:, https: → wss:
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.hostname || 'localhost';
  // FIX-42 改进：只要页面当前端口 ≠ 后端端口(8525)，就视为存在同源 ``/ws`` 反代
  // （vite dev 或 nginx 都配了 ``/ws`` → 8525）。这样无论 dev server 跑在 5173 / 5175 /
  // 4173 还是任意自定义端口，WS 都走与 http 同源的反代路径，不硬编码端口列表。
  const port = window.location.port;
  const backendPort = import.meta.env.VITE_WS_PORT || '8525';
  if (port && port !== backendPort) {
    // 页面端口 ≠ 后端端口 → 走 same-origin /ws（推荐，与 http 一致，经 vite/nginx 反代）
    return `${proto}//${host}:${port}/ws`;
  }
  // standalone：直接打开后端 8525（无反代）时，用 VITE_WS_PORT 拼真实后端地址
  return `${proto}//${host}:${backendPort}/ws`;
}

class WSClient {
  private url: string;
  private ws: WebSocket | null = null;
  private handlers = new Set<WSHandler>();
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private explicitClose = false;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  /** 当前连接状态（暴露给 provider 通过 getState() 读取） */
  public currentState: WSConnectionState = 'connecting';

  constructor(url: string) {
    this.url = url;
  }

  getState(): WSConnectionState {
    return this.currentState;
  }

  start() {
    this.explicitClose = false;
    this.connect();
  }

  stop() {
    this.explicitClose = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
    this.ws?.close();
  }

  subscribe(handler: WSHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  send(msg: WSMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  private setState(s: WSConnectionState) {
    this.currentState = s;
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(wsStatusEventName, { detail: s }));
    }
  }

  private connect() {
    this.setState(this.reconnectAttempts === 0 ? 'connecting' : 'reconnecting');
    try {
      this.ws = new WebSocket(this.url);
    } catch (err) {
      console.warn('[WS] connect failed', err);
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setState('open');
      this.startHeartbeat();
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      if (!this.explicitClose) {
        this.setState('closed');
        this.scheduleReconnect();
      } else {
        this.setState('closed');
      }
    };

    this.ws.onerror = () => {
      // onerror 后通常会触发 onclose，无需重复处理
    };

    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data) as WSMessage;
        this.handlers.forEach((h) => h(msg));
      } catch (err) {
        console.warn('[WS] parse error', err);
      }
    };
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    // 每 30s 发一个 ping；后端目前没有回复 pong 也 OK——心跳只用于让某些 proxy 知道连接活着
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try { this.ws.send(JSON.stringify({ type: 'ping' } as unknown as WSMessage)); } catch { /* ignore */ }
      }
    }, 30_000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect() {
    if (this.explicitClose) return;
    const delays = [1000, 2000, 4000, 8000, 15000];
    const idx = Math.min(this.reconnectAttempts, delays.length - 1);
    const wait = delays[idx];
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => this.connect(), wait);
  }
}

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const setWSState = useUIStore((s) => s.setWSState);
  // FIX-51: lazy-initialise the WS client from inside ``useEffect``
  // rather than during render. The previous version constructed
  // ``new WSClient(...)`` during the render phase, which (a) ran the
  // constructor twice under React StrictMode, (b) created a stale
  // connection on HMR, and (c) technically violated the React rule
  // against side effects in render.
  const clientRef = useRef<WSClient | null>(null);
  if (clientRef.current === null && typeof window !== 'undefined') {
    clientRef.current = new WSClient(resolveWsUrl());
  }

  useEffect(() => {
    const client = clientRef.current;
    if (!client) return;
    // ``start()`` opens the underlying WebSocket. We've now ensured
    // the client only exists once per provider mount; the effect
    // simply attaches the listener and binds teardown.
    client.start();
    const handler = (ev: Event) => {
      const detail = (ev as CustomEvent<WSConnectionState>).detail;
      setWSState(detail);
    };
    window.addEventListener(wsStatusEventName, handler);
    return () => {
      window.removeEventListener(wsStatusEventName, handler);
      client.stop();
    };
  }, [setWSState]);

  const value = useMemo<WSContextValue>(
    () => ({
      subscribe: (h) => clientRef.current?.subscribe(h) ?? (() => {}),
      send: (m) => clientRef.current?.send(m),
      get state() {
        return clientRef.current?.getState() ?? 'connecting';
      },
    }),
    [],
  );

  return <WSContext.Provider value={value}>{children}</WSContext.Provider>;
}

export function useWebSocketContext(): WSContextValue | null {
  return useContext(WSContext);
}