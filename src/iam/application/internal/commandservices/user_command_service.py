"""Implementación del servicio de comandos del bounded context IAM.

Agrupa todos los casos de uso de escritura en una sola clase, siguiendo la
convención `XxxCommandService` (sin sufijo `Impl`) — ver class diagram en
`docs/architecture/class-diagram.puml`.

Cada método `handle_*` toma su Command DTO y orquesta los Aggregates +
Repositorios + Services del dominio.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from ....domain.entities.user import User
from ....domain.model.commands.change_password_command import (
    ChangePasswordCommand,
    InvalidCurrentPasswordError,
)
from ....domain.model.commands.deactivate_user_command import (
    CannotDeactivateAdminError,
    DeactivateUserCommand,
)
from ....domain.model.commands.login_command import (
    InactiveAccountError,
    InvalidCredentialsError,
    LoginCommand,
)
from ....domain.model.commands.mark_all_notifications_read_command import (
    MarkAllNotificationsReadCommand,
)
from ....domain.model.commands.mark_notification_read_command import (
    MarkNotificationReadCommand,
)
from ....domain.model.commands.refresh_token_command import RefreshTokenCommand
from ....domain.model.commands.register_user_command import (
    RegisterUserCommand,
    UserAlreadyExistsError,
)
from ....domain.model.commands.request_password_reset_command import (
    RequestPasswordResetCommand,
)
from ....domain.model.commands.update_profile_command import UpdateProfileCommand
from ....domain.repositories.notification_repository import NotificationRepository
from ....domain.repositories.user_repository import UserRepository
from ....domain.services.password_service import PasswordService
from ....domain.services.token_service import TokenService
from ....domain.value_objects.anthropometric_data import AnthropometricData
from ....domain.value_objects.preferences import Preferences
from ....domain.value_objects.role import Role
from ....domain.value_objects.token_pair import TokenPair

logger = logging.getLogger(__name__)


@dataclass
class UserCommandService:
    user_repository: UserRepository
    notification_repository: NotificationRepository
    password_service: PasswordService
    token_service: TokenService

    # ── Registro y autenticación ──────────────────────────────────────────

    async def handle_register(self, command: RegisterUserCommand) -> User:
        if not command.email or "@" not in command.email:
            raise ValueError("Email inválido")
        if len(command.plain_password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if await self.user_repository.exists_by_email(command.email.lower()):
            raise UserAlreadyExistsError("El email ya está registrado")

        now = datetime.utcnow()
        user = User(
            id=uuid4(),
            name=command.name.strip(),
            email=command.email.lower().strip(),
            password_hash=self.password_service.hash(command.plain_password),
            role=command.role,
            created_at=now,
            updated_at=now,
            anthropometric_data=AnthropometricData(
                weight_kg=command.weight_kg,
                height_cm=command.height_cm,
            ),
        )
        await self.user_repository.save(user)
        return user

    async def handle_login(self, command: LoginCommand) -> tuple[User, TokenPair]:
        user = await self.user_repository.find_by_email(command.email.lower().strip())
        if user is None:
            raise InvalidCredentialsError("Email o contraseña incorrectos")
        if not self.password_service.verify(command.plain_password, user.password_hash):
            raise InvalidCredentialsError("Email o contraseña incorrectos")
        if not user.is_active:
            raise InactiveAccountError("La cuenta está desactivada")
        token_pair = self.token_service.issue(user.id, user.role)
        return user, token_pair

    async def handle_refresh_token(self, command: RefreshTokenCommand) -> TokenPair:
        return self.token_service.refresh(command.refresh_token)

    # ── Perfil ────────────────────────────────────────────────────────────

    async def handle_update_profile(self, command: UpdateProfileCommand) -> User:
        user = await self.user_repository.find_by_id(command.user_id)
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
        await self.user_repository.save(user)
        return user

    # ── Contraseñas ───────────────────────────────────────────────────────

    async def handle_change_password(self, command: ChangePasswordCommand) -> None:
        user = await self.user_repository.find_by_id(command.user_id)
        if user is None:
            raise InvalidCurrentPasswordError("La contraseña actual es incorrecta")
        if not self.password_service.verify(command.current_password, user.password_hash):
            raise InvalidCurrentPasswordError("La contraseña actual es incorrecta")
        user.password_hash = self.password_service.hash(command.new_password)
        user.updated_at = datetime.utcnow()
        await self.user_repository.save(user)

    async def handle_request_password_reset(
        self, command: RequestPasswordResetCommand
    ) -> None:
        # HU-27 — respuesta uniforme aunque el correo no exista (AC2). Si la
        # cuenta existe, dejamos rastro en logs para que un consumidor de
        # email envíe el enlace con TTL 1h (AC3). Aquí no se envía correo;
        # el stub describe la intención.
        normalized = command.email.lower().strip()
        user = await self.user_repository.find_by_email(normalized)
        if user is None:
            logger.info(
                "[forgot-password] solicitud para correo no registrado: %s", normalized
            )
            return
        logger.info(
            "[forgot-password] solicitud válida para user_id=%s (TTL 1h pendiente)",
            user.id,
        )

    # ── Admin ─────────────────────────────────────────────────────────────

    async def handle_deactivate_user(self, command: DeactivateUserCommand) -> None:
        user = await self.user_repository.find_by_id(command.user_id)
        if user is None:
            raise ValueError("Usuario no encontrado")
        if user.role == Role.ADMIN:
            raise CannotDeactivateAdminError(
                "No se puede desactivar una cuenta de administrador desde esta vista"
            )
        user.deactivate()
        await self.user_repository.save(user)

    # ── Notificaciones ────────────────────────────────────────────────────

    async def handle_mark_notification_read(
        self, command: MarkNotificationReadCommand
    ) -> None:
        await self.notification_repository.mark_as_read(command.notification_id)

    async def handle_mark_all_notifications_read(
        self, command: MarkAllNotificationsReadCommand
    ) -> int:
        return await self.notification_repository.mark_all_as_read(command.user_id)
