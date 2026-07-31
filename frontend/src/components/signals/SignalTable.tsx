/**
 * 信号表格
 * - 分页（client-driven：page/limit 由 SignalFilters 控制）
 * - 行点击 → 触发 onSelect（由父组件打开 Drawer）
 * - 已在 SignalsView 通过 SignalFiltersBar 提供过滤条件
 *
 * 列：
 *  ID · 时间 · 等级 · 综合分 · 4 维分项 · 结果 · 状态
 */
import { useMemo } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from 'sparkdesign';
import { Badge } from 'sparkdesign';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious, PaginationEllipsis } from 'sparkdesign';
import type { Signal } from '@/lib/api/types';
import { fmtClock, fmtNum, fmtPct } from '@/lib/utils/format';
import { levelOf, levelTone } from '@/lib/utils/signal';
import { cn } from '@/lib/utils/cn';

interface SignalTableProps {
  rows: Signal[];
  total: number;
  page: number;
  limit: number;
  loading: boolean;
  selectedId?: Signal['id'] | null;
  onSelect: (signal: Signal) => void;
  onPageChange: (page: number) => void;
}

function outcomeBadge(outcome: Signal['outcome']) {
  if (!outcome) {
    return { label: '待评估', tone: 'outline' as const };
  }
  if (outcome.result === 1) return { label: '盈利', tone: 'default' as const };
  if (outcome.result === 0) return { label: '持平', tone: 'secondary' as const };
  if (outcome.result === -1) return { label: '亏损', tone: 'destructive' as const };
  return { label: '待评估', tone: 'outline' as const };
}

function acknowledgementBadge(s: Signal) {
  if (s.acknowledged) {
    return { label: '已确认', tone: 'secondary' as const };
  }
  return { label: '未确认', tone: 'outline' as const };
}

function levelBadge(level: number | null) {
  // 兼容字符串 alert_level（归一化）
  const lvl = level != null && typeof level === 'number' ? level : 0;
  const tone = levelTone(lvl);
  return {
    label: lvl === 0 ? '—' : `L${lvl}`,
    cls:
      tone === 'danger'
        ? 'bg-[var(--color-danger)]/20 text-[var(--color-danger)]'
        : tone === 'warning'
          ? 'bg-[var(--color-warning)]/20 text-[var(--color-warning)]'
          : 'bg-[var(--color-info)]/20 text-[var(--color-info)]',
  };
}

