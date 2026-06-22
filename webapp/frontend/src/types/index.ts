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
