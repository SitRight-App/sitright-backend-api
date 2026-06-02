from dataclasses import dataclass

from ...entities.user import User


@dataclass(frozen=True)
class ListUsersQuery:
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class UsersPage:
    """Resultado de ListUsersQuery — total + slice paginado."""

    total: int
    users: list[User]
