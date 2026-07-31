/**
 * Zustand UI store
 * - theme/style（Spark Design 双维度）
 * - sidebar collapsed
 * - last update timestamp
 * - WS connection state（同时由 WebSocketProvider 同步）
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type SparkTheme = 'light' | 'dark' | 'light-parchment' | 'dark-parchment';
export type SparkStyle = 'neutral' | 'compact' | 'soft' | 'sharp' | 'dense';
export type WSConnectionState = 'connecting' | 'open' | 'closed' | 'reconnecting';

interface UIState {
  theme: SparkTheme;
  style: SparkStyle;
  sidebarCollapsed: boolean;
  wsState: WSConnectionState;
  lastUpdateAt: string | null;
  setTheme: (t: SparkTheme) => void;
  setStyle: (s: SparkStyle) => void;
  toggleSidebar: () => void;
  setWSState: (s: WSConnectionState) => void;
  setLastUpdateAt: (iso: string) => void;
}

const defaultTheme = (import.meta.env.VITE_DEFAULT_THEME as SparkTheme) || 'dark';
const defaultStyle = (import.meta.env.VITE_DEFAULT_STYLE as SparkStyle) || 'neutral';

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: defaultTheme,
      style: defaultStyle,
      sidebarCollapsed: false,
      wsState: 'connecting',
      lastUpdateAt: null,
      setTheme: (theme) => set({ theme }),
      setStyle: (style) => set({ style }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setWSState: (wsState) => set({ wsState }),
      setLastUpdateAt: (lastUpdateAt) => set({ lastUpdateAt }),
    }),
    {
      name: 'msr-ui-state',
      partialize: (s) => ({ theme: s.theme, style: s.style, sidebarCollapsed: s.sidebarCollapsed }),
    },
  ),
);

/** 把 Spark theme + style 组合写到 root 的 data-* 属性 */
export function applySparkTheme(theme: SparkTheme, style: SparkStyle) {
  if (typeof document === 'undefined') return;
  const el = document.documentElement;
  // dark + style / light + style
  const darkLike = theme.startsWith('dark');
  el.setAttribute('data-theme', darkLike ? `dark${theme.endsWith('parchment') ? '-parchment' : ''}` : theme.replace('parchment', '-parchment'));
  el.setAttribute('data-style', style);
}