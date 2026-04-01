export type TranscriptStatus = 'not_processed' | 'processing' | 'processed' | 'failed';

export interface AudioFileItem {
  id: number;
  folder_root: string;
  absolute_path: string;
  relative_path: string;
  filename: string;
  extension: string;
  file_size: number;
  created_at_fs: string | null;
  modified_at_fs: string;
  duration_seconds: number | null;
  processed: boolean;
  transcript_status: TranscriptStatus;
  processing_error: string | null;
  transcript_text: string | null;
  detected_language: string | null;
  processed_at: string | null;
}

export interface AudioFilesResponse {
  current_folder_path: string | null;
  items: AudioFileItem[];
}

export interface AppSettingsResponse {
  last_folder_path: string | null;
  transcription_provider: string;
}

export interface JobResponse {
  id: string;
  job_type: 'scan' | 'process';
  status: 'queued' | 'running' | 'completed' | 'failed';
  total: number;
  completed: number;
  current_label: string | null;
  message: string | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface SearchResultItem {
  audio_file_id: number;
  filename: string;
  relative_path: string;
  snippet_html: string;
  processed_at: string | null;
  absolute_path: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResultItem[];
}
