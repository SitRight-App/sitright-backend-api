from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...domain.repositories.user_repository import UserRepository
from ...domain.services.password_service import PasswordService


class InvalidCurrentPasswordError(Exception):
    pass


@dataclass(frozen=True)
class ChangePasswordCommand:
    user_id: UUID
    current_password: str
    new_password: str


@dataclass
class ChangePasswordHandler:
    """HU-28 — cambio de contraseña desde el perfil.

    Verifica la contraseña actual antes de actualizar (AC2). La política de
    longitud mínima (≥8) la hace cumplir el schema. El "envío de correo
    notificando el cambio" del AC1 queda como hook para un email service
    futuro: este handler solo persiste el cambio.
    """

    user_repo: UserRepository
    password_service: PasswordService

    async def execute(self, command: ChangePasswordCommand) -> None:
        user = await self.user_repo.find_by_id(command.user_id)
        if user is None:
            raise InvalidCurrentPasswordError("La contraseña actual es incorrecta")
        if not self.password_service.verify(command.current_password, user.password_hash):
            raise InvalidCurrentPasswordError("La contraseña actual es incorrecta")
        user.password_hash = self.password_service.hash(command.new_password)
        user.updated_at = datetime.utcnow()
        await self.user_repo.save(user)
