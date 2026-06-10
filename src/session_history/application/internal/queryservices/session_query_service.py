"""Implementación de ISessionQueryService."""
from dataclasses import dataclass
from uuid import UUID

from ....domain.entities.posture_session import PostureSession
from ....domain.model.queries.get_session_query import (
    GetActiveSessionQuery,
    GetSessionQuery,
)
from ....domain.model.queries.list_sessions_query import ListSessionsQuery
from ....domain.repositories.session_repository import PostureSessionRepository
from ....domain.services.session_query_service import ISessionQueryService
from ....domain.services.zone_analyzer import ZoneAnalyzer
from ....domain.value_objects.zone_analysis import SessionZoneAnalysis


@dataclass
class SessionQueryService(ISessionQueryService):
    session_repository: PostureSessionRepository
    zone_analyzer: ZoneAnalyzer | None = None

    async def handle_get_session(
        self, query: GetSessionQuery
    ) -> PostureSession | None:
        return await self.session_repository.find_by_id(query.session_id)

    async def handle_zone_analysis(
        self, session_id: UUID
    ) -> SessionZoneAnalysis | None:
        session = await self.session_repository.find_by_id(session_id)
        if session is None or self.zone_analyzer is None:
            return None
        return await self.zone_analyzer.analyze(
            session.vest_device_id, session.started_at, session.ended_at
        )

    async def handle_get_active_session(
        self, query: GetActiveSessionQuery
    ) -> PostureSession | None:
        return await self.session_repository.find_active_by_user(query.user_id)

    async def handle_list_sessions(
        self, query: ListSessionsQuery
    ) -> list[PostureSession]:
        return await self.session_repository.find_by_user(
            query.user_id, query.limit, query.offset, query.since, query.until
        )
