<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="logo">MSR</h1>
      <span class="logo-sub">Resonance</span>
    </div>
    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: $route.path === item.path }"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>
    <div class="sidebar-footer">
      <div class="version">v3.1</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
const navItems = [
  { path: '/', label: '仪表盘', icon: '◉' },
  { path: '/gex', label: 'GEX', icon: 'Γ' },
  { path: '/vix', label: 'VIX', icon: 'σ' },
  { path: '/crypto', label: '加密', icon: '₿' },
  { path: '/darkpool', label: '暗池', icon: '◈' },
  { path: '/signals', label: '信号', icon: '⚡' },
  { path: '/analysis', label: '分析', icon: '◐' },
  { path: '/system', label: '系统', icon: '⚙' },
  { path: '/settings', label: '配置', icon: '☰' },
]
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-secondary);
  border-right: 1px solid var(--glass-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: 100vh;
}
.sidebar-header {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--glass-border);
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.logo {
  font-size: 22px;
  font-weight: 800;
  color: var(--accent-indigo);
  letter-spacing: 2px;
}
.logo-sub {
  font-size: 12px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
}
.sidebar-nav {
  flex: 1;
  padding: var(--spacing-sm) 0;
  overflow-y: auto;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 10px var(--spacing-lg);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}
.nav-item:hover {
  background: var(--glass-bg);
  color: var(--text-primary);
}
.nav-item.active {
  background: rgba(99, 102, 241, 0.1);
  color: var(--accent-indigo);
  border-left-color: var(--accent-indigo);
}
.nav-icon {
  font-size: 16px;
  width: 24px;
  text-align: center;
}
.sidebar-footer {
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--glass-border);
}
.version {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
