/**
 * TanStack Query hooks — Configuration / Settings
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getConfig,
  getConfigAuditLog,
  getConfigDefaults,
  getSourcesConfig,
  getWeights,
  resetWeights,
  restoreConfigDefaults,
  updateConfigKV,
  updateSourceConfig,
} from '@/lib/api/config';

export function useConfigList() {
  return useQuery({
    queryKey: ['config', 'list'],
    queryFn: getConfig,
    staleTime: 15_000,
    retry: 1,
  });
}

export function useConfigDefaults() {
  return useQuery({
    queryKey: ['config', 'defaults'],
    queryFn: getConfigDefaults,
    staleTime: 60_000,
    retry: 1,
  });
}

export function useSourcesConfig() {
  return useQuery({
    queryKey: ['config', 'sources'],
    queryFn: getSourcesConfig,
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 1,
  });
}

export function useWeights() {
  return useQuery({
    queryKey: ['config', 'weights'],
    queryFn: getWeights,
    staleTime: 15_000,
    refetchInterval: 60_000,
    retry: 1,
  });
}

export function useConfigAuditLog() {
  return useQuery({
    queryKey: ['config', 'audit'],
    queryFn: getConfigAuditLog,
    staleTime: 30_000,
    retry: 1,
  });
}

export function useUpdateConfigKV() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { key: string; value: string; description?: string }) =>
      updateConfigKV(input.key, input.value, input.description),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function useUpdateSourceConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; enabled?: boolean; api_key?: string }) =>
      updateSourceConfig(input.name, { enabled: input.enabled, api_key: input.api_key }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config', 'sources'] });
    },
  });
}

export function useRestoreDefaults() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => restoreConfigDefaults(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

export function useResetWeights() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => resetWeights(),
    onSuccess: () => {
      // Invalidate both the legacy config route and the new observability
      // endpoint so reset reflects everywhere (IMPL-BAYESIAN-001 #4).
      qc.invalidateQueries({ queryKey: ['config', 'weights'] });
      qc.invalidateQueries({ queryKey: ['signals', 'bayesian-weights'] });
    },
  });
}