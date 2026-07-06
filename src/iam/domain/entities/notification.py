from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID


class NotificationType(str, Enum):
    BAD_POSTURE_ALERT = "bad_posture_alert"
    BREAK_REMINDER = "break_reminder"
    SESSION_CLOSED = "session_closed"
    WEEKLY_SUMMARY = "weekly_summary"
    CALIBRATION_NEEDED = "calibration_needed"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    IN_APP = "in_app"


@dataclass
class Notification:
    id: UUID
    user_id: UUID
    type: NotificationType
    message: str
    channel: NotificationChannel
    sent_at: datetime
    is_read: bool = False
    read_at: datetime | None = None

    def mark_as_read(self) -> None:
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.now(timezone.utc)
