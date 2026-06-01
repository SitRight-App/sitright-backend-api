from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ...domain.entities.posture_session import PostureSession
from ...domain.repositories.session_repository import PostureSessionRepository
from ...domain.value_objects.session_summary import SessionSummary


class ReadingsAggregator(Protocol):
    async def aggregate_for_session(self, session_id: UUID) -> SessionSummary: ...


@dataclass
class CloseSessionCommand:
    session_id: UUID
    note: str | None = None


class CloseSessionHandler:
    def __init__(
        self,
        repo: PostureSessionRepository,
        aggregator: ReadingsAggregator,
    ) -> None:
        self._repo = repo
        self._aggregator = aggregator

    async def execute(self, command: CloseSessionCommand) -> PostureSession:
        session = await self._repo.find_by_id(command.session_id)
        if session is None:
            raise ValueError("Sesión no encontrada")
        if not session.is_active():
            return session  # idempotente

        summary = await self._aggregator.aggregate_for_session(session.id)
        session.close(summary, ended_at=datetime.utcnow())
        if command.note:
            session.note = command.note
        await self._repo.save(session)
        return session
