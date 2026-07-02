from datetime import datetime
from uuid import uuid4

from src.iam.application.internal.queryservices.user_query_service import (
    UserQueryService,
)
from src.iam.domain.entities.user import User
from src.iam.domain.model.queries.list_users_query import ListUsersQuery
from src.iam.domain.value_objects.role import Role

NOW = datetime(2026, 7, 1, 12, 0, 0)


class _UserRepo:
    """Fake in-memory que replica el filtro `active` de MongoUserRepository."""

    def __init__(self, users):
        self._users = list(users)

    async def find_all(self, limit: int = 100, offset: int = 0, active=None):
        users = self._users if active is None else [
            u for u in self._users if u.is_active == active
        ]
        return users[offset : offset + limit]

    async def count_all(self, active=None):
        if active is None:
            return len(self._users)
        return len([u for u in self._users if u.is_active == active])

    async def count_active(self):
        return len([u for u in self._users if u.is_active])


def _user(**kw) -> User:
    base = dict(
        id=uuid4(), name="Ana", email="ana@correo.com", password_hash="hashed",
        role=Role.WORKER, created_at=NOW, updated_at=NOW, is_active=True,
    )
    base.update(kw)
    return User(**base)


def _service(users):
    return UserQueryService(
        user_repository=_UserRepo(users),
        notification_repository=None,
        session_stats=None,
    )


async def test_lista_todos_los_usuarios_cuando_no_se_filtra():
    users = [_user(is_active=True), _user(is_active=False)]
    svc = _service(users)
    page = await svc.handle_list_users(ListUsersQuery())
    assert page.total == 2
    assert len(page.users) == 2


async def test_filtra_solo_usuarios_activos():
    activo = _user(is_active=True)
    inactivo = _user(is_active=False)
    svc = _service([activo, inactivo])
    page = await svc.handle_list_users(ListUsersQuery(active=True))
    assert page.total == 1
    assert page.users == [activo]


async def test_filtra_solo_usuarios_inactivos():
    activo = _user(is_active=True)
    inactivo = _user(is_active=False)
    svc = _service([activo, inactivo])
    page = await svc.handle_list_users(ListUsersQuery(active=False))
    assert page.total == 1
    assert page.users == [inactivo]
