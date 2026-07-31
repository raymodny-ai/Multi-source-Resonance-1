<template>
  <div class="app-container">
    <Sidebar />
    <div class="main-wrapper">
      <Header />
      <main class="main-content">
        <router-view />
      </main>
      <Footer />
    </div>
    <ErrorToast />
  </div>
</template>

<script setup lang="ts">
import Sidebar from '@/components/layout/Sidebar.vue'
import Header from '@/components/layout/Header.vue'
import Footer from '@/components/layout/Footer.vue'
import ErrorToast from '@/components/common/ErrorToast.vue'
</script>

<style>
/* Global design tokens — dark financial monitor theme */
:root {
  --bg-primary: #0a0a1a;
  --bg-secondary: #111128;
  --bg-tertiary: #1a1a3e;
  --glass-bg: rgba(255, 255, 255, 0.05);
  --glass-border: rgba(255, 255, 255, 0.1);
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  --text-primary: #f0f0f5;
  --text-secondary: #a0a0b5;
  --text-muted: #6b6b80;
  --accent-indigo: #6366f1;
  --accent-cyan: #22d3ee;
  --accent-green: #10b981;
  --accent-amber: #f59e0b;
  --accent-red: #ef4444;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --spacing-xs: 8px;
  --spacing-sm: 12px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --sidebar-width: 240px;
  --header-height: 56px;
  --footer-height: 36px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  overflow: hidden;
  height: 100vh;
}

#app {
  height: 100vh;
}

.app-container {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
  background: var(--bg-primary);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}
::-webkit-scrollbar-thumb {
  background: var(--glass-border);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* Utility classes */
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
  padding: var(--spacing-lg);
}

.text-green { color: var(--accent-green); }
.text-red { color: var(--accent-red); }
.text-amber { color: var(--accent-amber); }
.text-cyan { color: var(--accent-cyan); }
.text-indigo { color: var(--accent-indigo); }
.text-muted { color: var(--text-secondary); }

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.badge-green { background: rgba(16, 185, 129, 0.15); color: var(--accent-green); }
.badge-red { background: rgba(239, 68, 68, 0.15); color: var(--accent-red); }
.badge-amber { background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); }
.badge-indigo { background: rgba(99, 102, 241, 0.15); color: var(--accent-indigo); }

@keyframes pulse-glow {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.animate-pulse {
  animation: pulse-glow 2s ease-in-out infinite;
}
</style>
