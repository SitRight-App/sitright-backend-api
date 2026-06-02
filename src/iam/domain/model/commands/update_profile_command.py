from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UpdateProfileCommand:
    user_id: UUID
    name: str | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    email_notifications: bool | None = None
    alert_threshold_minutes: int | None = None
    break_reminder_minutes: int | None = None
    language: str | None = None
