/**
 * GEX Summary 表格 — 全部符号最新汇总（点击切换到对应 symbol）
 */
import { Card, CardContent } from 'sparkdesign';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from 'sparkdesign';
import type { GEXSummaryItem } from '@/lib/api/types';
import { fmtNum, fmtRelative } from '@/lib/utils/format';
import { GEXCompactTone } from '@/components/gex/GEXSymbolTabs';
import { cn } from '@/lib/utils/cn';
import type { GEXSymbol } from '@/lib/api/gex';

interface Props {
  rows: GEXSummaryItem[];
  active?: GEXSymbol;
  onSelect?: (s: GEXSymbol) => void;
  loading?: boolean;
}

export function GEXSymbolSummaryGrid({ rows, active, onSelect, loading }: Props) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-32 bg-[var(--color-border)] rounded mb-3 animate-pulse" />
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-7 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">全部符号概览</h3>
          <span className="text-[10px] text-[var(--color-text-muted)]">
            {rows.length} 符号
          </span>
        </div>
        {rows.length === 0 ? (
          <div className="h-[120px] flex items-center justify-center text-sm text-[var(--color-text-muted)]">
            暂无数据
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead className="text-right">Spot</TableHead>
                <TableHead className="text-right">Net GEX</TableHead>
                <TableHead className="text-right">Call Wall</TableHead>
                <TableHead className="text-right">Put Wall</TableHead>
                <TableHead>更新</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => {
                const sym = (r as { symbol?: string }).symbol ?? '';
                const isMock = Boolean((r as { is_mock?: boolean }).is_mock);
                const isActive = sym === active;
                const ts = (r as { timestamp?: string }).timestamp ?? null;
                return (
                  <TableRow
                    key={sym}
                    onClick={() => onSelect && sym && onSelect(sym as GEXSymbol)}
                    onKeyDown={(e: React.KeyboardEvent<HTMLTableRowElement>) => {
                      if (!onSelect || !sym) return;
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onSelect(sym as GEXSymbol);
                      }
                    }}
                    tabIndex={onSelect ? 0 : -1}
                    role={onSelect ? 'button' : undefined}
                    aria-pressed={isActive}
                    aria-label={`切换到 ${sym}`}
                    className={cn(
                      'cursor-pointer transition-colors',
                      isActive && 'bg-[var(--color-primary)]/10',
                    )}
                  >
                    <TableCell className="font-mono font-semibold">
                      {sym}
                      <span className="ml-2 inline-block align-middle">
                        <GEXCompactTone netGex={r.net_gex ?? null} isMock={isMock} />
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">{fmtNum(r.spot_price ?? null, 2)}</TableCell>
                    <TableCell className="text-right font-mono">{fmtNum(r.net_gex ?? null, 2)}</TableCell>
                    <TableCell className="text-right font-mono">{fmtNum(r.call_wall ?? null, 2)}</TableCell>
                    <TableCell className="text-right font-mono">{fmtNum(r.put_wall ?? null, 2)}</TableCell>
                    <TableCell className="font-mono text-[10px] text-[var(--color-text-muted)]">
                      {fmtRelative(ts)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
