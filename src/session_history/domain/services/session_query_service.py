"""Interfaz del servicio de queries para session_history."""
from typing import Protocol

from ..entities.posture_session import PostureSession
from ..model.queries.get_session_query import GetActiveSessionQuery, GetSessionQuery
from ..model.queries.list_sessions_query import ListSessionsQuery


class ISessionQueryService(Protocol):
    async def handle_get_session(self, query: GetSessionQuery) -> PostureSession | None: ...
    async def handle_get_active_session(
        self, query: GetActiveSessionQuery
    ) -> PostureSession | None: ...
    async def handle_list_sessions(
        self, query: ListSessionsQuery
    ) -> list[PostureSession]: ...
