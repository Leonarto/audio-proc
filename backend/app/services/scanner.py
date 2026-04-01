from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile

from app.db.database import Database
from app.services.jobs import JobStore, utc_now


SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}


@dataclass
class ScannedFile:
    folder_root: str
    absolute_path: str
    normalized_path: str
    relative_path: str
    filename: str
    extension: str
    file_size: int
    created_at_fs: Optional[str]
    modified_at_fs: str
    modified_at_fs_ns: int
    duration_seconds: Optional[float]
    fingerprint: str


def _to_iso(timestamp: Optional[float]) -> Optional[str]:
    if timestamp is None:
        return None

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _discover_audio_paths(folder_path: Path) -> list[Path]:
    matches: list[Path] = []

    for path in folder_path.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            matches.append(path)

    return sorted(matches)


def _duration_for_file(file_path: Path) -> Optional[float]:
    try:
        audio = MutagenFile(file_path)

        if audio is None or getattr(audio, "info", None) is None:
            return None

        duration = getattr(audio.info, "length", None)
        return round(float(duration), 3) if duration is not None else None
    except Exception:
        return None


def _file_metadata(folder_path: Path, file_path: Path) -> ScannedFile:
    resolved = file_path.resolve()
    stats = resolved.stat()
    absolute_path = str(resolved)
    normalized_path = os.path.normcase(absolute_path)
    relative_path = resolved.relative_to(folder_path.resolve()).as_posix()
    created_timestamp = getattr(stats, "st_birthtime", None)

    if created_timestamp is None and os.name == "nt":
        created_timestamp = stats.st_ctime

    fingerprint_input = f"{normalized_path}|{stats.st_size}|{stats.st_mtime_ns}"
    fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()

    return ScannedFile(
        folder_root=str(folder_path.resolve()),
        absolute_path=absolute_path,
        normalized_path=normalized_path,
        relative_path=relative_path,
        filename=resolved.name,
        extension=resolved.suffix.lower(),
        file_size=stats.st_size,
        created_at_fs=_to_iso(created_timestamp),
        modified_at_fs=_to_iso(stats.st_mtime) or utc_now(),
        modified_at_fs_ns=stats.st_mtime_ns,
        duration_seconds=_duration_for_file(resolved),
        fingerprint=fingerprint,
    )


def _clear_transcript_state(connection, audio_file_id: int) -> None:
    connection.execute("DELETE FROM transcript_fts WHERE audio_file_id = ?", (audio_file_id,))
    connection.execute(
        "DELETE FROM transcript_segments WHERE transcript_id IN (SELECT id FROM transcripts WHERE audio_file_id = ?)",
        (audio_file_id,),
    )
    connection.execute("DELETE FROM transcripts WHERE audio_file_id = ?", (audio_file_id,))


def _upsert_audio_file(database: Database, scanned_file: ScannedFile) -> None:
    now = utc_now()

    with database.connect() as connection:
        existing = connection.execute(
            """
            SELECT id, fingerprint
            FROM audio_files
            WHERE absolute_path = ?
            """,
            (scanned_file.absolute_path,),
        ).fetchone()

        if existing is None:
            connection.execute(
                """
                INSERT INTO audio_files (
                    folder_root,
                    absolute_path,
                    normalized_path,
                    relative_path,
                    filename,
                    extension,
                    file_size,
                    created_at_fs,
                    modified_at_fs,
                    modified_at_fs_ns,
                    duration_seconds,
                    fingerprint,
                    processed,
                    transcript_status,
                    processing_error,
                    last_seen_at,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'not_processed', NULL, ?, ?, ?)
                """,
                (
                    scanned_file.folder_root,
                    scanned_file.absolute_path,
                    scanned_file.normalized_path,
                    scanned_file.relative_path,
                    scanned_file.filename,
                    scanned_file.extension,
                    scanned_file.file_size,
                    scanned_file.created_at_fs,
                    scanned_file.modified_at_fs,
                    scanned_file.modified_at_fs_ns,
                    scanned_file.duration_seconds,
                    scanned_file.fingerprint,
                    now,
                    now,
                    now,
                ),
            )
            return

        if existing["fingerprint"] != scanned_file.fingerprint:
            _clear_transcript_state(connection, int(existing["id"]))
            connection.execute(
                """
                UPDATE audio_files
                SET
                    folder_root = ?,
                    normalized_path = ?,
                    relative_path = ?,
                    filename = ?,
                    extension = ?,
                    file_size = ?,
                    created_at_fs = ?,
                    modified_at_fs = ?,
                    modified_at_fs_ns = ?,
                    duration_seconds = ?,
                    fingerprint = ?,
                    processed = 0,
                    transcript_status = 'not_processed',
                    processing_error = NULL,
                    last_seen_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    scanned_file.folder_root,
                    scanned_file.normalized_path,
                    scanned_file.relative_path,
                    scanned_file.filename,
                    scanned_file.extension,
                    scanned_file.file_size,
                    scanned_file.created_at_fs,
                    scanned_file.modified_at_fs,
                    scanned_file.modified_at_fs_ns,
                    scanned_file.duration_seconds,
                    scanned_file.fingerprint,
                    now,
                    now,
                    int(existing["id"]),
                ),
            )
            return

        connection.execute(
            """
            UPDATE audio_files
            SET
                folder_root = ?,
                normalized_path = ?,
                relative_path = ?,
                filename = ?,
                extension = ?,
                file_size = ?,
                created_at_fs = ?,
                modified_at_fs = ?,
                modified_at_fs_ns = ?,
                duration_seconds = ?,
                last_seen_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                scanned_file.folder_root,
                scanned_file.normalized_path,
                scanned_file.relative_path,
                scanned_file.filename,
                scanned_file.extension,
                scanned_file.file_size,
                scanned_file.created_at_fs,
                scanned_file.modified_at_fs,
                scanned_file.modified_at_fs_ns,
                scanned_file.duration_seconds,
                now,
                now,
                int(existing["id"]),
            ),
        )


def _delete_missing_for_folder(database: Database, folder_root: str, seen_paths: set[str]) -> None:
    with database.connect() as connection:
        rows = connection.execute(
            "SELECT id, absolute_path FROM audio_files WHERE folder_root = ?",
            (folder_root,),
        ).fetchall()

        missing_ids = [int(row["id"]) for row in rows if row["absolute_path"] not in seen_paths]

        if not missing_ids:
            return

        placeholders = ",".join("?" for _ in missing_ids)
        connection.execute(
            f"DELETE FROM transcript_fts WHERE audio_file_id IN ({placeholders})",
            tuple(missing_ids),
        )
        connection.execute(
            f"DELETE FROM audio_files WHERE id IN ({placeholders})",
            tuple(missing_ids),
        )


def run_scan_job(job_store: JobStore, database: Database, job_id: str, folder_path: Path) -> None:
    folder_path = folder_path.expanduser().resolve()
    folder_root = str(folder_path)
    discovered_paths = _discover_audio_paths(folder_path)
    job_store.update(
        job_id,
        status="running",
        total=len(discovered_paths),
        message=f"Found {len(discovered_paths)} supported audio file(s).",
    )

    seen_paths: set[str] = set()

    for path in discovered_paths:
        job_store.update(job_id, current_label=path.name)
        metadata = _file_metadata(folder_path, path)
        _upsert_audio_file(database, metadata)
        seen_paths.add(metadata.absolute_path)
        job_store.increment(job_id)

    _delete_missing_for_folder(database, folder_root, seen_paths)

    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES ('last_folder_path', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (folder_root,),
        )

    job_store.finish(job_id, status="completed", message=f"Scan finished for {folder_root}.")
