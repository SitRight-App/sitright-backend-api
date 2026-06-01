from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ...domain.entities.posture_session import PostureSession
from ...domain.repositories.session_repository import PostureSessionRepository


@dataclass
class StartSessionCommand:
    user_id: UUID
    vest_device_id: UUID
    note: str | None = None


class StartSessionHandler:
    def __init__(self, repo: PostureSessionRepository) -> None:
        self._repo = repo

    async def execute(self, command: StartSessionCommand) -> PostureSession:
        existing = await self._repo.find_active_by_user(command.user_id)
        if existing is not None:
            return existing  # idempotente: ya hay sesión activa

        session = PostureSession(
            id=uuid4(),
            user_id=command.user_id,
            vest_device_id=command.vest_device_id,
            started_at=datetime.utcnow(),
            note=command.note,
        )
        await self._repo.save(session)
        return session
