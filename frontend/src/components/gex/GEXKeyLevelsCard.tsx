/**
 * GEX 关键水平卡片 — Call Wall / Put Wall / Zero Gamma / Spot
 * 显示 4 个数值的卡片，按"距 spot 的位移"做小条
 */
import { Card, CardContent } from 'sparkdesign';
import { fmtNum, fmtPct } from '@/lib/utils/format';
import { cn } from '@/lib/utils/cn';

export interface GEXLevelRow {
  label: string;
  value: number | null;
  description: string;
  /** 优先级（用于 layout 排序） */
  weight: number;
}

interface Props {
  spot: number | null;
  callWall: number | null;
  putWall: number | null;
  zeroGammaLevel: number | null;
  loading?: boolean;
}

function pctDelta(value: number | null, spot: number | null): string | null {
  if (value == null || spot == null || spot === 0) return null;
  const pct = ((value - spot) / spot) * 100;
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

function LevelRow({ label, value, description, spot, weight }: GEXLevelRow & { spot: number | null }) {
  const pct = pctDelta(value, spot);
  const isAbove = value != null && spot != null && value > spot;
  return (
    <div className="flex items-start justify-between border-t border-[var(--color-border)] py-2 first:border-t-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--color-text-muted)] font-mono">w{weight}</span>
          <span className="text-sm font-semibold">{label}</span>
        </div>
        <div className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{description}</div>
      </div>
      <div className="text-right shrink-0 ml-3">
        <div className="msr-number text-base">{fmtNum(value, 2)}</div>
        {pct && (
          <div
            className={cn(
              'text-[10px] font-mono mt-0.5',
              isAbove
                ? 'text-[var(--color-success)]'
                : 'text-[var(--color-danger)]',
            )}
          >
            {pct}
          </div>
        )}
      </div>
    </div>
  );
}

export function GEXKeyLevelsCard({ spot, callWall, putWall, zeroGammaLevel, loading }: Props) {
  const rows: GEXLevelRow[] = [
    { label: 'Call Wall', value: callWall, description: '最大 Call OI 行权价', weight: 3 },
    { label: 'Zero Gamma', value: zeroGammaLevel, description: '净 GEX = 0 关键反转点', weight: 3 },
    { label: 'Spot', value: spot, description: '当前价格', weight: 0 },
    { label: 'Put Wall', value: putWall, description: '最大 Put OI 行权价', weight: 3 },
  ];
  if (loading) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-24 bg-[var(--color-border)] rounded animate-pulse mb-2" />
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-10 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardContent className="p-4">
        <h3 className="text-sm font-semibold mb-2">关键水平</h3>
        <div className="text-xs text-[var(--color-text-muted)] mb-2">
          {spot != null ? (
            <>
              Spot <span className="msr-number font-semibold ml-1">{fmtNum(spot, 2)}</span>
              {pctDelta(callWall, spot) && (
                <span className="ml-2">
                  · Call/Put Wall 偏移 <span className="font-mono">{fmtPct(((callWall ?? 0) - spot) / spot, 2)}</span> /{' '}
                  <span className="font-mono">{fmtPct(((putWall ?? 0) - spot) / spot, 2)}</span>
                </span>
              )}
            </>
          ) : (
            '暂无关键水平'
          )}
        </div>
        <div>
          {rows.map((r) => (
            <LevelRow key={r.label} {...r} spot={spot} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
