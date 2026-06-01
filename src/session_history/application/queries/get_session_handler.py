from dataclasses import dataclass
from uuid import UUID

from ...domain.entities.posture_session import PostureSession
from ...domain.repositories.session_repository import PostureSessionRepository


@dataclass
class GetSessionQuery:
    session_id: UUID


@dataclass
class GetActiveSessionQuery:
    user_id: UUID


class GetSessionHandler:
    def __init__(self, repo: PostureSessionRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetSessionQuery) -> PostureSession | None:
        return await self._repo.find_by_id(query.session_id)


class GetActiveSessionHandler:
    def __init__(self, repo: PostureSessionRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetActiveSessionQuery) -> PostureSession | None:
        return await self._repo.find_active_by_user(query.user_id)
