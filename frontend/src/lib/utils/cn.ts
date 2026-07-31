/**
 * 通用工具：cn —— 合并 className（clsx + tailwind-merge 解决冲突）
 */
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}