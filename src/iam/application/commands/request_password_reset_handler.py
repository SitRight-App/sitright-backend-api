import logging
from dataclasses import dataclass

from ...domain.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestPasswordResetCommand:
    email: str


@dataclass
class RequestPasswordResetHandler:
    """HU-27 — recuperación de contraseña.

    Para no exponer qué correos existen, la respuesta al usuario es idéntica
    haya o no cuenta asociada (AC2). Si la cuenta existe, registramos la
    intención para que un job posterior envíe el correo con el enlace de
    recuperación (TTL 1 h, AC3). En el demo del piloto no se envía correo
    real — el log queda como evidencia.
    """

    user_repo: UserRepository

    async def execute(self, command: RequestPasswordResetCommand) -> None:
        normalized = command.email.lower().strip()
        user = await self.user_repo.find_by_email(normalized)
        if user is None:
            logger.info("[forgot-password] solicitud para correo no registrado: %s", normalized)
            return
        # Aquí iría: generar token con expiry 1h y publicar evento "PasswordResetRequested"
        # que un consumidor de email service envía al usuario. El stub registra y termina.
        logger.info(
            "[forgot-password] solicitud válida para user_id=%s (TTL 1h pendiente de envío)",
            user.id,
        )
