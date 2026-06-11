"""Adapters cross-context que viven en la composition root.

Su único propósito es satisfacer Protocols del subscriber MQTT (`VestLookupPort`,
`SessionStarterPort`) sin hacer que un bounded context dependa directamente
de otro.
"""
from uuid import UUID

from ..session_history.domain.model.commands.start_session_command import (
    StartSessionCommand,
)
from ..session_history.domain.model.queries.get_session_query import (
    GetActiveSessionQuery,
)
from ..session_history.domain.services.session_command_service import (
    ISessionCommandService,
)
from ..session_history.domain.services.session_query_service import (
    ISessionQueryService,
)
from ..vest_management.domain.repositories.vest_device_repository import (
    VestDeviceRepository,
)


class VestLookupAdapter:
    def __init__(self, vest_repo: VestDeviceRepository) -> None:
        self._repo = vest_repo

    async def resolve(self, mac_address: str) -> tuple[UUID, UUID] | None:
        device = await self._repo.find_by_mac_address(mac_address)
        if device is None or not device.is_linked():
            return None
        return (device.user_id, device.id)


class SessionStarterAdapter:
    def __init__(self, session_command_service: ISessionCommandService) -> None:
        self._service = session_command_service

    async def ensure_active(self, user_id: UUID, vest_device_id: UUID) -> UUID:
        session = await self._service.handle_start_session(
            StartSessionCommand(user_id=user_id, vest_device_id=vest_device_id)
        )
        return session.id


class ActiveSessionLookupAdapter:
    """Resuelve la sesión activa del usuario (sin crearla) para asociar lecturas
    capturadas vía REST a la sesión en curso. Satisface ActiveSessionLookupPort."""

    def __init__(self, session_query_service: ISessionQueryService) -> None:
        self._service = session_query_service

    async def active_session_id(self, user_id: UUID) -> UUID | None:
        session = await self._service.handle_get_active_session(
            GetActiveSessionQuery(user_id=user_id)
        )
        return session.id if session else None
