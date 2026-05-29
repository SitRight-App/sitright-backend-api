"""Seeding idempotente de cuentas demo para que la asesora/jurado puedan entrar sin registrarse.

Se ejecuta en el lifespan del FastAPI app. Si las cuentas ya existen, no hace nada.
"""
import logging

from .commands.register_user_handler import RegisterUserCommand, RegisterUserHandler
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


async def seed_demo_users(register_handler: RegisterUserHandler) -> None:
    """Crea las cuentas demo si no existen. Idempotente."""
    for spec in DEMO_USERS:
        try:
            await register_handler.execute(
                RegisterUserCommand(
                    name=spec["name"],
                    email=spec["email"],
                    plain_password=spec["password"],
                    role=spec["role"],
                )
            )
            log.info("Cuenta demo creada: %s (%s)", spec["email"], spec["role"].value)
        except ValueError as exc:
            if "ya está registrado" in str(exc):
                log.debug("Cuenta demo %s ya existía", spec["email"])
            else:
                log.warning("No se pudo crear cuenta demo %s: %s", spec["email"], exc)
