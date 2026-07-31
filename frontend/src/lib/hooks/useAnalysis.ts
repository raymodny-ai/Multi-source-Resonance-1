/**
 * TanStack Query hooks — Analysis (LLM-Enhanced)
 *
 * 后端实际端点（无 /api/analysis/latest / generate）：
 * - GET /api/analysis/scoring
 * - GET /api/analysis/gex
 * - GET /api/analysis/vix
 * - GET /api/analysis/crypto
 * - GET /api/analysis/darkpool
 */
import { useQuery } from '@tanstack/react-query';
import { getAnalysisLatest } from '@/lib/api/analysis';

export function useAnalysisLatest() {
  return useQuery({
    queryKey: ['analysis', 'latest'],
    queryFn: getAnalysisLatest,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  });
}
