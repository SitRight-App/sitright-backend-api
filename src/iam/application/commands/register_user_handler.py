from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository
from ...domain.services.password_service import PasswordService
from ...domain.value_objects.anthropometric_data import AnthropometricData
from ...domain.value_objects.role import Role


@dataclass
class RegisterUserCommand:
    name: str
    email: str
    plain_password: str
    role: Role = Role.WORKER
    weight_kg: float | None = None
    height_cm: float | None = None


class RegisterUserHandler:
    def __init__(self, repo: UserRepository, password_service: PasswordService) -> None:
        self._repo = repo
        self._password_service = password_service

    async def execute(self, command: RegisterUserCommand) -> User:
        if not command.email or "@" not in command.email:
            raise ValueError("Email inválido")
        if len(command.plain_password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")

        if await self._repo.exists_by_email(command.email.lower()):
            raise ValueError("El email ya está registrado")

        now = datetime.utcnow()
        user = User(
            id=uuid4(),
            name=command.name.strip(),
            email=command.email.lower().strip(),
            password_hash=self._password_service.hash(command.plain_password),
            role=command.role,
            created_at=now,
            updated_at=now,
            anthropometric_data=AnthropometricData(
                weight_kg=command.weight_kg,
                height_cm=command.height_cm,
            ),
        )
        await self._repo.save(user)
        return user
