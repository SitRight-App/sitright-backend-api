from dataclasses import dataclass
from uuid import UUID

from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.anthropometric_data import AnthropometricData
from ...domain.value_objects.preferences import Preferences


@dataclass
class UpdateProfileCommand:
    user_id: UUID
    name: str | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    email_notifications: bool | None = None
    alert_threshold_minutes: int | None = None
    break_reminder_minutes: int | None = None
    language: str | None = None


class UpdateProfileHandler:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, command: UpdateProfileCommand) -> User:
        user = await self._repo.find_by_id(command.user_id)
        if user is None:
            raise ValueError("Usuario no encontrado")

        anthro = None
        if command.weight_kg is not None or command.height_cm is not None:
            anthro = AnthropometricData(
                weight_kg=command.weight_kg or user.anthropometric_data.weight_kg,
                height_cm=command.height_cm or user.anthropometric_data.height_cm,
            )

        prefs = None
        if any(
            v is not None
            for v in (
                command.email_notifications,
                command.alert_threshold_minutes,
                command.break_reminder_minutes,
                command.language,
            )
        ):
            prefs = Preferences(
                email_notifications=(
                    command.email_notifications
                    if command.email_notifications is not None
                    else user.preferences.email_notifications
                ),
                alert_threshold_minutes=(
                    command.alert_threshold_minutes
                    if command.alert_threshold_minutes is not None
                    else user.preferences.alert_threshold_minutes
                ),
                break_reminder_minutes=(
                    command.break_reminder_minutes
                    if command.break_reminder_minutes is not None
                    else user.preferences.break_reminder_minutes
                ),
                language=command.language or user.preferences.language,
            )

        user.update_profile(name=command.name, anthropometric_data=anthro, preferences=prefs)
        await self._repo.save(user)
        return user
