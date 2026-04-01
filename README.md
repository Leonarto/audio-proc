# Audio Proc MVP

Local-first desktop audio transcription management for macOS development and Windows desktop runtime.

## Architecture

- `SvelteKit + TypeScript` drives the UI.
- `Capacitor` configuration is included so the web layer stays Capacitor-ready.
- `Electron` is the pragmatic desktop host for this MVP because it gives reliable macOS/Windows folder picking and Python process launching today.
- `Python + FastAPI` runs locally on `127.0.0.1:8765` for folder scanning, audio metadata extraction, SQLite persistence, transcript search, and transcription orchestration.
- `SQLite` persists file metadata, transcripts, transcript segments, and app settings.
- The frontend talks to Python over JSON HTTP on `localhost`, which keeps the bridge cross-platform and easy to swap later.

## MVP Features

- Choose a local folder from the desktop shell.
- Recursively scan supported audio files: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`, `.aac`.
- Persist file metadata in SQLite.
- Browse files in a desktop-oriented table with sorting and processed filters.
- Desktop-style multi-selection:
  - Single click selects one.
  - `Cmd` click on macOS or `Ctrl` click on Windows toggles.
  - `Shift` click selects ranges.
  - Select visible and clear selection actions are included.
- Play audio directly from the app via the local backend stream endpoint.
- Process selected files through a replaceable transcription provider interface.
- Mock transcription provider included now.
- Faster-whisper provider stub included as the next extension point.
- Persist processed status, transcript text, detected language, segments, timestamps, and errors.
- Search transcript text across processed items with SQLite FTS5 and keyword fallback.

## Project Structure

```text
audio-proc/
  backend/
    app/
      api/
      db/
      services/
    requirements.txt
    run_backend.py
  electron/
    main.mjs
    preload.mjs
  scripts/
    dev-desktop.mjs
    dev-web.mjs
    python.mjs
    run-backend.mjs
  src/
    lib/
      api/
      components/
      desktop/
      stores/
      utils/
    routes/
  capacitor.config.ts
  package.json
  README.md
```

## How The Pieces Communicate

### Development

`npm run dev:desktop`

- starts the Python backend with a platform-safe Node launcher,
- starts the SvelteKit/Vite dev server,
- waits for both to become reachable,
- launches the desktop shell.

### Desktop Runtime

The desktop shell starts the Python backend on app launch and passes the backend URL into the renderer preload bridge.

### Folder Access

The desktop shell exposes:

- `chooseFolder()` for the native folder picker
- `showItemInFolder(path)` for opening the containing folder

The renderer uses those helpers, then sends the selected folder path to the Python backend for scanning.

## SQLite Schema

Schema lives in [backend/app/db/schema.sql](/Users/leonardodiazvidal/Documents/dev-projects/audio-proc/backend/app/db/schema.sql).

Tables:

- `audio_files`
- `transcripts`
- `transcript_segments`
- `app_settings`
- `transcript_fts` virtual table for transcript keyword search

## Requirements

### macOS Development

- Node.js 20+
- npm 10+
- Python 3.9+

### Windows Development / Runtime

- Node.js 20+
- npm 10+
- Python 3.9+

Important: this MVP does **not** bundle Python yet. The built desktop app expects Python to be installed on the machine. The next packaging milestone would be bundling an embedded Python runtime for Windows.

## Setup: macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt
npm install
```

Run desktop dev:

```bash
AUDIO_PROC_PYTHON=.venv/bin/python npm run dev:desktop
```

Run browser-only dev:

```bash
AUDIO_PROC_PYTHON=.venv/bin/python npm run dev:web
```

Run backend only:

```bash
AUDIO_PROC_PYTHON=.venv/bin/python npm run backend:dev
```

## Setup: Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
npm install
```

Run desktop dev:

```powershell
$env:AUDIO_PROC_PYTHON = "$PWD\.venv\Scripts\python.exe"
npm run dev:desktop
```

Run browser-only dev:

```powershell
$env:AUDIO_PROC_PYTHON = "$PWD\.venv\Scripts\python.exe"
npm run dev:web
```

## Build Commands

Build the web bundle:

```bash
npm run build:web
```

Build the desktop app:

```bash
npm run build:desktop
```

## App Data Locations

- macOS: `~/Library/Application Support/Audio Proc MVP/`
- Windows: `%APPDATA%\Audio Proc MVP\`

The SQLite file is stored as `audio_proc.sqlite3` in that app data directory.

## Current Transcription Provider Layer

Provider interface lives in [backend/app/services/transcription.py](/Users/leonardodiazvidal/Documents/dev-projects/audio-proc/backend/app/services/transcription.py).

Included now:

- `MockTranscriptionProvider`
- `FasterWhisperProvider` stub

This keeps the MVP ready for:

- faster-whisper local transcription
- paid backend integrations
- LATAM Spanish tuning
- segment browsing improvements

## Notes For The Next Iteration

- Replace the mock provider with faster-whisper and real segment output.
- Add a settings screen for provider configuration.
- Bundle Python for a smoother Windows install story.
- Add richer search ranking and segment-level navigation.
