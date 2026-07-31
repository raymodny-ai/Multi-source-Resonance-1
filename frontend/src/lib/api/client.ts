/**
 * Axios 客户端（MSR v4.0）
 * - baseURL：dev 用 Vite proxy（same-origin /api/*），prod 同样（nginx reverse-proxy），仅 standalone 用 VITE_API_BASE_URL
 * - 拦截器：所有 HTTP 错误广播 `msr-api-error` CustomEvent，供 ErrorToast 全局监听
 * - 超时：60s（collect-manual / analysis-generate 等长耗时端点）
 * - 默认 headers：Accept、Content-Type
 */
import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig } from 'axios';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const DEFAULT_TIMEOUT = 60_000;

export const apiErrorEventName = 'msr-api-error';

export const httpClient: AxiosInstance = axios.create({
  baseURL: BASE_URL || '',
  timeout: DEFAULT_TIMEOUT,
  headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
});

httpClient.interceptors.response.use(
  (resp) => resp,
  (error: AxiosError) => {
    const apiError = {
      status: error.response?.status ?? 0,
      code: error.code ?? 'NETWORK_ERROR',
      message: error.response
        ? `${error.response.status} ${error.message}`
        : error.message || '网络错误',
      url: error.config?.url ?? '',
      timestamp: new Date().toISOString(),
    };
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(apiErrorEventName, { detail: apiError }));
    }
    return Promise.reject(error);
  },
);

/** 便捷 GET，返回响应 data（已解包） */
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const resp = await httpClient.get<T>(url, config);
  return resp.data;
}

/** 便捷 POST */
export async function post<T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> {
  const resp = await httpClient.post<T>(url, body, config);
  return resp.data;
}

/** 便捷 PUT */
export async function put<T, B = unknown>(url: string, body?: B, config?: AxiosRequestConfig): Promise<T> {
  const resp = await httpClient.put<T>(url, body, config);
  return resp.data;
}

/** 便捷 DELETE */
export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const resp = await httpClient.delete<T>(url, config);
  return resp.data;
}