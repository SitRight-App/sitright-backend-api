from dataclasses import dataclass

from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class ListUsersQuery:
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class UsersPage:
    total: int
    users: list[User]


@dataclass
class ListUsersHandler:
    repo: UserRepository

    async def execute(self, query: ListUsersQuery) -> UsersPage:
        users = await self.repo.find_all(limit=query.limit, offset=query.offset)
        total = await self.repo.count_all()
        return UsersPage(total=total, users=users)
