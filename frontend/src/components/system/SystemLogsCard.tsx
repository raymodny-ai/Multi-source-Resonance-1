/**
 * SystemLogsCard — 最近日志（in-memory buffer）
 */
import { useState } from 'react';
import { Card, CardContent } from 'sparkdesign';
import { useSystemLogs } from '@/lib/hooks/useSystem';
import { cn } from '@/lib/utils/cn';
import { fmtClock } from '@/lib/utils/format';

interface LogEntry {
  timestamp: string;
  level: string;
  source: string;
  message: string;
}

const LEVEL_TONE: Record<string, string> = {
  ERROR: 'bg-[var(--color-danger)]/15 text-[var(--color-danger)]',
  WARN: 'bg-[var(--color-warning)]/15 text-[var(--color-warning)]',
  WARNING: 'bg-[var(--color-warning)]/15 text-[var(--color-warning)]',
  INFO: 'bg-[var(--color-info)]/15 text-[var(--color-info)]',
  DEBUG: 'bg-[var(--color-text-muted)]/15 text-[var(--color-text-muted)]',
};

export function SystemLogsCard() {
  const [limit, setLimit] = useState(50);
  const { data, isLoading, error } = useSystemLogs(limit);
  const logs = (data ?? []) as LogEntry[];

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">系统日志</h3>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-[var(--color-text-muted)]">
              {logs.length} 条
            </span>
            <select
              value={String(limit)}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="text-[10px] bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded px-1.5 py-0.5 focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]"
              aria-label="日志条数"
            >
              <option value="20">20</option>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="200">200</option>
            </select>
          </div>
        </div>

        {error && (
          <div className="text-xs text-[var(--color-danger)] py-2">
            日志加载失败：{(error as Error).message}
          </div>
        )}

        {isLoading && logs.length === 0 ? (
          <div className="space-y-1">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-5 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        ) : logs.length === 0 ? (
          <div className="h-[80px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            暂无日志
          </div>
        ) : (
          <div className="max-h-[280px] overflow-y-auto pr-2">
            <ul className="space-y-0.5 font-mono text-[11px]">
              {logs.map((log, idx) => {
                const levelKey = (log.level ?? 'INFO').toUpperCase();
                const tone = LEVEL_TONE[levelKey] ?? LEVEL_TONE.INFO;
                return (
                  <li
                    key={`${log.timestamp}-${idx}`}
                    className="flex items-start gap-2 border-b border-[var(--color-border)]/30 py-1 last:border-b-0"
                  >
                    <span className="text-[10px] text-[var(--color-text-muted)] shrink-0 w-14">
                      {fmtClock(log.timestamp)}
                    </span>
                    <span
                      className={cn(
                        'inline-block px-1 rounded text-[9px] font-bold shrink-0 w-12 text-center uppercase',
                        tone,
                      )}
                    >
                      {levelKey}
                    </span>
                    <span className="text-[10px] text-[var(--color-text-secondary)] shrink-0 w-20 truncate" title={log.source}>
                      {log.source}
                    </span>
                    <span className="flex-1 min-w-0 break-all">{log.message}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}