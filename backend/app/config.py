from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


APP_NAME = "Audio Proc MVP"


def _default_app_data_dir() -> Path:
    explicit = os.environ.get("AUDIO_PROC_APP_DATA_DIR")

    if explicit:
        return Path(explicit).expanduser()

    home = Path.home()

    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME

    if os.name == "nt":
        appdata = os.environ.get("APPDATA")

        if appdata:
            return Path(appdata) / APP_NAME

        return home / "AppData" / "Roaming" / APP_NAME

    return home / ".local" / "share" / "audio-proc-mvp"


@dataclass(frozen=True)
class Settings:
    app_data_dir: Path
    database_path: Path
    backend_host: str = "127.0.0.1"
    backend_port: int = 8765


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    app_data_dir = _default_app_data_dir()
    app_data_dir.mkdir(parents=True, exist_ok=True)
    database_path = app_data_dir / "audio_proc.sqlite3"
    return Settings(app_data_dir=app_data_dir, database_path=database_path)
