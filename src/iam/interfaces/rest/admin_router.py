from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ...application.commands.deactivate_user_handler import (
    CannotDeactivateAdminError,
    DeactivateUserCommand,
    DeactivateUserHandler,
)
from ...application.queries.get_admin_stats_handler import GetAdminStatsHandler
from ...application.queries.list_users_handler import (
    ListUsersHandler,
    ListUsersQuery,
)
from ...domain.services.token_service import TokenPayload
from ..schemas.user_schema import (
    AnthropometricSchema,
    PreferencesSchema,
    UserResponse,
)
from .dependencies import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_list_users_handler: ListUsersHandler | None = None
_admin_stats_handler: GetAdminStatsHandler | None = None
_deactivate_user_handler: DeactivateUserHandler | None = None
# HU-29 AC1 — adapters que enriquecen la lista de usuarios con su última
# sesión y el estado del chaleco vinculado.
_last_sessions_lookup = None  # type: ignore[var-annotated]
_linked_vests_lookup = None  # type: ignore[var-annotated]


def set_last_sessions_lookup(adapter) -> None:  # noqa: ANN001 — adapter duck-typed
    global _last_sessions_lookup
    _last_sessions_lookup = adapter


def set_linked_vests_lookup(adapter) -> None:  # noqa: ANN001
    global _linked_vests_lookup
    _linked_vests_lookup = adapter


def set_deactivate_user_handler(handler: DeactivateUserHandler) -> None:
    global _deactivate_user_handler
    _deactivate_user_handler = handler


def get_deactivate_user_handler() -> DeactivateUserHandler:
    if _deactivate_user_handler is None:
        raise RuntimeError("DeactivateUserHandler no inicializado")
    return _deactivate_user_handler


def set_list_users_handler(handler: ListUsersHandler) -> None:
    global _list_users_handler
    _list_users_handler = handler


def set_admin_stats_handler(handler: GetAdminStatsHandler) -> None:
    global _admin_stats_handler
    _admin_stats_handler = handler


def get_list_users_handler() -> ListUsersHandler:
    if _list_users_handler is None:
        raise RuntimeError("ListUsersHandler no inicializado")
    return _list_users_handler


def get_admin_stats_handler() -> GetAdminStatsHandler:
    if _admin_stats_handler is None:
        raise RuntimeError("GetAdminStatsHandler no inicializado")
    return _admin_stats_handler


class _UsersPageResponse(UserResponse):
    pass


@router.get("/stats", response_model=dict)
async def get_admin_stats(
    _: Annotated[TokenPayload, Depends(require_admin)],
    handler: Annotated[GetAdminStatsHandler, Depends(get_admin_stats_handler)],
) -> dict:
    """HU-22 AC1 — estadísticas globales de adopción para el panel admin.

    Devuelve usuarios activos, sesiones totales y promedio de postura
    adecuada general.
    """
    stats = await handler.execute()
    return {
        "active_users": stats.active_users,
        "total_users": stats.total_users,
        "total_sessions": stats.total_sessions,
        "average_adequate_percentage": stats.average_adequate_percentage,
    }


@router.get("/users", response_model=dict)
async def list_users(
    _: Annotated[TokenPayload, Depends(require_admin)],
    handler: Annotated[ListUsersHandler, Depends(get_list_users_handler)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Lista todos los usuarios del sistema (solo admin).

    HU-29 AC1 — enriquecemos cada usuario con la última sesión registrada y
    el estado del chaleco vinculado para mostrarlos en la tabla.
    """
    page = await handler.execute(ListUsersQuery(limit=limit, offset=offset))

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
    handler: Annotated[DeactivateUserHandler, Depends(get_deactivate_user_handler)],
) -> Response:
    """HU-30 — desactivar una cuenta de usuario (solo admin, solo no-admin)."""
    try:
        await handler.execute(DeactivateUserCommand(user_id=user_id))
    except CannotDeactivateAdminError as exc:
        # AC2 — intentar desactivar a otro admin
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)
