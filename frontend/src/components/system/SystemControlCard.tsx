/**
 * SystemControlCard — 手动采集 + 自动轮询开关 + 系统动作
 */
import { useState } from 'react';
import { Card, CardContent } from 'sparkdesign';
import { Button, Switch } from 'sparkdesign';
import { useAutoPolling, useManualCollect, useSetAutoPolling } from '@/lib/hooks/useSystem';
import { fmtClock } from '@/lib/utils/format';

export function SystemControlCard() {
  const manual = useManualCollect();
  const polling = useAutoPolling();
  const setPolling = useSetAutoPolling();
  const [lastResult, setLastResult] = useState<{
    success: number;
    error: number;
    mock: number;
    elapsed: number;
    at: string;
  } | null>(null);

  const handleManual = async () => {
    try {
      const r = await manual.mutateAsync();
      setLastResult({
        success: r.success_count ?? 0,
        error: r.error_count ?? 0,
        mock: r.mock_count ?? 0,
        elapsed: r.total_elapsed_sec ?? 0,
        at: new Date().toISOString(),
      });
    } catch {
      /* ErrorToast handles */
    }
  };

  const handleToggle = (v: boolean) => {
    setPolling.mutate(v);
  };

  return (
    <Card>
      <CardContent className="p-4">
        <h3 className="text-sm font-semibold mb-3">系统控制</h3>

        {/* Auto-polling toggle */}
        <div className="flex items-center justify-between py-2 border-t border-[var(--color-border)]">
          <div className="min-w-0 flex-1">
            <div className="text-xs font-medium">自动轮询</div>
            <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
              {polling.data
                ? `每 ${polling.data.interval_seconds}s 自动触发采集`
                : '加载中...'}
            </div>
          </div>
          <Switch
            checked={polling.data?.enabled ?? false}
            onCheckedChange={handleToggle}
            disabled={setPolling.isPending}
            aria-label="切换自动轮询"
          />
        </div>

        {/* Manual collect */}
        <div className="flex items-center justify-between py-2 border-t border-[var(--color-border)]">
          <div className="min-w-0 flex-1">
            <div className="text-xs font-medium">手动触发采集</div>
            <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
              立即运行一个完整 pipeline cycle
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleManual}
            disabled={manual.isPending}
            aria-label="手动触发采集"
          >
            {manual.isPending ? '采集中...' : '立即采集'}
          </Button>
        </div>

        {/* Last manual result */}
        {lastResult && (
          <div
            role="status"
            className="mt-2 rounded border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2 text-xs"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold">最近一次手动结果</span>
              <span className="text-[10px] text-[var(--color-text-muted)] font-mono">
                {fmtClock(lastResult.at)}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-2 text-center">
              <div>
                <div className="text-[10px] text-[var(--color-text-muted)]">成功</div>
                <div className="msr-number text-[var(--color-success)]">{lastResult.success}</div>
              </div>
              <div>
                <div className="text-[10px] text-[var(--color-text-muted)]">错误</div>
                <div className="msr-number text-[var(--color-danger)]">{lastResult.error}</div>
              </div>
              <div>
                <div className="text-[10px] text-[var(--color-text-muted)]">Mock</div>
                <div className="msr-number text-[var(--color-warning)]">{lastResult.mock}</div>
              </div>
              <div>
                <div className="text-[10px] text-[var(--color-text-muted)]">耗时</div>
                <div className="msr-number">{lastResult.elapsed.toFixed(1)}s</div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}