"""Implementación de ISessionCommandService."""
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from ....domain.entities.posture_session import PostureSession
from ....domain.model.commands.close_session_command import CloseSessionCommand
from ....domain.model.commands.start_session_command import StartSessionCommand
from ....domain.repositories.session_repository import PostureSessionRepository
from ....domain.services.readings_aggregator import ReadingsAggregator


@dataclass
class SessionCommandService:
    session_repository: PostureSessionRepository
    readings_aggregator: ReadingsAggregator

    async def handle_start_session(
        self, command: StartSessionCommand
    ) -> PostureSession:
        # Idempotente: si ya hay sesión activa para el usuario, la devuelvo.
        existing = await self.session_repository.find_active_by_user(command.user_id)
        if existing is not None:
            return existing

        session = PostureSession(
            id=uuid4(),
            user_id=command.user_id,
            vest_device_id=command.vest_device_id,
            started_at=datetime.utcnow(),
            note=command.note,
        )
        await self.session_repository.save(session)
        return session

    async def handle_close_session(
        self, command: CloseSessionCommand
    ) -> PostureSession:
        session = await self.session_repository.find_by_id(command.session_id)
        if session is None:
            raise ValueError("Sesión no encontrada")
        if not session.is_active():
            return session  # idempotente

        summary = await self.readings_aggregator.aggregate_for_session(session.id)
        session.close(summary, ended_at=datetime.utcnow())
        if command.note:
            session.note = command.note
        await self.session_repository.save(session)
        return session
