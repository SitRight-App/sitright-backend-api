"""Seeding idempotente de cuentas demo para que la asesora/jurado puedan entrar sin registrarse.

Se ejecuta en el lifespan del FastAPI app. Si las cuentas ya existen, no hace nada.
"""
import logging

from ..domain.model.commands.register_user_command import (
    RegisterUserCommand,
    UserAlreadyExistsError,
)
from ..domain.services.user_command_service import IUserCommandService
from ..domain.value_objects.role import Role

log = logging.getLogger(__name__)


DEMO_USERS = [
    {
        "name": "Demo Trabajador",
        "email": "demo@sitright.app",
        "password": "Demo1234!",
        "role": Role.WORKER,
    },
    {
        "name": "Demo Administrador",
        "email": "admin@sitright.app",
        "password": "Admin1234!",
        "role": Role.ADMIN,
    },
]


async def seed_demo_users(service: IUserCommandService) -> None:
    """Crea las cuentas demo si no existen. Idempotente."""
    for spec in DEMO_USERS:
        try:
            await service.handle_register(
                RegisterUserCommand(
                    name=spec["name"],
                    email=spec["email"],
                    plain_password=spec["password"],
                    role=spec["role"],
                )
            )
            log.info("Cuenta demo creada: %s (%s)", spec["email"], spec["role"].value)
        except UserAlreadyExistsError:
            log.debug("Cuenta demo %s ya existía", spec["email"])
        except ValueError as exc:
            log.warning("No se pudo crear cuenta demo %s: %s", spec["email"], exc)
