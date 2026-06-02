from dataclasses import dataclass
from typing import Protocol

from ...domain.repositories.user_repository import UserRepository


class SessionStatsPort(Protocol):
    """Port que cualquier infraestructura debe satisfacer para que el handler
    del panel admin pueda traer las métricas globales sin importar otro
    bounded context directamente."""

    async def total_sessions(self) -> int: ...
    async def average_adequate_percentage(self) -> float | None: ...


@dataclass(frozen=True)
class AdminStats:
    active_users: int
    total_users: int
    total_sessions: int
    average_adequate_percentage: float | None


@dataclass
class GetAdminStatsHandler:
    """Resuelve las 3 métricas que el AC HU-22 AC1 pide en el panel admin."""

    user_repo: UserRepository
    session_stats: SessionStatsPort

    async def execute(self) -> AdminStats:
        active = await self.user_repo.count_active()
        total = await self.user_repo.count_all()
        sessions = await self.session_stats.total_sessions()
        avg_adequate = await self.session_stats.average_adequate_percentage()
        return AdminStats(
            active_users=active,
            total_users=total,
            total_sessions=sessions,
            average_adequate_percentage=avg_adequate,
        )
