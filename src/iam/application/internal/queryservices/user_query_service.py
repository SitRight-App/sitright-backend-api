"""Implementación del servicio de queries del bounded context IAM.

Agrupa todos los casos de uso de lectura en una clase única, siguiendo la
convención `XxxQueryService` documentada en el class diagram.
"""
from __future__ import annotations

from dataclasses import dataclass

from ....domain.entities.notification import Notification
from ....domain.entities.user import User
from ....domain.model.queries.count_unread_notifications_query import (
    CountUnreadNotificationsQuery,
)
from ....domain.model.queries.get_admin_stats_query import (
    AdminStats,
    GetAdminStatsQuery,
    SessionStatsPort,
)
from ....domain.model.queries.get_user_query import GetUserQuery
from ....domain.model.queries.list_notifications_query import ListNotificationsQuery
from ....domain.model.queries.list_users_query import ListUsersQuery, UsersPage
from ....domain.repositories.notification_repository import NotificationRepository
from ....domain.repositories.user_repository import UserRepository
from ....domain.services.user_query_service import IUserQueryService


@dataclass
class UserQueryService(IUserQueryService):
    user_repository: UserRepository
    notification_repository: NotificationRepository
    session_stats: SessionStatsPort

    async def handle_get_user(self, query: GetUserQuery) -> User | None:
        return await self.user_repository.find_by_id(query.user_id)

    async def handle_list_users(self, query: ListUsersQuery) -> UsersPage:
        users = await self.user_repository.find_all(
            limit=query.limit, offset=query.offset, active=query.active
        )
        total = await self.user_repository.count_all(active=query.active)
        return UsersPage(total=total, users=users)

    async def handle_list_notifications(
        self, query: ListNotificationsQuery
    ) -> list[Notification]:
        return await self.notification_repository.find_by_user_id(
            query.user_id, query.limit, query.offset
        )

    async def handle_count_unread_notifications(
        self, query: CountUnreadNotificationsQuery
    ) -> int:
        return await self.notification_repository.count_unread(query.user_id)

    async def handle_get_admin_stats(self, _query: GetAdminStatsQuery) -> AdminStats:
        active = await self.user_repository.count_active()
        total = await self.user_repository.count_all()
        sessions = await self.session_stats.total_sessions()
        avg_adequate = await self.session_stats.average_adequate_percentage()
        return AdminStats(
            active_users=active,
            total_users=total,
            total_sessions=sessions,
            average_adequate_percentage=avg_adequate,
        )
