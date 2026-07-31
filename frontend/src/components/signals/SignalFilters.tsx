/**
 * Signals 过滤器条
 * - Level (all / 1 / 2 / 3)
 * - Outcome (all / profit / breakeven / loss / pending)
 * - Search (按时间或标签)
 * - Date range (startDate / endDate)
 * - Reset
 */
import type { SignalFilters } from '@/lib/hooks/useSignals';
import type { SignalLevelFilter, SignalOutcomeFilter } from '@/lib/api/types';
import { Button } from 'sparkdesign';
import { Input } from 'sparkdesign';
import { InputGroup, InputGroupInput } from 'sparkdesign';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from 'sparkdesign';
import { cn } from '@/lib/utils/cn';

const LEVEL_OPTIONS: { value: SignalLevelFilter; label: string }[] = [
  { value: 'all', label: '全部等级' },
  { value: '1', label: 'L1 提示' },
  { value: '2', label: 'L2 警告' },
  { value: '3', label: 'L3 严重' },
];

const OUTCOME_OPTIONS: { value: SignalOutcomeFilter; label: string }[] = [
  { value: 'all', label: '全部结果' },
  { value: 'profit', label: '盈利' },
  { value: 'breakeven', label: '持平' },
  { value: 'loss', label: '亏损' },
  { value: 'pending', label: '待评估' },
];

interface SignalFiltersBarProps {
  filters: SignalFilters;
  update: (patch: Partial<SignalFilters>) => void;
  reset: () => void;
}

export function SignalFiltersBar({ filters, update, reset }: SignalFiltersBarProps) {
  const isFiltered =
    filters.level !== 'all' ||
    filters.outcome !== 'all' ||
    filters.search !== '' ||
    filters.startDate !== null ||
    filters.endDate !== null;

  return (
    <div
      className={cn(
        'msr-card flex flex-wrap items-end gap-3 p-3',
        'sticky top-0 z-10 backdrop-blur supports-[backdrop-filter]:bg-[var(--color-bg-container)]/80',
      )}
      role="search"
      aria-label="信号过滤"
    >
      {/* Search */}
      <div className="flex-1 min-w-[200px]">
        <label className="block text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
          搜索
        </label>
        <InputGroup>
          <InputGroupInput
            type="text"
            value={filters.search}
            placeholder="按标签 / 时间 / ID…"
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => update({ search: e.target.value })}
            aria-label="搜索信号"
          />
        </InputGroup>
      </div>

      {/* Level */}
      <div className="w-[140px]">
        <label className="block text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
          等级
        </label>
        <Select value={filters.level} onValueChange={(v: string) => update({ level: v as SignalLevelFilter })}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LEVEL_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Outcome */}
      <div className="w-[140px]">
        <label className="block text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
          结果
        </label>
        <Select
          value={filters.outcome}
          onValueChange={(v: string) => update({ outcome: v as SignalOutcomeFilter })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {OUTCOME_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Date range */}
      <div className="w-[150px]">
        <label className="block text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
          起始日期
        </label>
        <Input
          type="date"
          value={filters.startDate ?? ''}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            update({ startDate: e.target.value || null })
          }
          aria-label="起始日期"
        />
      </div>

      <div className="w-[150px]">
        <label className="block text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] mb-1">
          结束日期
        </label>
        <Input
          type="date"
          value={filters.endDate ?? ''}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            update({ endDate: e.target.value || null })
          }
          aria-label="结束日期"
        />
      </div>

      {/* Reset */}
      <Button
        variant={isFiltered ? 'primary' : 'outline'}
        size="sm"
        disabled={!isFiltered}
        onClick={reset}
        aria-label="重置过滤器"
      >
        重置
      </Button>
    </div>
  );
}
