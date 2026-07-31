/**
 * 通用格式化工具
 */

/** 数字 toFixed，兼容 null/undefined */
export function fmtNum(value: number | null | undefined, digits = 2, fallback = '—'): string {
  if (value === null || value === undefined || Number.isNaN(value)) return fallback;
  return value.toFixed(digits);
}

/** 整数格式化 */
export function fmtInt(value: number | null | undefined, fallback = '—'): string {
  if (value === null || value === undefined || Number.isNaN(value)) return fallback;
  return Math.round(value).toLocaleString('en-US');
}

/** 百分比 */
export function fmtPct(value: number | null | undefined, digits = 2, fallback = '—'): string {
  if (value === null || value === undefined || Number.isNaN(value)) return fallback;
  return `${(value * 100).toFixed(digits)}%`;
}

/** ISO 时间戳 → 本地化短串 */
export function fmtTime(iso: string | null | undefined, fallback = '—'): string {
  if (!iso) return fallback;
  try {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return fallback;
  }
}

/** ISO 时间戳 → HH:mm:ss */
export function fmtClock(iso: string | null | undefined, fallback = '—'): string {
  if (!iso) return fallback;
  try {
    return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return fallback;
  }
}

/** 相对时间（如"2 分钟前"） */
export function fmtRelative(iso: string | null | undefined, nowMs = Date.now(), fallback = '—'): string {
  if (!iso) return fallback;
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return fallback;
  const diff = (nowMs - t) / 1000;
  if (diff < 60) return `${Math.max(0, Math.floor(diff))} 秒前`;
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return `${Math.floor(diff / 86400)} 天前`;
}

/** 数据陈旧度（>5min → 'stale'，>15min → 'critical'） */
export type Staleness = 'fresh' | 'stale' | 'critical';

export function checkStaleness(iso: string | null | undefined, nowMs = Date.now()): Staleness {
  if (!iso) return 'critical';
  const age = (nowMs - new Date(iso).getTime()) / 1000;
  if (age > 900) return 'critical';
  if (age > 300) return 'stale';
  return 'fresh';
}

/** Signal Level 着色（语义色 → sparkdesign token 名） */
export function levelTone(level: number): 'info' | 'warning' | 'danger' {
  if (level >= 3) return 'danger';
  if (level >= 2) return 'warning';
  return 'info';
}

export function levelLabel(level: number): string {
  if (level >= 3) return `LEVEL ${level} 严重`;
  if (level >= 2) return `LEVEL ${level} 警告`;
  if (level >= 1) return `LEVEL ${level} 提示`;
  return '—';
}

/** Source status → 语义色 */
export type SourceStatusTone = 'success' | 'warning' | 'danger' | 'neutral';

export function sourceTone(status: string | null | undefined, isMock = false, hasError = false): SourceStatusTone {
  if (hasError) return 'danger';
  if (isMock) return 'warning';
  if (status === 'online' || status === 'ok') return 'success';
  if (status === 'degraded' || status === 'stale') return 'warning';
  if (status === 'offline' || status === 'error') return 'danger';
  return 'neutral';
}

export function sourceLabel(tone: SourceStatusTone): string {
  switch (tone) {
    case 'success': return '在线';
    case 'warning': return '降级';
    case 'danger': return '离线';
    default: return '未知';
  }
}