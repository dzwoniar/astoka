// Tiny fetch wrapper with credentials: 'include' so JWT cookie roundtrips.
// All API calls go through this — no raw fetch in components.

import type {
  ApiError,
  ArchiveFilter,
  LoginRequest,
  ProjectCreate,
  ProjectListResponse,
  ProjectResponse,
  ProjectSortField,
  ProjectUpdate,
  UserResponse,
} from "./api-types";

// In dev, Next.js rewrites /api/* → http://api:8000/* (see next.config.mjs).
// In prod via Traefik, /api/* is also routed.
const API_PREFIX = "/api";

class HttpError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`HTTP ${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

async function apiCall<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as ApiError;
      detail = body.detail ?? detail;
    } catch {
      // Body wasn't JSON — keep statusText.
    }
    throw new HttpError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

// === Auth ===

export const authApi = {
  login: (body: LoginRequest) =>
    apiCall<UserResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  logout: () =>
    apiCall<void>("/auth/logout", { method: "POST" }),

  me: () => apiCall<UserResponse>("/auth/me"),
};

// === Projects ===

export interface ListProjectsParams {
  sort_by?: ProjectSortField;
  sort_desc?: boolean;
  archive_filter?: ArchiveFilter;
  [key: string]: string | number | boolean | undefined;
}

function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined);
  if (entries.length === 0) return "";
  const search = new URLSearchParams();
  for (const [k, v] of entries) search.append(k, String(v));
  return `?${search.toString()}`;
}

export const projectsApi = {
  list: (params: ListProjectsParams = {}) =>
    apiCall<ProjectListResponse>(`/projects${qs(params)}`),

  create: (body: ProjectCreate) =>
    apiCall<ProjectResponse>("/projects", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  get: (id: string) => apiCall<ProjectResponse>(`/projects/${id}`),

  update: (id: string, body: ProjectUpdate) =>
    apiCall<ProjectResponse>(`/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  archive: (id: string) =>
    apiCall<ProjectResponse>(`/projects/${id}`, { method: "DELETE" }),

  restore: (id: string) =>
    apiCall<ProjectResponse>(`/projects/${id}/restore`, { method: "POST" }),

  hardDelete: (id: string) =>
    apiCall<void>(`/projects/${id}/hard`, { method: "DELETE" }),
};

export { HttpError };
