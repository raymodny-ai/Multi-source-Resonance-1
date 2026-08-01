import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

// MSR-1 v4.0 frontend — React 19 + Spark Design + Vite 6
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    // SEC-12: bind localhost by default so the dev server isn't
    // reachable from the LAN unless the operator explicitly opts in
    // via ``MSR_VITE_HOST=0.0.0.0``.
    host: process.env.MSR_VITE_HOST || 'localhost',
    proxy: {
      '/api': {
        target: 'http://localhost:8525',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8525',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    target: 'es2022',
    chunkSizeWarningLimit: 1500,
  },
});