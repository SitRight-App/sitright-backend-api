from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...domain.entities.posture_session import PostureSession
from ...domain.repositories.session_repository import PostureSessionRepository


@dataclass
class ListSessionsQuery:
    user_id: UUID
    limit: int = 20
    offset: int = 0
    since: datetime | None = None
    until: datetime | None = None


class ListSessionsHandler:
    def __init__(self, repo: PostureSessionRepository) -> None:
        self._repo = repo

    async def execute(self, query: ListSessionsQuery) -> list[PostureSession]:
        return await self._repo.find_by_user(
            query.user_id, query.limit, query.offset, query.since, query.until
        )
