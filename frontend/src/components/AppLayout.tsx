/**
 * App Shell 布局：Sidebar + TopBar + Content Outlet
 */
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function AppLayout() {
  return (
    <div className="flex h-full w-full">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6 bg-[var(--color-bg-base)]" role="main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}