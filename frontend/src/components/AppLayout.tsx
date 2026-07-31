/**
 * App Shell 布局：Sidebar + TopBar + Content Outlet
 * - 桌面：固定 sidebar + content
 * - 平板：可折叠 icon-only sidebar
 * - 移动：抽屉式 sidebar + 内容占满
 */
import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { cn } from '@/lib/utils/cn';

export function AppLayout() {
  const sidebarCollapsed = false; // 由 Sidebar 内部管理
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mq = window.matchMedia('(max-width: 767px)');
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);

  // ESC 关闭移动 drawer
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mobileOpen]);

  // 切换路由时自动关闭移动 drawer
  useEffect(() => {
    if (isMobile) setMobileOpen(false);
  }, [isMobile]);

  return (
    <div className="flex h-full w-full">
      {/* 跳过导航链接（无障碍） */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-2 focus:rounded focus:bg-[var(--color-primary)] focus:text-white focus:outline-none"
      >
        跳转到主内容
      </a>

      {/* Desktop sidebar */}
      {!isMobile && (
        <Sidebar collapsed={sidebarCollapsed} variant="desktop" />
      )}

      {/* Mobile sidebar drawer */}
      {isMobile && (
        <>
          {/* Backdrop */}
          <div
            role="presentation"
            onClick={() => setMobileOpen(false)}
            className={cn(
              'fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity',
              mobileOpen ? 'opacity-100' : 'opacity-0 pointer-events-none',
            )}
            aria-hidden={!mobileOpen}
          />
          <div
            className={cn(
              'fixed inset-y-0 left-0 z-50 transform transition-transform',
              mobileOpen ? 'translate-x-0' : '-translate-x-full',
            )}
            role="dialog"
            aria-modal="true"
            aria-label="导航菜单"
          >
            <Sidebar collapsed={false} variant="mobile" onNavigate={() => setMobileOpen(false)} />
          </div>
        </>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onMobileMenuToggle={() => setMobileOpen((v) => !v)} showMobileMenu={isMobile} />
        <main
          id="main-content"
          className="flex-1 overflow-y-auto p-4 md:p-6 bg-[var(--color-bg-base)]"
          role="main"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}