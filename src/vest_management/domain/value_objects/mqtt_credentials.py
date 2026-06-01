from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MqttCredentials:
    username: str
    password_hash: str
    rotated_at: datetime
