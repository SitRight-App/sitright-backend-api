from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.user_repository import UserRepository
from ...domain.value_objects.role import Role


class CannotDeactivateAdminError(Exception):
    """HU-30 AC2 — no se permite desactivar otra cuenta admin desde el panel."""


@dataclass(frozen=True)
class DeactivateUserCommand:
    user_id: UUID


@dataclass
class DeactivateUserHandler:
    user_repo: UserRepository

    async def execute(self, command: DeactivateUserCommand) -> None:
        user = await self.user_repo.find_by_id(command.user_id)
        if user is None:
            raise ValueError("Usuario no encontrado")
        if user.role == Role.ADMIN:
            raise CannotDeactivateAdminError(
                "No se puede desactivar una cuenta de administrador desde esta vista"
            )
        user.deactivate()
        await self.user_repo.save(user)
