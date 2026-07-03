from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GetAdminStatsQuery:
    """Métricas globales del piloto. Query sin parámetros, sólo
    pide los conteos agregados."""


@dataclass(frozen=True)
class AdminStats:
    active_users: int
    total_users: int
    total_sessions: int
    average_adequate_percentage: float | None


class SessionStatsPort(Protocol):
    """Port que cualquier infraestructura debe satisfacer para que el query
    service del panel admin pueda traer las métricas globales sin importar
    otro bounded context directamente."""

    async def total_sessions(self) -> int: ...
    async def average_adequate_percentage(self) -> float | None: ...
