from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from ..value_objects.session_status import SessionStatus
from ..value_objects.session_summary import SessionSummary


@dataclass
class PostureSession:
    id: UUID
    user_id: UUID
    vest_device_id: UUID
    started_at: datetime
    status: SessionStatus = SessionStatus.ACTIVE
    ended_at: datetime | None = None
    summary: SessionSummary | None = None
    reading_count: int = 0
    note: str | None = None

    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE

    def close(self, summary: SessionSummary, ended_at: datetime | None = None) -> None:
        self.ended_at = ended_at or datetime.now(timezone.utc)
        self.summary = summary
        self.status = SessionStatus.COMPLETED

    def cancel(self) -> None:
        self.ended_at = datetime.now(timezone.utc)
        self.status = SessionStatus.CANCELLED

    def increment_reading_count(self) -> None:
        self.reading_count += 1

    def duration_minutes(self) -> float | None:
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds() / 60.0
