from dataclasses import dataclass


@dataclass(frozen=True)
class Preferences:
    email_notifications: bool = True
    alert_threshold_minutes: int = 30
    language: str = "es"
