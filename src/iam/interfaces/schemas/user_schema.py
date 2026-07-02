from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AnthropometricSchema(BaseModel):
    weight_kg: float | None = None
    height_cm: float | None = None


class PreferencesSchema(BaseModel):
    email_notifications: bool = True
    alert_threshold_minutes: int = 30
    break_reminder_minutes: int = 60
    language: str = "es"


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    anthropometric_data: AnthropometricSchema
    preferences: PreferencesSchema


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    email_notifications: bool | None = None
    alert_threshold_minutes: int | None = None
    break_reminder_minutes: int | None = None
    language: str | None = None


class NotificationResponse(BaseModel):
    id: str
    type: str
    message: str
    channel: str
    sent_at: datetime
    is_read: bool


class UnreadNotificationsResponse(BaseModel):
    count: int


class NotifyEventRequest(BaseModel):
    type: Literal["bad_posture_alert", "break_reminder"]