export function SignalTable({
  rows,
  total,
  page,
  limit,
  loading,
  selectedId,
  onSelect,
  onPageChange,
}: SignalTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / limit));

  // 构造分页项：1 … [page-1] page [page+1] … totalPages
  const pages = useMemo(() => {
    const items: (number | 'ellipsis')[] = [];
    const add = (n: number) => items.push(n);
    add(1);
    const left = Math.max(2, page - 1);
    const right = Math.min(totalPages - 1, page + 1);
    if (left > 2) items.push('ellipsis');
    for (let i = left; i <= right; i++) add(i);
    if (right < totalPages - 1) items.push('ellipsis');
    if (totalPages > 1) add(totalPages);
    return items;
  }, [page, totalPages]);

  if (!loading && rows.length === 0) {
    return (
      <div className="msr-card p-10 text-center text-sm text-[var(--color-text-muted)]">
        没有匹配的信号。试试重置过滤条件或扩大日期范围。
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="msr-card overflow-x-auto p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[64px]">ID</TableHead>
              <TableHead className="w-[100px]">时间</TableHead>
              <TableHead className="w-[80px]">等级</TableHead>
              <TableHead className="w-[80px] text-right">综合分</TableHead>
              <TableHead className="w-[70px] text-right">GEX</TableHead>
              <TableHead className="w-[70px] text-right">VIX</TableHead>
              <TableHead className="w-[70px] text-right">Crypto</TableHead>
              <TableHead className="w-[80px] text-right">Darkpool</TableHead>
              <TableHead className="w-[80px]">结果</TableHead>
              <TableHead className="w-[80px]">状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((s) => {
              const lvlNum = levelOf(s);
              const lb = levelBadge(lvlNum);
              const ob = outcomeBadge(s.outcome);
              const ab = acknowledgementBadge(s);
              const selected = selectedId === s.id;
              return (
                <TableRow
                  key={s.id}
                  onClick={() => onSelect(s)}
                  onKeyDown={(e: React.KeyboardEvent<HTMLTableRowElement>) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelect(s);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`打开信号 ${s.id} 详情`}
                  className={cn(
                    'cursor-pointer transition-colors',
                    selected && 'bg-[var(--color-primary)]/10',
                  )}
                >
                  <TableCell className="font-mono text-xs text-[var(--color-text-muted)]">{s.id}</TableCell>
                  <TableCell className="font-mono text-xs">{fmtClock(s.trigger_time ?? s.timestamp)}</TableCell>
                  <TableCell>
                    <span
                      className={cn('inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', lb.cls)}
                    >
                      {lb.label}
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono font-semibold">
                    {fmtNum(s.total_score ?? s.resonance_score, 2)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs">{fmtNum(s.gex_score, 2)}</TableCell>
                  <TableCell className="text-right font-mono text-xs">{fmtNum(s.vix_score, 2)}</TableCell>
                  <TableCell className="text-right font-mono text-xs">{fmtNum(s.crypto_score, 2)}</TableCell>
                  <TableCell className="text-right font-mono text-xs">{fmtNum(s.darkpool_score, 2)}</TableCell>
                  <TableCell>
                    <Badge variant={ob.tone}>{ob.label}</Badge>
                    {s.outcome?.forward_return != null && (
                      <span
                        className={cn(
                          'ml-1 font-mono text-[10px]',
                          s.outcome.forward_return > 0
                            ? 'text-[var(--color-success)]'
                            : s.outcome.forward_return < 0
                              ? 'text-[var(--color-danger)]'
                              : 'text-[var(--color-text-muted)]',
                        )}
                      >
                        {fmtPct(s.outcome.forward_return, 2)}
                      </span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={ab.tone}>{ab.label}</Badge>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination className="justify-end">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => page > 1 && onPageChange(page - 1)}
                aria-disabled={page <= 1}
                className={cn(page <= 1 && 'pointer-events-none opacity-40')}
              />
            </PaginationItem>
            {pages.map((p, idx) =>
              p === 'ellipsis' ? (
                <PaginationItem key={`e-${idx}`}>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : (
                <PaginationItem key={p}>
                  <PaginationLink
                    isActive={p === page}
                    onClick={() => onPageChange(p)}
                    aria-current={p === page ? 'page' : undefined}
                  >
                    {p}
                  </PaginationLink>
                </PaginationItem>
              ),
            )}
            <PaginationItem>
              <PaginationNext
                onClick={() => page < totalPages && onPageChange(page + 1)}
                aria-disabled={page >= totalPages}
                className={cn(page >= totalPages && 'pointer-events-none opacity-40')}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      <p className="text-[10px] text-[var(--color-text-muted)] text-right font-mono">
        共 {total} 条 · 第 {page}/{totalPages} 页
      </p>
    </div>
  );
}

/** 表格骨架（加载态） */
export function SignalTableSkeleton({ rows = 10 }: { rows?: number }) {
  return (
    <div className="msr-card overflow-x-auto p-0">
      <Table aria-busy="true">
        <TableHeader>
          <TableRow>
            {Array.from({ length: 10 }).map((_, i) => (
              <TableHead key={i}>
                <div className="h-3 w-12 bg-[var(--color-border)] rounded animate-pulse" />
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: rows }).map((_, i) => (
            <TableRow key={i}>
              {Array.from({ length: 10 }).map((__, j) => (
                <TableCell key={j}>
                  <div className="h-3 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
