from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from ..value_objects.anthropometric_data import AnthropometricData
from ..value_objects.preferences import Preferences
from ..value_objects.role import Role


@dataclass
class User:
    id: UUID
    name: str
    email: str
    password_hash: str
    role: Role
    created_at: datetime
    updated_at: datetime
    anthropometric_data: AnthropometricData = field(default_factory=AnthropometricData)
    preferences: Preferences = field(default_factory=Preferences)
    is_active: bool = True

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)

    def update_profile(
        self,
        name: str | None = None,
        anthropometric_data: AnthropometricData | None = None,
        preferences: Preferences | None = None,
    ) -> None:
        if name is not None:
            self.name = name
        if anthropometric_data is not None:
            self.anthropometric_data = anthropometric_data
        if preferences is not None:
            self.preferences = preferences
        self.updated_at = datetime.now(timezone.utc)
