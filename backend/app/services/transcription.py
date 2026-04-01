from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol


@dataclass
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass
class TranscriptionResult:
    transcript_text: str
    detected_language: Optional[str]
    segments: list[TranscriptSegment]


class TranscriptionProvider(Protocol):
    name: str

    def transcribe(self, file_path: Path) -> TranscriptionResult:
        ...


class MockTranscriptionProvider:
    name = "mock"

    def transcribe(self, file_path: Path) -> TranscriptionResult:
        label = file_path.stem.replace("_", " ").replace("-", " ").strip()
        transcript_text = (
            f"Mock transcript for {file_path.name}. "
            f"This placeholder confirms the processing pipeline, SQLite persistence, search indexing, "
            f"and transcript status workflow are working for '{label or file_path.name}'."
        )
        segment = TranscriptSegment(start_seconds=0.0, end_seconds=12.0, text=transcript_text)
        return TranscriptionResult(
            transcript_text=transcript_text,
            detected_language="es",
            segments=[segment],
        )


class FasterWhisperProvider:
    name = "faster-whisper"

    def transcribe(self, file_path: Path) -> TranscriptionResult:
        raise NotImplementedError(
            "FasterWhisperProvider is a planned extension point. Wire in the faster-whisper package later."
        )


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, TranscriptionProvider] = {
            "mock": MockTranscriptionProvider(),
            "faster-whisper": FasterWhisperProvider(),
        }

    def get(self, provider_name: str) -> TranscriptionProvider:
        provider = self._providers.get(provider_name)

        if provider is None:
            raise KeyError(f"Unknown transcription provider: {provider_name}")

        return provider

    @property
    def default_provider(self) -> str:
        return "mock"
