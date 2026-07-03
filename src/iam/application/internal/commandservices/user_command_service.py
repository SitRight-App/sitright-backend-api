"""Implementación del servicio de comandos del bounded context IAM.

Agrupa todos los casos de uso de escritura en una sola clase, siguiendo la
convención `XxxCommandService` (sin sufijo `Impl`) — ver class diagram en
`docs/architecture/class-diagram.puml`.

Cada método `handle_*` toma su Command DTO y orquesta los Aggregates +
Repositorios + Services del dominio.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from ....domain.entities.notification import Notification, NotificationChannel, NotificationType
from ....domain.entities.password_reset_token import PasswordResetToken
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
from ....domain.model.commands.notify_event_command import (
    InvalidNotificationEventError,
    NotifyEventCommand,
)
from ....domain.model.commands.refresh_token_command import RefreshTokenCommand
from ....domain.model.commands.register_user_command import (
    RegisterUserCommand,
    UserAlreadyExistsError,
)
from ....domain.model.commands.request_password_reset_command import (
    RequestPasswordResetCommand,
)
from ....domain.model.commands.reset_password_command import (
    InvalidResetTokenError,
    ResetPasswordCommand,
)
from ....domain.model.commands.update_profile_command import UpdateProfileCommand
from ....domain.repositories.notification_repository import NotificationRepository
from ....domain.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from ....domain.repositories.user_repository import UserRepository
from ....domain.services.email_service import EmailService
from ....domain.services.password_service import PasswordService
from ....domain.services.token_service import TokenService
from ....domain.services.user_command_service import IUserCommandService
from ....domain.value_objects.anthropometric_data import AnthropometricData
from ....domain.value_objects.preferences import Preferences
from ....domain.value_objects.role import Role
from ....domain.value_objects.token_pair import TokenPair

logger = logging.getLogger(__name__)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# HU alertas — mapeo evento -> (tipo de notificacion, mensaje).
_NOTIFY_EVENTS: dict[str, tuple[NotificationType, str]] = {
    "bad_posture_alert": (
        NotificationType.BAD_POSTURE_ALERT,
        "Llevas varios minutos en mala postura. Endereza la espalda.",
    ),
    "break_reminder": (
        NotificationType.BREAK_REMINDER,
        "Llevas mucho tiempo sentado. Tomate una pausa activa de 1-2 min.",
    ),
}

_NOTIFY_COOLDOWN = timedelta(minutes=30)


@dataclass
class UserCommandService(IUserCommandService):
    user_repository: UserRepository
    notification_repository: NotificationRepository
    password_service: PasswordService
    token_service: TokenService
    reset_token_repository: PasswordResetTokenRepository
    email_service: EmailService
    app_base_url: str
    reset_token_ttl_seconds: int

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
        try:
            await self.email_service.send_password_changed(user.email, user.name)
        except Exception:
            logger.warning(
                "[change-password] fallo enviando el correo de aviso a user_id=%s",
                user.id,
                exc_info=True,
            )

    async def handle_request_password_reset(
        self, command: RequestPasswordResetCommand
    ) -> None:
        # Respuesta uniforme aunque el correo no exista.
        normalized = command.email.lower().strip()
        user = await self.user_repository.find_by_email(normalized)
        if user is None:
            logger.info(
                "[forgot-password] solicitud para correo no registrado: %s", normalized
            )
            return
        # Invalida enlaces previos y genera uno nuevo (crudo por correo, hash en BD).
        await self.reset_token_repository.invalidate_for_user(user.id)
        raw = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        token = PasswordResetToken(
            id=uuid4(),
            user_id=user.id,
            token_hash=_hash_token(raw),
            expires_at=now + timedelta(seconds=self.reset_token_ttl_seconds),
            created_at=now,
        )
        await self.reset_token_repository.save(token)
        link = f"{self.app_base_url}/reset-password?token={raw}"
        try:
            await self.email_service.send_password_reset(user.email, user.name, link)
        except Exception:
            logger.warning(
                "[forgot-password] fallo enviando el correo a user_id=%s",
                user.id,
                exc_info=True,
            )

    async def handle_reset_password(self, command: ResetPasswordCommand) -> None:
        # Fija la nueva contrasena si el token es valido (no usado, no vencido).
        if len(command.new_password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        token = await self.reset_token_repository.find_by_hash(
            _hash_token(command.token)
        )
        now = datetime.utcnow()
        if token is None or not token.is_valid(now):
            raise InvalidResetTokenError("El enlace no es válido o expiró")
        user = await self.user_repository.find_by_id(token.user_id)
        if user is None or not user.is_active:
            raise InvalidResetTokenError("El enlace no es válido o expiró")
        user.password_hash = self.password_service.hash(command.new_password)
        user.updated_at = now
        await self.user_repository.save(user)
        # Un solo uso: marca el usado e invalida todos los del usuario.
        await self.reset_token_repository.mark_used(token.id, now)
        await self.reset_token_repository.invalidate_for_user(user.id)

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

    async def handle_notify_event(self, command: NotifyEventCommand) -> None:
        mapped = _NOTIFY_EVENTS.get(command.event_type)
        if mapped is None:
            raise InvalidNotificationEventError(
                f"Tipo de evento de notificación desconocido: {command.event_type}"
            )
        type_, message = mapped

        user = await self.user_repository.find_by_id(command.user_id)
        if user is None:
            return

        now = datetime.utcnow()
        latest = await self.notification_repository.find_latest_by_type(user.id, type_)
        if latest is not None and (now - latest.sent_at) < _NOTIFY_COOLDOWN:
            return  # anti-spam: ya se notificó este tipo de evento hace poco.

        channel = (
            NotificationChannel.EMAIL
            if user.preferences.email_notifications
            else NotificationChannel.IN_APP
        )
        notification = Notification(
            id=uuid4(),
            user_id=user.id,
            type=type_,
            message=message,
            channel=channel,
            sent_at=now,
            is_read=False,
        )
        await self.notification_repository.save(notification)

        if user.preferences.email_notifications:
            try:
                if type_ == NotificationType.BAD_POSTURE_ALERT:
                    await self.email_service.send_posture_alert(user.email, user.name)
                else:
                    await self.email_service.send_break_reminder(user.email, user.name)
            except Exception:
                logger.warning(
                    "[notify-event] fallo enviando el correo de %s a user_id=%s",
                    command.event_type,
                    user.id,
                    exc_info=True,
                )
