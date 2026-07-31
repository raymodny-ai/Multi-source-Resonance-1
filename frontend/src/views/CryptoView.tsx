/**
 * Crypto 页面 — 加密衍生品监控
 * PRD §4.4
 *
 * Layout:
 * - Top: CryptoMetricsCard (Funding + OI + ELR + flags)
 * - Middle: CryptoHistoryChart (Funding / OI dual-axis)
 * - Bottom: 风险说明 + 异常事件面板（最近 liquidation_spike 时间线）
 */
import { useMemo } from 'react';
import { PageHeader } from '@/components/PageHeader';
import { AlertBanner } from '@/components/AlertBanner';
import { Button } from 'sparkdesign';
import { CryptoMetricsCard } from '@/components/crypto/CryptoMetricsCard';
import { CryptoHistoryChart } from '@/components/crypto/CryptoHistoryChart';
import { useCryptoHistory, useCryptoLatest, useCryptoWSSync } from '@/lib/hooks/useCrypto';
import { useQueryClient } from '@tanstack/react-query';
import { useUIStore } from '@/lib/stores/ui';
import { fmtClock, fmtTime } from '@/lib/utils/format';
import { Card, CardContent } from 'sparkdesign';
import { cn } from '@/lib/utils/cn';

export function CryptoView() {
  useCryptoWSSync();
  const qc = useQueryClient();
  const setLastUpdateAt = useUIStore((s) => s.setLastUpdateAt);

  const latest = useCryptoLatest();
  const history = useCryptoHistory(30);

  const handleRefresh = () => {
    qc.invalidateQueries({ queryKey: ['crypto'] });
    setLastUpdateAt(new Date().toISOString());
  };

  const anomalies = useMemo(() => {
    const list: { ts: string; type: string }[] = [];
    (history.data ?? []).forEach((row) => {
      if (row.liquidation_spike) list.push({ ts: row.timestamp, type: '爆仓激增' });
      if (row.funding_anomaly) list.push({ ts: row.timestamp, type: '资金费率异常' });
      if (row.oi_crash) list.push({ ts: row.timestamp, type: 'OI 闪崩' });
      if (row.leverage_cleanup) list.push({ ts: row.timestamp, type: '杠杆清理' });
    });
    return list.slice(0, 30);
  }, [history.data]);

  const anomalyCount = (latest.data &&
    [latest.data.liquidation_spike, latest.data.funding_anomaly, latest.data.oi_crash, latest.data.leverage_cleanup].filter(Boolean).length) ||
    0;

  return (
    <>
      <PageHeader
        title="Crypto"
        description="加密货币衍生品监控 · BTC 资金费率 / 持仓量 / 异常事件"
        actions={
          <Button variant="outline" size="sm" onClick={handleRefresh} aria-label="手动刷新">
            刷新
          </Button>
        }
      />

      {latest.error && (
        <AlertBanner tone="danger" title="Crypto 数据加载失败">
          {(latest.error as Error).message}
        </AlertBanner>
      )}

      {anomalyCount >= 2 && (
        <AlertBanner tone="warning" title="检测到多个异常标记" className="mt-2" dismissible>
          当前 row 同时触发 <strong>{anomalyCount}</strong> 个异常标签，建议查看 Signals 是否触发共振警报。
        </AlertBanner>
      )}

      <div className="mt-4">
        <CryptoMetricsCard latest={latest.data ?? null} loading={latest.isLoading && !latest.data} />
      </div>

      <div className="mt-4">
        <CryptoHistoryChart
          history={history.data ?? []}
          loading={history.isLoading && !history.data}
          height={300}
        />
      </div>

      {/* Anomaly timeline */}
      <div className="mt-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold">异常事件时间线</h3>
              <span className="text-[10px] text-[var(--color-text-muted)]">最近 {anomalies.length} 条</span>
            </div>
            {anomalies.length === 0 ? (
              <div className="h-[100px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
                近 30 天未触发异常事件
              </div>
            ) : (
              <ul className="space-y-1 max-h-[220px] overflow-y-auto pr-2">
                {anomalies.map((a, idx) => (
                  <li
                    key={`${a.ts}-${a.type}-${idx}`}
                    className="flex items-center justify-between border-t border-[var(--color-border)] py-1.5 first:border-t-0"
                  >
                    <span className="text-xs font-mono text-[var(--color-text-muted)]">{fmtTime(a.ts)}</span>
                    <span className="text-xs text-[var(--color-text-primary)]">{fmtClock(a.ts)}</span>
                    <span
                      className={cn(
                        'inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider',
                        'bg-[var(--color-danger)]/15 text-[var(--color-danger)]',
                      )}
                    >
                      {a.type}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <p className="text-[10px] text-[var(--color-text-muted)] mt-6 font-mono">
        数据源 <span className="text-[var(--color-primary)] font-semibold">Coinglass / CryptoQuant / Bitfinex</span> ·
        上次更新：{latest.dataUpdatedAt ? new Date(latest.dataUpdatedAt).toLocaleString('zh-CN') : '—'}
      </p>
    </>
  );
}
