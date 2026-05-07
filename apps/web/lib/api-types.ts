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

// === Source materials + jobs (Phase B) ===

export type SourceType = "upload" | "youtube";

export type JobType =
  | "youtube_download"
  | "probe"
  | "proxy_preview"
  | "asr"
  | "highlight"
  | "render";

export type JobStatus = "pending" | "running" | "succeeded" | "failed" | "cancelled";

export interface SourceMaterialResponse {
  id: string;
  project_id: string;
  source_type: SourceType;
  original_filename: string | null;
  youtube_url: string | null;
  storage_key: string | null;
  proxy_storage_key: string | null;
  thumbnail_storage_key: string | null;
  duration_s: number | null;
  width: number | null;
  height: number | null;
  fps: number | null;
  bytes_size: number | null;
  detected_language: string | null;
  extra_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface JobResponse {
  id: string;
  source_material_id: string;
  job_type: JobType;
  status: JobStatus;
  progress: number;
  progress_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  result: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface UploadInitRequest {
  filename: string;
  content_type?: string;
  bytes_size?: number;
}

export interface UploadInitResponse {
  source_material_id: string;
  storage_key: string;
  presigned_put_url: string;
}

export interface UploadCompleteRequest {
  source_material_id: string;
  content_hash?: string;
}

export interface YouTubeIngestRequest {
  url: string;
}

export interface JobUpdateEvent {
  event: "job_update";
  project_id: string;
  source_material_id: string;
  job_id: string;
  job_type: JobType;
  status: JobStatus;
  progress: number;
  progress_message: string | null;
  error_message: string | null;
}

// === Phase C/D ===

export interface TranscriptWord {
  text: string;
  start: number;
  end: number;
  confidence: number;
}

export interface TranscriptSegment {
  text: string;
  start: number;
  end: number;
  words: TranscriptWord[];
}

export interface TranscriptResponse {
  id: string;
  source_material_id: string;
  language: string;
  model_id: string;
  alignment_method: string;
  full_text: string;
  segments_json: TranscriptSegment[];
  avg_confidence: number | null;
  created_at: string;
}

export type HighlightStatus = "pending" | "accepted" | "rejected" | "hidden";

export interface HighlightResponse {
  id: string;
  source_material_id: string;
  start_s: number;
  end_s: number;
  audio_corrected: boolean;
  viral_score: number;
  confidence: number | null;
  typology: string | null;
  hook_sentence: string | null;
  virality_reason: string | null;
  suggested_title: string | null;
  llm_provider: string;
  feature_scores: Record<string, number>;
  status: HighlightStatus;
  created_at: string;
  updated_at: string;
}
