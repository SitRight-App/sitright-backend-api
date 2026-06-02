from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ...domain.model.commands.deactivate_user_command import (
    CannotDeactivateAdminError,
    DeactivateUserCommand,
)
from ...domain.model.queries.get_admin_stats_query import GetAdminStatsQuery
from ...domain.model.queries.list_users_query import ListUsersQuery
from ...domain.services.token_service import TokenPayload
from ...domain.services.user_command_service import IUserCommandService
from ...domain.services.user_query_service import IUserQueryService
from ..schemas.user_schema import (
    AnthropometricSchema,
    PreferencesSchema,
    UserResponse,
)
from .dependencies import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_user_command_service: IUserCommandService | None = None
_user_query_service: IUserQueryService | None = None
# HU-29 AC1 — adapters que enriquecen la lista con última sesión y vest.
_last_sessions_lookup = None  # type: ignore[var-annotated]
_linked_vests_lookup = None  # type: ignore[var-annotated]


def set_user_command_service(service: IUserCommandService) -> None:
    global _user_command_service
    _user_command_service = service


def set_user_query_service(service: IUserQueryService) -> None:
    global _user_query_service
    _user_query_service = service


def set_last_sessions_lookup(adapter) -> None:  # noqa: ANN001
    global _last_sessions_lookup
    _last_sessions_lookup = adapter


def set_linked_vests_lookup(adapter) -> None:  # noqa: ANN001
    global _linked_vests_lookup
    _linked_vests_lookup = adapter


def get_user_command_service() -> IUserCommandService:
    if _user_command_service is None:
        raise RuntimeError("UserCommandService no inicializado")
    return _user_command_service


def get_user_query_service() -> IUserQueryService:
    if _user_query_service is None:
        raise RuntimeError("UserQueryService no inicializado")
    return _user_query_service


@router.get("/stats", response_model=dict)
async def get_admin_stats(
    _: Annotated[TokenPayload, Depends(require_admin)],
    service: Annotated[IUserQueryService, Depends(get_user_query_service)],
) -> dict:
    """HU-22 AC1 — estadísticas globales de adopción para el panel admin."""
    stats = await service.handle_get_admin_stats(GetAdminStatsQuery())
    return {
        "active_users": stats.active_users,
        "total_users": stats.total_users,
        "total_sessions": stats.total_sessions,
        "average_adequate_percentage": stats.average_adequate_percentage,
    }


@router.get("/users", response_model=dict)
async def list_users(
    _: Annotated[TokenPayload, Depends(require_admin)],
    service: Annotated[IUserQueryService, Depends(get_user_query_service)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Lista todos los usuarios del sistema (solo admin).

    HU-29 AC1 — enriquecemos cada usuario con la última sesión registrada y
    el estado del chaleco vinculado para mostrarlos en la tabla.
    """
    page = await service.handle_list_users(ListUsersQuery(limit=limit, offset=offset))

    user_ids = [u.id for u in page.users]
    last_sessions = (
        await _last_sessions_lookup.get_last_session_by_user(user_ids)
        if _last_sessions_lookup is not None
        else {}
    )
    linked_vests = (
        await _linked_vests_lookup.get_linked_vest_by_user(user_ids)
        if _linked_vests_lookup is not None
        else {}
    )

    def _serialize(u):  # noqa: ANN001
        base = UserResponse(
            id=str(u.id),
            name=u.name,
            email=u.email,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at,
            anthropometric_data=AnthropometricSchema(
                weight_kg=u.anthropometric_data.weight_kg,
                height_cm=u.anthropometric_data.height_cm,
            ),
            preferences=PreferencesSchema(
                email_notifications=u.preferences.email_notifications,
                alert_threshold_minutes=u.preferences.alert_threshold_minutes,
                break_reminder_minutes=u.preferences.break_reminder_minutes,
                language=u.preferences.language,
            ),
        ).model_dump(mode="json")
        base["last_session_at"] = last_sessions.get(u.id)
        base["linked_vest"] = linked_vests.get(u.id)
        return base

    return {
        "total": page.total,
        "users": [_serialize(u) for u in page.users],
    }


@router.patch("/users/{user_id}/deactivate", status_code=204)
async def deactivate_user(
    user_id: UUID,
    _: Annotated[TokenPayload, Depends(require_admin)],
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> Response:
    """HU-30 — desactivar una cuenta de usuario (solo admin, solo no-admin)."""
    try:
        await service.handle_deactivate_user(DeactivateUserCommand(user_id=user_id))
    except CannotDeactivateAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)
