// Hand-written API types — mirror Pydantic schemas in services/api/astoka_api/schemas/.
// In a future sprint we'll generate these from OpenAPI; for now stay in sync manually.

export interface UserResponse {
  id: string;
  username: string;
  is_admin: boolean;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface ProjectResponse {
  id: string;
  owner_id: string;
  name: string;
  client: string | null;
  is_archived: boolean;
  archived_at: string | null;
  settings: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  source_materials_count: number;
  clips_count: number;
}

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
}

export interface ProjectCreate {
  name: string;
  client?: string | null;
}

export interface ProjectUpdate {
  name?: string;
  client?: string | null;
  settings?: Record<string, unknown>;
}

export type ArchiveFilter = "all" | "active" | "archived";
export type ProjectSortField = "updated_at" | "created_at" | "name" | "client";

export interface ApiError {
  detail: string;
  status?: number;
}
