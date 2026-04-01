import { getBackendBaseUrl } from '$desktop/bridge';
import type {
  AppSettingsResponse,
  AudioFilesResponse,
  JobResponse,
  SearchResponse
} from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBackendBaseUrl()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function getAudioStreamUrl(audioFileId: number) {
  return `${getBackendBaseUrl()}/api/audio-files/${audioFileId}/stream`;
}

export function getSettings() {
  return request<AppSettingsResponse>('/api/settings');
}

export function updateSettings(payload: { last_folder_path?: string | null; transcription_provider?: string | null }) {
  return request<AppSettingsResponse>('/api/settings', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export function listAudioFiles() {
  return request<AudioFilesResponse>('/api/audio-files');
}

export function startScan(folderPath: string) {
  return request<JobResponse>('/api/folders/scan', {
    method: 'POST',
    body: JSON.stringify({ folder_path: folderPath })
  });
}

export function getJob(jobId: string) {
  return request<JobResponse>(`/api/jobs/${jobId}`);
}

export function processAudio(audioFileIds: number[], reprocess = false) {
  return request<JobResponse>('/api/process', {
    method: 'POST',
    body: JSON.stringify({ audio_file_ids: audioFileIds, reprocess })
  });
}

export function searchTranscripts(query: string) {
  const params = new URLSearchParams({ query });
  return request<SearchResponse>(`/api/search?${params.toString()}`);
}
