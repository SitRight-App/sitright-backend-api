"""Interfaz del servicio de comandos del bounded context IAM.

Sigue la convención UPC: una sola interfaz por agregado que agrupa todos los
casos de uso de escritura (registro, login, perfil, contraseñas, notifs,
admin).

Las implementaciones viven en `application/internal/commandservices/`.
"""
from typing import Protocol

from ..entities.user import User
from ..model.commands.change_password_command import ChangePasswordCommand
from ..model.commands.deactivate_user_command import DeactivateUserCommand
from ..model.commands.login_command import LoginCommand
from ..model.commands.mark_all_notifications_read_command import (
    MarkAllNotificationsReadCommand,
)
from ..model.commands.mark_notification_read_command import (
    MarkNotificationReadCommand,
)
from ..model.commands.refresh_token_command import RefreshTokenCommand
from ..model.commands.register_user_command import RegisterUserCommand
from ..model.commands.request_password_reset_command import (
    RequestPasswordResetCommand,
)
from ..model.commands.update_profile_command import UpdateProfileCommand
from ..value_objects.token_pair import TokenPair


class IUserCommandService(Protocol):
    """Casos de uso de escritura del contexto IAM."""

    async def handle_register(self, command: RegisterUserCommand) -> User: ...
    async def handle_login(self, command: LoginCommand) -> tuple[User, TokenPair]: ...
    async def handle_refresh_token(self, command: RefreshTokenCommand) -> TokenPair: ...
    async def handle_update_profile(self, command: UpdateProfileCommand) -> User: ...
    async def handle_change_password(self, command: ChangePasswordCommand) -> None: ...
    async def handle_request_password_reset(
        self, command: RequestPasswordResetCommand
    ) -> None: ...
    async def handle_deactivate_user(self, command: DeactivateUserCommand) -> None: ...
    async def handle_mark_notification_read(
        self, command: MarkNotificationReadCommand
    ) -> None: ...
    async def handle_mark_all_notifications_read(
        self, command: MarkAllNotificationsReadCommand
    ) -> int: ...
