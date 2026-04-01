from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRecord:
    id: str
    job_type: str
    status: str
    total: int
    completed: int
    current_label: Optional[str]
    message: Optional[str]
    error: Optional[str]
    started_at: str
    finished_at: Optional[str]


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, job_type: str, *, total: int = 0, message: Optional[str] = None) -> JobRecord:
        record = JobRecord(
            id=str(uuid4()),
            job_type=job_type,
            status="queued",
            total=total,
            completed=0,
            current_label=None,
            message=message,
            error=None,
            started_at=utc_now(),
            finished_at=None,
        )

        with self._lock:
            self._jobs[record.id] = record

        return record

    def update(self, job_id: str, **changes: object) -> JobRecord:
        with self._lock:
            record = self._jobs[job_id]

            for key, value in changes.items():
                setattr(record, key, value)

            self._jobs[job_id] = record
            return record

    def increment(self, job_id: str, amount: int = 1) -> JobRecord:
        with self._lock:
            record = self._jobs[job_id]
            record.completed += amount
            self._jobs[job_id] = record
            return record

    def finish(
        self,
        job_id: str,
        *,
        status: str,
        message: Optional[str] = None,
        error: Optional[str] = None,
    ) -> JobRecord:
        return self.update(
            job_id,
            status=status,
            message=message,
            error=error,
            finished_at=utc_now(),
        )

    def get(self, job_id: str) -> dict[str, object]:
        with self._lock:
            record = self._jobs[job_id]
            return asdict(record)
