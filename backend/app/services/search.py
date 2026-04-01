from __future__ import annotations

import sqlite3

from app.db.database import Database


def _fts_query_from_keywords(query: str) -> str:
    parts = [part.strip().replace('"', "") for part in query.split() if part.strip()]
    return " ".join(f'"{part}"*' for part in parts)


def search_transcripts(database: Database, query: str) -> list[dict[str, object]]:
    cleaned = query.strip()

    if not cleaned:
        return []

    with database.connect() as connection:
        try:
            fts_query = _fts_query_from_keywords(cleaned)
            if not fts_query:
                return []

            rows = connection.execute(
                """
                SELECT
                    af.id AS audio_file_id,
                    af.filename,
                    af.relative_path,
                    af.absolute_path,
                    t.processed_at,
                    snippet(transcript_fts, 1, '<mark>', '</mark>', ' ... ', 18) AS snippet_html
                FROM transcript_fts
                INNER JOIN audio_files af ON af.id = transcript_fts.audio_file_id
                INNER JOIN transcripts t ON t.audio_file_id = af.id
                WHERE transcript_fts MATCH ?
                ORDER BY bm25(transcript_fts), t.processed_at DESC
                LIMIT 50
                """,
                (fts_query,),
            ).fetchall()
        except sqlite3.OperationalError:
            like_query = f"%{cleaned.lower()}%"
            rows = connection.execute(
                """
                SELECT
                    af.id AS audio_file_id,
                    af.filename,
                    af.relative_path,
                    af.absolute_path,
                    t.processed_at,
                    substr(t.transcript_text, 1, 240) AS snippet_html
                FROM transcripts t
                INNER JOIN audio_files af ON af.id = t.audio_file_id
                WHERE lower(t.transcript_text) LIKE ?
                ORDER BY t.processed_at DESC
                LIMIT 50
                """,
                (like_query,),
            ).fetchall()

    return [dict(row) for row in rows]
