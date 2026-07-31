/**
 * 信号确认对话框
 * - Spark Design AlertDialog
 * - 显示信号摘要，确认后回调 onConfirm
 */
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from 'sparkdesign';
import type { Signal } from '@/lib/api/types';
import { fmtClock, fmtNum } from '@/lib/utils/format';
import { levelLabel, levelOf, levelTone } from '@/lib/utils/signal';
import { cn } from '@/lib/utils/cn';

interface AcknowledgeDialogProps {
  signal: Signal | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (signal: Signal) => void;
  confirming?: boolean;
}

export function AcknowledgeDialog({
  signal,
  open,
  onOpenChange,
  onConfirm,
  confirming = false,
}: AcknowledgeDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent size="sm">
        <AlertDialogHeader>
          <AlertDialogTitle>确认信号 #{signal?.id ?? ''} ?</AlertDialogTitle>
          <AlertDialogDescription>
            确认后将记录到审计日志，后续无法撤销。
          </AlertDialogDescription>
        </AlertDialogHeader>
        {signal && (
          <div className="px-6 py-2 space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--color-text-muted)]">时间</span>
              <span className="font-mono">{fmtClock(signal.trigger_time ?? signal.timestamp)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-muted)]">综合分</span>
              <span className="font-mono font-semibold">
                {fmtNum(signal.total_score ?? signal.resonance_score, 2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-muted)]">等级</span>
              <span
                className={cn(
                  'font-bold text-xs uppercase tracking-wider',
                  levelTone(levelOf(signal)) === 'danger' && 'text-[var(--color-danger)]',
                  levelTone(levelOf(signal)) === 'warning' && 'text-[var(--color-warning)]',
                  levelTone(levelOf(signal)) === 'info' && 'text-[var(--color-info)]',
                )}
              >
                {levelLabel(levelOf(signal))}
              </span>
            </div>
          </div>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={confirming}>取消</AlertDialogCancel>
          <AlertDialogAction
            onClick={(e: React.MouseEvent) => {
              e.preventDefault();
              if (signal) onConfirm(signal);
            }}
            disabled={confirming || !signal}
          >
            {confirming ? '确认中…' : '确认'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
