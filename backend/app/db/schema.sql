PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS audio_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_root TEXT NOT NULL,
    absolute_path TEXT NOT NULL UNIQUE,
    normalized_path TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    created_at_fs TEXT,
    modified_at_fs TEXT NOT NULL,
    modified_at_fs_ns INTEGER NOT NULL,
    duration_seconds REAL,
    fingerprint TEXT NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0,
    transcript_status TEXT NOT NULL DEFAULT 'not_processed',
    processing_error TEXT,
    last_seen_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audio_files_folder_root ON audio_files(folder_root);
CREATE INDEX IF NOT EXISTS idx_audio_files_processed ON audio_files(processed);
CREATE INDEX IF NOT EXISTS idx_audio_files_status ON audio_files(transcript_status);
CREATE INDEX IF NOT EXISTS idx_audio_files_modified ON audio_files(modified_at_fs);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audio_file_id INTEGER NOT NULL UNIQUE REFERENCES audio_files(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    transcript_text TEXT NOT NULL,
    detected_language TEXT,
    processed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcript_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcript_id INTEGER NOT NULL REFERENCES transcripts(id) ON DELETE CASCADE,
    segment_index INTEGER NOT NULL,
    start_seconds REAL,
    end_seconds REAL,
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transcript_segments_transcript_id
    ON transcript_segments(transcript_id, segment_index);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS transcript_fts USING fts5(
    audio_file_id UNINDEXED,
    transcript_text
);
