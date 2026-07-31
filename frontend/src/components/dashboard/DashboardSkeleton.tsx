/**
 * Dashboard 页面骨架
 */
export function DashboardSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="msr-card h-[240px] bg-[var(--color-bg-elevated)] animate-pulse" />
        <div className="lg:col-span-2 grid grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="msr-card h-[110px] bg-[var(--color-bg-elevated)] animate-pulse" />
          ))}
        </div>
      </div>
      <div className="msr-card h-[140px] bg-[var(--color-bg-elevated)] animate-pulse" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="msr-card h-[180px] bg-[var(--color-bg-elevated)] animate-pulse" />
        <div className="lg:col-span-2 msr-card h-[180px] bg-[var(--color-bg-elevated)] animate-pulse" />
      </div>
    </div>
  );
}