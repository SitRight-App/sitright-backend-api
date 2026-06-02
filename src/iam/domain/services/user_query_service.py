"""Interfaz del servicio de queries del bounded context IAM."""
from typing import Protocol

from ..entities.notification import Notification
from ..entities.user import User
from ..model.queries.count_unread_notifications_query import (
    CountUnreadNotificationsQuery,
)
from ..model.queries.get_admin_stats_query import AdminStats, GetAdminStatsQuery
from ..model.queries.get_user_query import GetUserQuery
from ..model.queries.list_notifications_query import ListNotificationsQuery
from ..model.queries.list_users_query import ListUsersQuery, UsersPage


class IUserQueryService(Protocol):
    """Casos de uso de lectura del contexto IAM."""

    async def handle_get_user(self, query: GetUserQuery) -> User | None: ...
    async def handle_list_users(self, query: ListUsersQuery) -> UsersPage: ...
    async def handle_list_notifications(
        self, query: ListNotificationsQuery
    ) -> list[Notification]: ...
    async def handle_count_unread_notifications(
        self, query: CountUnreadNotificationsQuery
    ) -> int: ...
    async def handle_get_admin_stats(self, query: GetAdminStatsQuery) -> AdminStats: ...
