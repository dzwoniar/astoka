// Tiny fetch wrapper with credentials: 'include' so JWT cookie roundtrips.
// All API calls go through this — no raw fetch in components.

import type {
  ApiError,
  ArchiveFilter,
  HighlightResponse,
  JobResponse,
  LoginRequest,
  ProjectCreate,
  ProjectListResponse,
  ProjectResponse,
  ProjectSortField,
  ProjectUpdate,
  SourceMaterialResponse,
  TranscriptResponse,
  UploadCompleteRequest,
  UploadInitRequest,
  UploadInitResponse,
  UserResponse,
  YouTubeIngestRequest,
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

// === Ingest (Phase B) ===

export const ingestApi = {
  listSourceMaterials: (projectId: string) =>
    apiCall<SourceMaterialResponse[]>(`/projects/${projectId}/source-materials`),

  uploadInit: (projectId: string, body: UploadInitRequest) =>
    apiCall<UploadInitResponse>(`/projects/${projectId}/uploads/init`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  uploadComplete: (projectId: string, body: UploadCompleteRequest) =>
    apiCall<SourceMaterialResponse>(`/projects/${projectId}/uploads/complete`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  youtube: (projectId: string, body: YouTubeIngestRequest) =>
    apiCall<SourceMaterialResponse>(`/projects/${projectId}/youtube`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listJobs: (projectId: string) =>
    apiCall<JobResponse[]>(`/projects/${projectId}/jobs`),
};

// === Phase C/D ===

export const transcriptsApi = {
  get: (sourceMaterialId: string) =>
    apiCall<TranscriptResponse>(
      `/source-materials/${sourceMaterialId}/transcript`,
    ),
};

export const highlightsApi = {
  list: (projectId: string, includeArchived = false) =>
    apiCall<HighlightResponse[]>(
      `/projects/${projectId}/highlights${includeArchived ? "?include_archived=true" : ""}`,
    ),

  accept: (highlightId: string) =>
    apiCall<HighlightResponse>(`/highlights/${highlightId}/accept`, {
      method: "POST",
    }),

  reject: (highlightId: string) =>
    apiCall<HighlightResponse>(`/highlights/${highlightId}/reject`, {
      method: "POST",
    }),

  hide: (highlightId: string) =>
    apiCall<HighlightResponse>(`/highlights/${highlightId}/hide`, {
      method: "POST",
    }),
};

/**
 * Upload a File directly to MinIO via presigned PUT URL, then notify backend.
 * Returns the SourceMaterial after backend kicks off probe pipeline.
 */
export async function uploadFile(
  projectId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<SourceMaterialResponse> {
  const init = await ingestApi.uploadInit(projectId, {
    filename: file.name,
    content_type: file.type || undefined,
    bytes_size: file.size,
  });

  // PUT directly to MinIO. fetch() doesn't expose progress; use XMLHttpRequest
  // for upload progress events.
  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener("progress", (ev) => {
      if (ev.lengthComputable && onProgress) {
        onProgress(ev.loaded / ev.total);
      }
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed with HTTP ${xhr.status}`));
    });
    xhr.addEventListener("error", () => reject(new Error("Upload network error")));
    xhr.open("PUT", init.presigned_put_url, true);
    if (file.type) xhr.setRequestHeader("Content-Type", file.type);
    xhr.send(file);
  });

  return ingestApi.uploadComplete(projectId, {
    source_material_id: init.source_material_id,
  });
}

export { HttpError };
