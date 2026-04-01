from __future__ import annotations

import mimetypes
from pathlib import Path
from threading import Thread
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.api.schemas import (
    AppSettingsResponse,
    AudioFileItem,
    AudioFilesResponse,
    FolderScanRequest,
    HealthResponse,
    JobResponse,
    ProcessRequest,
    SearchResponse,
    UpdateSettingsRequest,
)
from app.services.processing import run_processing_job
from app.services.scanner import run_scan_job
from app.services.search import search_transcripts


router = APIRouter(prefix="/api")


def _get_setting(connection, key: str) -> Optional[str]:
    row = connection.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (key,),
    ).fetchone()
    return None if row is None else str(row["value"])


@router.get("/health", response_model=HealthResponse)
def healthcheck(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(
        ok=True,
        app_data_dir=str(settings.app_data_dir),
        database_path=str(settings.database_path),
    )


@router.get("/settings", response_model=AppSettingsResponse)
def get_settings(request: Request) -> AppSettingsResponse:
    database = request.app.state.database

    with database.connect() as connection:
        last_folder_path = _get_setting(connection, "last_folder_path")
        transcription_provider = _get_setting(connection, "transcription_provider") or "mock"

    return AppSettingsResponse(
        last_folder_path=last_folder_path,
        transcription_provider=transcription_provider,
    )


@router.post("/settings", response_model=AppSettingsResponse)
def update_settings(payload: UpdateSettingsRequest, request: Request) -> AppSettingsResponse:
    database = request.app.state.database

    with database.connect() as connection:
        if payload.last_folder_path is not None:
            connection.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES ('last_folder_path', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (payload.last_folder_path,),
            )

        if payload.transcription_provider is not None:
            connection.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES ('transcription_provider', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (payload.transcription_provider,),
            )

    return get_settings(request)


@router.get("/audio-files", response_model=AudioFilesResponse)
def list_audio_files(request: Request) -> AudioFilesResponse:
    database = request.app.state.database

    with database.connect() as connection:
        current_folder_path = _get_setting(connection, "last_folder_path")

        if current_folder_path is None:
            return AudioFilesResponse(current_folder_path=None, items=[])

        rows = connection.execute(
            """
            SELECT
                af.id,
                af.folder_root,
                af.absolute_path,
                af.relative_path,
                af.filename,
                af.extension,
                af.file_size,
                af.created_at_fs,
                af.modified_at_fs,
                af.duration_seconds,
                af.processed,
                af.transcript_status,
                af.processing_error,
                t.transcript_text,
                t.detected_language,
                t.processed_at
            FROM audio_files af
            LEFT JOIN transcripts t ON t.audio_file_id = af.id
            WHERE af.folder_root = ?
            ORDER BY af.filename COLLATE NOCASE, af.relative_path COLLATE NOCASE
            """,
            (current_folder_path,),
        ).fetchall()

    items = [
        AudioFileItem(
            id=int(row["id"]),
            folder_root=str(row["folder_root"]),
            absolute_path=str(row["absolute_path"]),
            relative_path=str(row["relative_path"]),
            filename=str(row["filename"]),
            extension=str(row["extension"]),
            file_size=int(row["file_size"]),
            created_at_fs=row["created_at_fs"],
            modified_at_fs=str(row["modified_at_fs"]),
            duration_seconds=float(row["duration_seconds"]) if row["duration_seconds"] is not None else None,
            processed=bool(row["processed"]),
            transcript_status=str(row["transcript_status"]),
            processing_error=row["processing_error"],
            transcript_text=row["transcript_text"],
            detected_language=row["detected_language"],
            processed_at=row["processed_at"],
        )
        for row in rows
    ]

    return AudioFilesResponse(current_folder_path=current_folder_path, items=items)


@router.post("/folders/scan", response_model=JobResponse)
def scan_folder(payload: FolderScanRequest, request: Request) -> JobResponse:
    folder_path = Path(payload.folder_path).expanduser()

    if not folder_path.exists() or not folder_path.is_dir():
        raise HTTPException(status_code=400, detail="Folder path must exist and point to a directory.")

    jobs = request.app.state.jobs
    database = request.app.state.database

    job = jobs.create("scan", message=f"Scanning {folder_path}.")
    thread = Thread(
        target=run_scan_job,
        args=(jobs, database, job.id, folder_path),
        daemon=True,
    )
    thread.start()

    return JobResponse(**jobs.get(job.id))


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, request: Request) -> JobResponse:
    jobs = request.app.state.jobs

    try:
        return JobResponse(**jobs.get(job_id))
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Job not found.") from error


@router.post("/process", response_model=JobResponse)
def process_audio(payload: ProcessRequest, request: Request) -> JobResponse:
    if not payload.audio_file_ids:
        raise HTTPException(status_code=400, detail="Select at least one audio file.")

    database = request.app.state.database
    jobs = request.app.state.jobs

    with database.connect() as connection:
        provider_name = _get_setting(connection, "transcription_provider") or request.app.state.providers.default_provider

    job = jobs.create("process", total=len(payload.audio_file_ids), message="Queueing audio processing.")
    thread = Thread(
        target=run_processing_job,
        args=(
            jobs,
            database,
            request.app.state.providers,
            provider_name,
            job.id,
            payload.audio_file_ids,
        ),
        kwargs={"reprocess": payload.reprocess},
        daemon=True,
    )
    thread.start()

    return JobResponse(**jobs.get(job.id))


@router.get("/search", response_model=SearchResponse)
def search(query: str, request: Request) -> SearchResponse:
    database = request.app.state.database
    results = search_transcripts(database, query)
    return SearchResponse(query=query, results=results)


@router.get("/audio-files/{audio_file_id}/stream")
def stream_audio(audio_file_id: int, request: Request) -> FileResponse:
    database = request.app.state.database

    with database.connect() as connection:
        row = connection.execute(
            "SELECT absolute_path FROM audio_files WHERE id = ?",
            (audio_file_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Audio file not found.")

    absolute_path = Path(str(row["absolute_path"]))

    if not absolute_path.exists():
        raise HTTPException(status_code=404, detail="Audio file no longer exists on disk.")

    media_type, _ = mimetypes.guess_type(absolute_path.name)
    return FileResponse(absolute_path, media_type=media_type or "application/octet-stream")
