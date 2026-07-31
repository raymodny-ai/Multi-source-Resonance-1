/**
 * Signal 字段归一化工具
 * 后端 signal_alerts 表字段：
 * - id / trigger_time (ISO) / total_score / gex/vix/crypto/darkpool_score
 * - alert_level: 'NONE' | 'LEVEL_1' | 'LEVEL_2' | 'LEVEL_3' (string)
 * - hawkes_branching_ratio / acknowledged / acknowledged_at / acknowledged_by
 * - outcome (SignalOutcome, 可以为 null)
 * - details (JSON)
 *
 * 同时保留旧字段 `timestamp` 与 `resonance_score` 的兼容回退。
 */
import type { Signal } from '@/lib/api/types';

export function scoreOf(s: Signal | null | undefined): number {
  if (!s) return 0;
  const v = s.total_score ?? s.resonance_score ?? null;
  return typeof v === 'number' && Number.isFinite(v) ? v : 0;
}

export function tsOf(s: Signal | null | undefined): string {
  if (!s) return '';
  return s.trigger_time ?? s.timestamp ?? '';
}

/** 把字符串/数字的 alert_level 归一化到 0..3 数字 */
export function levelOf(s: Signal | null | undefined): number {
  if (!s) return 0;
  const lvl = s.alert_level;
  if (lvl == null) return 0;
  if (typeof lvl === 'number') return lvl;
  const s2 = String(lvl).toUpperCase();
  if (s2 === 'LEVEL_1' || s2 === '1') return 1;
  if (s2 === 'LEVEL_2' || s2 === '2') return 2;
  if (s2 === 'LEVEL_3' || s2 === '3') return 3;
  if (s2 === 'NONE' || s2 === '0' || s2 === '') return 0;
  return 0;
}

/** Signal level → text label */
export function levelLabel(level: number): string {
  if (level >= 3) return 'LEVEL 3 严重';
  if (level >= 2) return 'LEVEL 2 警告';
  if (level >= 1) return 'LEVEL 1 提示';
  return 'NONE';
}

/** 4 维度 score 提取 */
export function dimScore(s: Signal | null | undefined, key: 'gex' | 'vix' | 'crypto' | 'darkpool'): number {
  if (!s) return 0;
  const v =
    key === 'gex'
      ? s.gex_score
      : key === 'vix'
        ? s.vix_score
        : key === 'crypto'
          ? s.crypto_score
          : s.darkpool_score;
  return typeof v === 'number' && Number.isFinite(v) ? v : 0;
}

/** 与 levelTone 一致的语义色 */
export function levelTone(level: number): 'info' | 'warning' | 'danger' {
  if (level >= 3) return 'danger';
  if (level >= 2) return 'warning';
  if (level >= 1) return 'info';
  return 'info';
}
