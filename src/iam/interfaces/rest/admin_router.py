from typing import Annotated

from fastapi import APIRouter, Depends, Query

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


def set_list_users_handler(handler: ListUsersHandler) -> None:
    global _list_users_handler
    _list_users_handler = handler


def get_list_users_handler() -> ListUsersHandler:
    if _list_users_handler is None:
        raise RuntimeError("ListUsersHandler no inicializado")
    return _list_users_handler


class _UsersPageResponse(UserResponse):
    pass


@router.get("/users", response_model=dict)
async def list_users(
    _: Annotated[TokenPayload, Depends(require_admin)],
    handler: Annotated[ListUsersHandler, Depends(get_list_users_handler)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    """Lista todos los usuarios del sistema (solo admin)."""
    page = await handler.execute(ListUsersQuery(limit=limit, offset=offset))
    return {
        "total": page.total,
        "users": [
            UserResponse(
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
                    language=u.preferences.language,
                ),
            ).model_dump(mode="json")
            for u in page.users
        ],
    }
