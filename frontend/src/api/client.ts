import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export const ACCESS_KEY = "boroughs_access_token";
export const REFRESH_KEY = "boroughs_refresh_token";

export const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

// --- Attach access token to every request ---
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_KEY);
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Auto-refresh on 401, single in-flight refresh promise ---
type RetryConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return null;
  try {
    const res = await axios.post(
      `${baseURL}/auth/refresh/`,
      { refresh },
      { headers: { "Content-Type": "application/json" } },
    );
    const newAccess: string = res.data.access;
    localStorage.setItem(ACCESS_KEY, newAccess);
    return newAccess;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as RetryConfig | undefined;
    const status = error.response?.status;

    // Don't try to refresh on the refresh endpoint itself, or if we've retried
    if (
      !original ||
      status !== 401 ||
      original._retry ||
      original.url?.includes("/auth/refresh/") ||
      original.url?.includes("/auth/login/")
    ) {
      return Promise.reject(error);
    }

    original._retry = true;

    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }

    const newAccess = await refreshPromise;
    if (!newAccess) {
      // Refresh failed — clear tokens and bubble the error
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
      return Promise.reject(error);
    }

    if (original.headers) {
      original.headers.Authorization = `Bearer ${newAccess}`;
    }
    return api(original);
  },
);
