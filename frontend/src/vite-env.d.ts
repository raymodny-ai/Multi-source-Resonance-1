/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend API base URL (e.g. http://localhost:8525). Empty = same-origin (dev proxy or prod nginx). */
  readonly VITE_API_BASE_URL: string;
  /** WebSocket port fallback when running without a /ws proxy. */
  readonly VITE_WS_PORT: string;
  /** Default Spark Design theme. */
  readonly VITE_DEFAULT_THEME: string;
  /** Default Spark Design layout scale. */
  readonly VITE_DEFAULT_STYLE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}