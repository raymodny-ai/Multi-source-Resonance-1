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
import { SignalsView } from '@/views/SignalsView';
import { PlaceholderView } from '@/views/PlaceholderView';

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
      {
        path: 'gex',
        element: (
          <PlaceholderView
            title="GEX"
            description="期权伽马暴露分析"
            milestone="P2"
            features={[
              '按到期日 / Strike 的 Gamma 分布热图',
              '净 GEX 走势（实时 + 历史回放）',
              '关键 Flip Point 标识（Call/Put 主导切换）',
              '与共振分数的协动分析',
            ]}
          />
        ),
      },
      {
        path: 'vix',
        element: (
          <PlaceholderView
            title="VIX"
            description="波动率期限结构与衍生指标"
            milestone="P2"
            features={[
              'VIX/VIX3M/VIX9D 实时走势',
              '期限结构曲线（Contango/Backwardation）',
              '波动率风险溢价（VRP）计算',
              '历史分位与回归模型',
            ]}
          />
        ),
      },
      {
        path: 'crypto',
        element: (
          <PlaceholderView
            title="Crypto"
            description="加密衍生品监控"
            milestone="P2"
            features={[
              'BTC/ETH 永续费率与持仓量',
              '现货/期货基差（Basis）走势',
              '爆仓事件追踪与归因',
              '链上清算热力图',
            ]}
          />
        ),
      },
      {
        path: 'darkpool',
        element: (
          <PlaceholderView
            title="Dark Pool"
            description="暗池机构流动监控"
            milestone="P2"
            features={[
              'FINRA ADF 大宗成交流',
              '异常 block trade 警报',
              '板块 / 个股资金净流向',
              '与价格走势的时滞分析',
            ]}
          />
        ),
      },
      { path: 'signals', element: <SignalsView /> },
      {
        path: 'analysis',
        element: (
          <PlaceholderView
            title="Analysis"
            description="LLM 增强的多源分析"
            milestone="P3"
            features={[
              '多 LLM 验证（multi-verify）的统一解读',
              'Prompt 模板管理与版本化',
              '历史推理缓存与可解释性回溯',
              '对单条信号的深度归因',
            ]}
          />
        ),
      },
      {
        path: 'system',
        element: (
          <PlaceholderView
            title="System"
            description="系统健康与诊断"
            milestone="P3"
            features={[
              'Pipeline 状态 + 23 fetcher 健康矩阵',
              '数据库 / SQLite 维护入口',
              '手动触发采集 / 重跑 pipeline',
              'Prometheus 指标与告警规则',
            ]}
          />
        ),
      },
      {
        path: 'settings',
        element: (
          <PlaceholderView
            title="Settings"
            description="运行时配置"
            milestone="P3"
            features={[
              '采集周期 / 阈值热更新',
              '主题 / 样式切换（Spark 双维度）',
              'WebSocket 自动重连开关',
              '导出 CSV / 重置缓存',
            ]}
          />
        ),
      },
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
