// User types
export interface User {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  role: 'admin' | 'manager' | 'operator' | 'viewer';
  organization_id: string | null;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

// Auth types
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// SIP Settings types (PJSIP extension configuration)
export interface SIPSettings {
  id: string;
  organization_id: string;
  sip_server: string;
  sip_port: number;
  sip_username: string;
  sip_transport: 'UDP' | 'TCP' | 'TLS';
  registration_required: boolean;
  register_expires: number;
  keepalive_enabled: boolean;
  keepalive_interval: number;
  rtp_port_start: number;
  rtp_port_end: number;
  codecs: string[];
  default_caller_id: string | null;
  caller_id_name: string | null;
  is_active: boolean;
  connection_status: 'disconnected' | 'connecting' | 'connected' | 'registered' | 'failed';
  last_connected_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface SIPSettingsCreate {
  sip_server: string;
  sip_port: number;
  sip_username: string;
  sip_password: string;
  sip_transport: 'UDP' | 'TCP' | 'TLS';
  registration_required: boolean;
  register_expires: number;
  keepalive_enabled: boolean;
  keepalive_interval: number;
  rtp_port_start: number;
  rtp_port_end: number;
  codecs: string[];
  default_caller_id?: string;
  caller_id_name?: string;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  details?: Record<string, unknown>;
  timing_ms?: number;
  resolved_ip?: string;
  test_steps?: string[];
  server_info?: Record<string, unknown>;
  registered?: boolean;
  diagnostic_hint?: string;
}

// Campaign types
export type CampaignStatus = 'draft' | 'scheduled' | 'running' | 'paused' | 'completed' | 'cancelled';
export type DialingMode = 'progressive' | 'predictive';
export type AMDAction = 'play_ivr' | 'leave_message' | 'hangup' | 'transfer';
export type ContactStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'dnc' | 'skipped';
export type CallDisposition = 'answered_human' | 'answered_machine' | 'no_answer' | 'busy' | 'failed' | 'invalid_number' | 'dnc';

export interface Campaign {
  id: string;
  name: string;
  description: string | null;
  organization_id: string;
  status: CampaignStatus;
  contact_list_id: string;
  ivr_flow_id: string | null;
  greeting_audio_id: string | null;
  voicemail_audio_id: string | null;
  dialing_mode: DialingMode;
  max_concurrent_calls: number;
  calls_per_minute: number | null;
  max_retries: number;
  retry_delay_minutes: number;
  retry_on_no_answer: boolean;
  retry_on_busy: boolean;
  retry_on_failed: boolean;
  ring_timeout_seconds: number;
  amd_enabled: boolean;
  amd_action_human: string;
  amd_action_machine: string;
  scheduled_start: string | null;
  scheduled_end: string | null;
  calling_hours_start: string;
  calling_hours_end: string;
  respect_timezone: boolean;
  total_contacts: number;
  contacts_called: number;
  contacts_answered: number;
  contacts_completed: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  created_by_id: string | null;
}

export interface CampaignListItem {
  id: string;
  name: string;
  description: string | null;
  status: CampaignStatus;
  dialing_mode: DialingMode;
  total_contacts: number;
  contacts_called: number;
  contacts_answered: number;
  contacts_completed: number;
  scheduled_start: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignListResponse {
  items: CampaignListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface CampaignCreate {
  name: string;
  description?: string;
  contact_list_id: string;
  ivr_flow_id?: string;
  greeting_audio_id?: string;
  voicemail_audio_id?: string;
  dialing_mode?: DialingMode;
  max_concurrent_calls?: number;
  calls_per_minute?: number;
  max_retries?: number;
  retry_delay_minutes?: number;
  retry_on_no_answer?: boolean;
  retry_on_busy?: boolean;
  retry_on_failed?: boolean;
  ring_timeout_seconds?: number;
  amd_enabled?: boolean;
  amd_action_human?: AMDAction;
  amd_action_machine?: AMDAction;
  scheduled_start?: string;
  scheduled_end?: string;
  calling_hours_start?: string;
  calling_hours_end?: string;
  respect_timezone?: boolean;
}

export interface CampaignUpdate {
  name?: string;
  description?: string;
  contact_list_id?: string;
  ivr_flow_id?: string;
  greeting_audio_id?: string;
  voicemail_audio_id?: string;
  dialing_mode?: DialingMode;
  max_concurrent_calls?: number;
  calls_per_minute?: number;
  max_retries?: number;
  retry_delay_minutes?: number;
  retry_on_no_answer?: boolean;
  retry_on_busy?: boolean;
  retry_on_failed?: boolean;
  ring_timeout_seconds?: number;
  amd_enabled?: boolean;
  amd_action_human?: AMDAction;
  amd_action_machine?: AMDAction;
  scheduled_start?: string;
  scheduled_end?: string;
  calling_hours_start?: string;
  calling_hours_end?: string;
  respect_timezone?: boolean;
}

export interface CampaignContact {
  id: string;
  campaign_id: string;
  contact_id: string;
  status: ContactStatus;
  attempts: number;
  last_attempt_at: string | null;
  next_attempt_at: string | null;
  last_disposition: CallDisposition | null;
  priority: number;
  phone_number: string | null;
  first_name: string | null;
  last_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignContactsResponse {
  items: CampaignContact[];
  total: number;
  page: number;
  page_size: number;
}

export interface CampaignStats {
  campaign_id: string;
  status: CampaignStatus;
  total_contacts: number;
  contacts_pending: number;
  contacts_in_progress: number;
  contacts_completed: number;
  contacts_failed: number;
  contacts_dnc: number;
  contacts_skipped: number;
  total_calls: number;
  answered_human: number;
  answered_machine: number;
  no_answer: number;
  busy: number;
  failed: number;
  invalid_number: number;
  answer_rate: number;
  completion_rate: number;
  human_rate: number;
  average_call_duration: number | null;
  total_talk_time: number;
  started_at: string | null;
  completed_at: string | null;
  last_call_at: string | null;
}

export interface CampaignScheduleRequest {
  scheduled_start: string;
  scheduled_end?: string;
}

// Contact List types
export interface ContactList {
  id: string;
  name: string;
  description: string | null;
  organization_id: string;
  total_contacts: number;
  valid_contacts: number;
  invalid_contacts: number;
  is_active: boolean;
  original_filename: string | null;
  uploaded_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactListCreate {
  name: string;
  description?: string;
}

export interface ContactListUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export interface ContactListListResponse {
  items: ContactList[];
  total: number;
  page: number;
  page_size: number;
}

// Contact types
export interface Contact {
  id: string;
  contact_list_id: string;
  phone_number: string;
  phone_number_e164: string | null;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  custom_fields: Record<string, unknown> | null;
  is_valid: boolean;
  validation_error: string | null;
  timezone: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactListContactsResponse {
  items: Contact[];
  total: number;
  page: number;
  page_size: number;
}

// File Upload types
export interface FilePreviewResponse {
  file_id: string;
  filename: string;
  columns: string[];
  preview_rows: Record<string, unknown>[];
  row_count: number;
  suggested_mapping: ColumnMappingSuggestion;
}

export interface ColumnMappingSuggestion {
  phone_number: string | null;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  timezone: string | null;
}

export interface ColumnMapping {
  phone_number: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  timezone?: string;
  custom_fields?: Record<string, string>;
}

export interface ImportConfirmRequest {
  file_id: string;
  name: string;
  description?: string;
  column_mapping: ColumnMapping;
}

export interface ImportError {
  row: number;
  phone_number: string | null;
  error: string;
}

export interface ImportResultResponse {
  list_id: string;
  name: string;
  total_rows: number;
  valid_contacts: number;
  invalid_contacts: number;
  duplicate_contacts: number;
  dnc_contacts: number;
  errors: ImportError[];
}

// DNC types
export interface DNCEntry {
  id: string;
  phone_number: string;
  organization_id: string | null;
  source: string;
  reason: string | null;
  added_by_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DNCEntryCreate {
  phone_number: string;
  reason?: string;
}

export interface DNCListResponse {
  items: DNCEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface DNCCheckResponse {
  phone_number: string;
  is_dnc: boolean;
  entry: DNCEntry | null;
}

// IVR Flow types
export interface IVRFlow {
  id: string;
  name: string;
  description: string | null;
  organization_id: string;
  status: 'draft' | 'published' | 'archived';
  created_at: string;
  updated_at: string;
}

// Audio file types
export type AudioFormat = 'mp3' | 'wav' | 'gsm' | 'ulaw' | 'alaw';
export type AudioStatus = 'uploading' | 'processing' | 'ready' | 'failed';

export interface AudioFile {
  id: string;
  name: string;
  description: string | null;
  organization_id: string;
  original_filename: string;
  original_format: AudioFormat;
  file_size_bytes: number;
  duration_seconds: number | null;
  sample_rate: number | null;
  channels: number | null;
  status: AudioStatus;
  error_message: string | null;
  is_active: boolean;
  transcoded_paths: Record<string, string> | null;
  created_at: string;
  updated_at: string;
  uploaded_by_id: string | null;
}

export interface AudioFileListResponse {
  items: AudioFile[];
  total: number;
  page: number;
  page_size: number;
}

export interface AudioUploadResponse {
  id: string;
  name: string;
  original_filename: string;
  status: AudioStatus;
  message: string;
}

export interface AudioDownloadResponse {
  id: string;
  name: string;
  format: string;
  download_url: string;
  expires_in_seconds: number;
}
