/**
 * GEX Symbol Tabs — 6 个主符号切换（SPX/SPY/QQQ/IWM/AAPL/MSFT）
 */
import { Tabs, TabsList, TabsTrigger } from 'sparkdesign';
import { GEX_SYMBOLS, useGEXSummary } from '@/lib/hooks/useGEX';
import { cn } from '@/lib/utils/cn';
import type { GEXSymbol } from '@/lib/api/gex';

interface Props {
  active: GEXSymbol;
  onChange: (s: GEXSymbol) => void;
}

export function GEXSymbolTabs({ active, onChange }: Props) {
  const { data: summary } = useGEXSummary();
  return (
    <Tabs value={active} onValueChange={(v) => onChange(v as GEXSymbol)}>
      <TabsList>
        {GEX_SYMBOLS.map((sym) => {
          const row = summary?.find((r) => (r as { symbol?: string }).symbol === sym);
          const mock = row && (row as { is_mock?: boolean }).is_mock;
          return (
            <TabsTrigger key={sym} value={sym}>
              <span className="font-mono">{sym}</span>
              {mock && (
                <span
                  className="ml-1 text-[9px] font-bold text-[var(--color-warning)] bg-[var(--color-warning)]/15 px-1 rounded"
                  aria-label="模拟数据"
                  title="该符号当前为模拟数据"
                >
                  MOCK
                </span>
              )}
            </TabsTrigger>
          );
        })}
      </TabsList>
    </Tabs>
  );
}

/** 简化的「简要状态」小条 — 用于非 BFF 模式的 compact 视图 */
export function GEXCompactTone({ netGex, isMock }: { netGex: number | null; isMock: boolean }) {
  const tone = isMock
    ? 'bg-[var(--color-warning)]/15 text-[var(--color-warning)] border-[var(--color-warning)]/40'
    : netGex == null
      ? 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] border-[var(--color-border)]'
      : netGex > 0
        ? 'bg-[var(--color-success)]/15 text-[var(--color-success)] border-[var(--color-success)]/40'
        : 'bg-[var(--color-danger)]/15 text-[var(--color-danger)] border-[var(--color-danger)]/40';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider',
        tone,
      )}
    >
      {isMock ? 'MOCK' : netGex == null ? 'N/A' : netGex > 0 ? 'LONG-GAMMA' : 'SHORT-GAMMA'}
    </span>
  );
}
