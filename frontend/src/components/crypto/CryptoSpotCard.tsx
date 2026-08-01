/**
 * CoinGecko 市场现货价格卡片 (MSR-1 Crypto 页)
 * 补充显示 BTC / ETH 现货价、24h 涨跌、BTC 24h 成交额。
 * 数据来自 backend `/api/crypto/latest` 里 crypto_fetcher 合并的 CoinGecko 字段。
 */
import { Card, CardContent } from 'sparkdesign';
import { cn } from '@/lib/utils/cn';
import type { CryptoLatest } from '@/lib/api/crypto';

interface Props {
  latest: CryptoLatest | null;
  loading?: boolean;
}

function changeTone(v: number | null | undefined) {
  if (v == null) return { text: 'text-[var(--color-text-muted)]', label: '—' };
  if (v > 0.5) return { text: 'text-[var(--color-success)]', label: '↑' };
  if (v < -0.5) return { text: 'text-[var(--color-danger)]', label: '↓' };
  return { text: 'text-[var(--color-text-muted)]', label: '→' };
}

export function CryptoSpotCard({ latest, loading }: Props) {
  if (loading || !latest) {
    return (
      <Card>
        <CardContent className="p-4">
          <div className="h-4 w-32 bg-[var(--color-border)] rounded animate-pulse mb-2" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-16 w-full bg-[var(--color-bg-elevated)] rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const btc = latest.btc_price ?? null;
  const btcChg = latest.btc_24h_change ?? null;
  const btcVol = latest.btc_volume ?? null;
  const eth = latest.eth_price ?? null;
  const ethChg = latest.eth_24h_change ?? null;

  const fmtPrice = (v: number | null) =>
    v == null ? '—' : `$${v.toLocaleString('en-US', { maximumFractionDigits: v < 100 ? 2 : 0 })}`;
  const fmtVol = (v: number | null) =>
    v == null ? '—' : `$${(v / 1e9).toFixed(2)}B`;

  const btcTone = changeTone(btcChg);
  const ethTone = changeTone(ethChg);

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold">市场现货 · CoinGecko</h3>
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[var(--color-success)]/10 text-[var(--color-success)]">
            Live Spot
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* BTC price */}
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">BTC 现货价</div>
            <div className="msr-number text-lg mt-1">{fmtPrice(btc)}</div>
          </div>
          {/* BTC 24h */}
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">BTC 24h</div>
            <div className={cn('msr-number text-lg mt-1', btcTone.text)}>
              {btcChg == null ? '—' : `${btcTone.label} ${btcChg > 0 ? '+' : ''}${btcChg.toFixed(2)}%`}
            </div>
          </div>
          {/* ETH price */}
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">ETH 现货价</div>
            <div className="msr-number text-lg mt-1">{fmtPrice(eth)}</div>
          </div>
          {/* BTC 24h volume */}
          <div className="rounded-md bg-[var(--color-bg-elevated)] px-3 py-2">
            <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">ETH 24h</div>
            <div className={cn('msr-number text-lg mt-1', ethTone.text)}>
              {ethChg == null ? '—' : `${ethTone.label} ${ethChg > 0 ? '+' : ''}${ethChg.toFixed(2)}%`}
            </div>
            <div className="text-[10px] text-[var(--color-text-muted)] mt-1 font-mono">BTC 24h vol {fmtVol(btcVol)}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
