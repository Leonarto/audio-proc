from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


TranscriptStatus = Literal["not_processed", "processing", "processed", "failed"]
JobStatus = Literal["queued", "running", "completed", "failed"]
JobType = Literal["scan", "process"]


class HealthResponse(BaseModel):
    ok: bool
    app_data_dir: str
    database_path: str


class AudioFileItem(BaseModel):
    id: int
    folder_root: str
    absolute_path: str
    relative_path: str
    filename: str
    extension: str
    file_size: int
    created_at_fs: Optional[str]
    modified_at_fs: str
    duration_seconds: Optional[float]
    processed: bool
    transcript_status: TranscriptStatus
    processing_error: Optional[str]
    transcript_text: Optional[str] = None
    detected_language: Optional[str] = None
    processed_at: Optional[str] = None


class AudioFilesResponse(BaseModel):
    current_folder_path: Optional[str]
    items: list[AudioFileItem]


class AppSettingsResponse(BaseModel):
    last_folder_path: Optional[str]
    transcription_provider: str


class UpdateSettingsRequest(BaseModel):
    last_folder_path: Optional[str] = None
    transcription_provider: Optional[str] = None


class FolderScanRequest(BaseModel):
    folder_path: str = Field(min_length=1)


class ProcessRequest(BaseModel):
    audio_file_ids: list[int] = Field(default_factory=list)
    reprocess: bool = False


class JobResponse(BaseModel):
    id: str
    job_type: JobType
    status: JobStatus
    total: int
    completed: int
    current_label: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None


class SearchResultItem(BaseModel):
    audio_file_id: int
    filename: str
    relative_path: str
    snippet_html: str
    processed_at: Optional[str] = None
    absolute_path: str


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
