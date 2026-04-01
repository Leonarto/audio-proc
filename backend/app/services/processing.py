from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.db.database import Database
from app.services.jobs import JobStore, utc_now
from app.services.transcription import ProviderRegistry


def _mark_processing_started(database: Database, audio_file_id: int) -> None:
    with database.connect() as connection:
        connection.execute(
            """
            UPDATE audio_files
            SET transcript_status = 'processing', processing_error = NULL, updated_at = ?
            WHERE id = ?
            """,
            (utc_now(), audio_file_id),
        )


def _mark_processing_failed(database: Database, audio_file_id: int, error: str) -> None:
    with database.connect() as connection:
        connection.execute(
            """
            UPDATE audio_files
            SET processed = 0, transcript_status = 'failed', processing_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (error, utc_now(), audio_file_id),
        )


def _store_transcription(
    database: Database,
    *,
    audio_file_id: int,
    provider_name: str,
    transcript_text: str,
    detected_language: Optional[str],
    segments: list[dict[str, object]],
) -> None:
    now = utc_now()

    with database.connect() as connection:
        connection.execute("DELETE FROM transcript_fts WHERE audio_file_id = ?", (audio_file_id,))

        existing = connection.execute(
            "SELECT id FROM transcripts WHERE audio_file_id = ?",
            (audio_file_id,),
        ).fetchone()

        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO transcripts (
                    audio_file_id,
                    provider,
                    transcript_text,
                    detected_language,
                    processed_at,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audio_file_id,
                    provider_name,
                    transcript_text,
                    detected_language,
                    now,
                    now,
                    now,
                ),
            )
            transcript_id = int(cursor.lastrowid)
        else:
            transcript_id = int(existing["id"])
            connection.execute(
                """
                UPDATE transcripts
                SET provider = ?, transcript_text = ?, detected_language = ?, processed_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    provider_name,
                    transcript_text,
                    detected_language,
                    now,
                    now,
                    transcript_id,
                ),
            )
            connection.execute("DELETE FROM transcript_segments WHERE transcript_id = ?", (transcript_id,))

        for index, segment in enumerate(segments):
            connection.execute(
                """
                INSERT INTO transcript_segments (
                    transcript_id,
                    segment_index,
                    start_seconds,
                    end_seconds,
                    text
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    transcript_id,
                    index,
                    segment.get("start_seconds"),
                    segment.get("end_seconds"),
                    segment["text"],
                ),
            )

        connection.execute(
            "INSERT INTO transcript_fts (audio_file_id, transcript_text) VALUES (?, ?)",
            (audio_file_id, transcript_text),
        )

        connection.execute(
            """
            UPDATE audio_files
            SET
                processed = 1,
                transcript_status = 'processed',
                processing_error = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (now, audio_file_id),
        )


def run_processing_job(
    job_store: JobStore,
    database: Database,
    provider_registry: ProviderRegistry,
    provider_name: str,
    job_id: str,
    audio_file_ids: list[int],
    *,
    reprocess: bool = False,
) -> None:
    with database.connect() as connection:
        placeholders = ",".join("?" for _ in audio_file_ids)
        rows = connection.execute(
            f"""
            SELECT id, absolute_path, filename, processed
            FROM audio_files
            WHERE id IN ({placeholders})
            ORDER BY filename COLLATE NOCASE
            """,
            tuple(audio_file_ids),
        ).fetchall()

    selected_items = [dict(row) for row in rows]
    work_items = [item for item in selected_items if reprocess or not bool(item["processed"])]

    if not work_items:
        job_store.finish(job_id, status="completed", message="Nothing to process. All selected files are already processed.")
        return

    job_store.update(
        job_id,
        status="running",
        total=len(work_items),
        message=f"Processing {len(work_items)} audio file(s) with '{provider_name}'.",
    )

    provider = provider_registry.get(provider_name)

    for item in work_items:
        audio_file_id = int(item["id"])
        absolute_path = Path(str(item["absolute_path"]))
        job_store.update(job_id, current_label=str(item["filename"]))
        _mark_processing_started(database, audio_file_id)

        try:
            result = provider.transcribe(absolute_path)
            _store_transcription(
                database,
                audio_file_id=audio_file_id,
                provider_name=provider_name,
                transcript_text=result.transcript_text,
                detected_language=result.detected_language,
                segments=[
                    {
                        "start_seconds": segment.start_seconds,
                        "end_seconds": segment.end_seconds,
                        "text": segment.text,
                    }
                    for segment in result.segments
                ],
            )
        except Exception as error:
            _mark_processing_failed(database, audio_file_id, str(error))

        job_store.increment(job_id)

    job_store.finish(job_id, status="completed", message="Processing finished.")
