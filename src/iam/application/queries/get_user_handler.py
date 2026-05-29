from dataclasses import dataclass
from uuid import UUID

from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository


@dataclass
class GetUserQuery:
    user_id: UUID


class GetUserHandler:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetUserQuery) -> User | None:
        return await self._repo.find_by_id(query.user_id)
