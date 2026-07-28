import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '主仪表盘', icon: 'dashboard' },
  },
  {
    path: '/gex',
    name: 'GEX',
    component: () => import('@/views/GEXView.vue'),
    meta: { title: 'GEX 详情', icon: 'gamma' },
  },
  {
    path: '/vix',
    name: 'VIX',
    component: () => import('@/views/VIXView.vue'),
    meta: { title: 'VIX 期限结构', icon: 'vix' },
  },
  {
    path: '/crypto',
    name: 'Crypto',
    component: () => import('@/views/CryptoView.vue'),
    meta: { title: '加密衍生品', icon: 'crypto' },
  },
  {
    path: '/darkpool',
    name: 'Darkpool',
    component: () => import('@/views/DarkpoolView.vue'),
    meta: { title: '暗池数据', icon: 'darkpool' },
  },
  {
    path: '/signals',
    name: 'Signals',
    component: () => import('@/views/SignalsView.vue'),
    meta: { title: '信号历史', icon: 'signal' },
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/views/AnalysisView.vue'),
    meta: { title: '综合分析', icon: 'analysis' },
  },
  {
    path: '/system',
    name: 'System',
    component: () => import('@/views/SystemView.vue'),
    meta: { title: '系统管理', icon: 'system' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '系统配置', icon: 'settings' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || 'Monitor'} — Multi-source Resonance`
})

export default router
