export interface ConfigField {
  value: string | null;
  is_set: boolean;
  is_secret: boolean;
  label: string;
  group: string;
  description: string;
  required: boolean;
  options?: string[];
}

export type ConfigSchema = Record<string, ConfigField>;

export type ConfigScope = "app" | "profile";

export interface ProfileEntry {
  name: string;
  active: boolean;
  read_only: boolean;
  external: boolean;
}

export interface ProfilesInfo {
  active: string | null;
  profiles: string[];
  entries?: ProfileEntry[];
}

export interface ProfileResource {
  name: string;
  dir: string;
  path: string;
  exists: boolean;
  count: number;
}

export interface ProfileResources {
  name: string;
  location: string;
  resources: ProfileResource[];
}

export interface SetupStatus {
  anthropic_key: boolean;
  credentials_file: boolean;
  google_token: boolean;
  applicant: boolean;
  dismissed: boolean;
  complete: boolean;
  auth_running: boolean;
  auth_error: string | null;
}

export interface QueueItem {
  name: string;
  path: string;
  subfolder: string;
  extension: string;
}

export interface DriveState {
  found: boolean;
  file_count: number;
  folder_id: string | null;
  web_link: string | null;
  complete: boolean;
  error: string | null;
}

// Mirrors ApplicationStatus in webapp/backend/services/application_metadata.py —
// keep in sync.
export const APP_STATUSES = [
  "GENERATED",
  "APPLIED",
  "IGNORED",
  "INTERVIEWING",
  "REJECTED",
  "OFFER",
  "ACCEPTED",
  "WITHDRAWN",
] as const;

export type AppStatus = (typeof APP_STATUSES)[number];

// Mirrors NOTE_STATUS/NOTE_FREEFORM in application_metadata.py — keep in sync.
export type NoteKind = "status" | "note";

// A changelog entry on an application: an auto-logged status transition or a
// free-text note the user added.
export interface AppNote {
  ts: string;
  kind: NoteKind;
  text: string;
}

// A persisted execution record from GET /jobs — mirrors
// services/run_history.py. Kinds keep the API vocabulary ("apply"); UI copy
// renders them as Build etc. (UI-only rename; full rename is a future change).
export interface RunRecord {
  run_id: string;
  kind: "apply" | "enrich" | "batch" | "schedule";
  label: string;
  paths: string[];
  folder_name?: string | null;
  status: "running" | "completed" | "failed";
  error?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  has_log: boolean;
}

// Compact fit block persisted in summary.json — mirrors fit_summary() in
// jobjob/structure/fit.py; keep in sync. Null axes = not computable.
export interface FitSummary {
  band?: string;
  role_fit?: number | null;
  preference_fit?: number | null;
}

// ATS assessment payload from GET /tracking/applications/{folder}/ats —
// mirrors AtsAssessment (assessment_as_dict) in jobjob/apply/recheck.py.
export interface AtsCheckResult {
  name: string;
  passed: boolean;
  reason: string;
}

export interface AtsReport {
  skipped: boolean;
  coverage_score: number | null;
  present: string[];
  missing_evidenced: string[];
  missing_unevidenced: string[];
  unmapped: string[];
  recommendations: string[];
  skills_file_candidates: string[];
  upskill_targets: string[];
  checks: AtsCheckResult[];
  fit_gaps: string[];
}

export interface CompletedItem {
  name: string;
  path: string;
  folder_name: string;
  type: "jd" | "profile";
  status: "completed" | "error";
  drive: DriveState | null;
  // Parsed from "YYYY-MM-DD - Company - Role" (applications only).
  date?: string;
  company?: string;
  title?: string;
  app_status?: AppStatus; // metadata.json > folder-name prefix > GENERATED
  status_writable?: boolean; // false when only the Drive API fallback is in use
  note_count?: number; // changelog notes recorded for the application
  // Insights from summary.json (local mirror only; absent on older applications).
  fit?: FitSummary | null;
  ats_coverage?: number | null;
  // Profiles only — parsed from "<created>-<processed>-<Company>-<Person>" (sidecar preferred).
  person?: string;
  date_created?: string;
  date_processed?: string;
}

export interface TomlFile {
  name: string;
  content: string;
  parsed: unknown;
  parse_error: string | null;
}

export interface ReferenceFile {
  path: string;
  name: string;
  extension: string;
}

export interface ScheduledJob {
  job_id: string;
  status: "running" | "completed" | "failed";
  mode: "sync" | "async";
  concurrency: number;
  interval_minutes: number;
  start_at: string;
  paths: string[];
  expected_times: Record<string, string>;
  count: number;
}

export interface JobStatus {
  job_id: string;
  status: "running" | "completed" | "failed";
  has_result: boolean;
  error: string | null;
}

export interface SSELogEvent {
  type: "log";
  level: string;
  message: string;
  ts: number;
}

export interface SSEDoneEvent {
  type: "completed" | "failed";
  result?: Record<string, unknown>;
  message?: string;
  overwrite_conflict?: boolean;
  folder_name?: string;
}

export type SSEEvent = SSELogEvent | SSEDoneEvent;
