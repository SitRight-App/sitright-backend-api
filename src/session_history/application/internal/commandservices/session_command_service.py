"""Implementación de ISessionCommandService."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from ....domain.entities.posture_session import PostureSession
from ....domain.model.commands.close_session_command import CloseSessionCommand
from ....domain.model.commands.delete_session_command import DeleteSessionCommand
from ....domain.model.commands.start_session_command import StartSessionCommand
from ....domain.repositories.session_repository import PostureSessionRepository
from ....domain.services.readings_aggregator import ReadingsAggregator
from ....domain.services.session_command_service import ISessionCommandService

# Tope de jornada (ADR-007): una sesión nunca supera estas horas. Si se excede
# (típicamente porque el usuario olvidó cerrarla), se cierra automáticamente en
# la hora de la última lectura real y la siguiente lectura arranca una nueva.
# Así la duración sale correcta y nunca se mezclan lecturas de días distintos.
MAX_SESSION_DURATION = timedelta(hours=10)


@dataclass
class SessionCommandService(ISessionCommandService):
    session_repository: PostureSessionRepository
    readings_aggregator: ReadingsAggregator

    async def handle_start_session(
        self, command: StartSessionCommand
    ) -> PostureSession:
        existing = await self.session_repository.find_active_by_user(command.user_id)
        if existing is not None:
            if datetime.utcnow() - existing.started_at <= MAX_SESSION_DURATION:
                # Idempotente: sesión activa dentro del tope → la devuelvo.
                return existing
            # Excedió el tope de jornada: se quedó abierta. La cerramos en su
            # última lectura real (no en el reloj de pared) y arrancamos otra.
            await self._auto_close(existing)

        session = PostureSession(
            id=uuid4(),
            user_id=command.user_id,
            vest_device_id=command.vest_device_id,
            started_at=datetime.utcnow(),
            note=command.note,
        )
        await self.session_repository.save(session)
        return session

    async def _auto_close(self, session: PostureSession) -> None:
        last_ts = await self.readings_aggregator.last_reading_at(session.id)
        summary = await self.readings_aggregator.aggregate_for_session(session.id)
        session.close(summary, ended_at=last_ts or session.started_at)
        await self.session_repository.save(session)

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

    async def handle_delete_session(self, command: DeleteSessionCommand) -> None:
        session = await self.session_repository.find_by_id(command.session_id)
        # Una sesión ajena se trata como inexistente: no revelamos que existe.
        if session is None or session.user_id != command.user_id:
            raise ValueError("Sesión no encontrada")
        await self.session_repository.delete(command.session_id)
