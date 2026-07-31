/**
 * App 根组件 + 路由配置
 * PRD §3.1 — 9 个页面
 * - P1 实现：Dashboard (/) + Signals (/signals)
 * - 其余用 PlaceholderView 占位，待 P2 / P3 替换
 */
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { ErrorToast } from '@/components/ErrorToast';
import { DashboardView } from '@/views/DashboardView';
import { GEXView } from '@/views/GEXView';
import { VIXView } from '@/views/VIXView';
import { CryptoView } from '@/views/CryptoView';
import { DarkpoolView } from '@/views/DarkpoolView';
import { SignalsView } from '@/views/SignalsView';
import { AnalysisView } from '@/views/AnalysisView';
import { SystemView } from '@/views/SystemView';
import { SettingsView } from '@/views/SettingsView';

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    errorElement: (
      <div className="p-10 text-center">
        <h1 className="text-2xl font-semibold mb-2">页面加载出错</h1>
        <p className="text-sm text-[var(--color-text-muted)]">请刷新页面或检查网络连接。</p>
      </div>
    ),
    children: [
      { index: true, element: <DashboardView /> },
      { path: 'gex', element: <GEXView /> },
      { path: 'vix', element: <VIXView /> },
      { path: 'crypto', element: <CryptoView /> },
      { path: 'darkpool', element: <DarkpoolView /> },
      { path: 'signals', element: <SignalsView /> },
      { path: 'analysis', element: <AnalysisView /> },
      { path: 'system', element: <SystemView /> },
      { path: 'settings', element: <SettingsView /> },
      {
        path: '*',
        element: (
          <div className="p-10 text-center">
            <h1 className="text-2xl font-semibold mb-2">404</h1>
            <p className="text-sm text-[var(--color-text-muted)]">页面不存在或尚未实现。</p>
          </div>
        ),
      },
    ],
  },
]);

export function App() {
  return (
    <>
      <RouterProvider router={router} />
      <ErrorToast />
    </>
  );
}
