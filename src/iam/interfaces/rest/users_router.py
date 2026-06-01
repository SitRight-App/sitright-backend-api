from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from ...application.commands.mark_all_notifications_read_handler import (
    MarkAllNotificationsReadCommand,
    MarkAllNotificationsReadHandler,
)
from ...application.commands.mark_notification_read_handler import (
    MarkNotificationReadCommand,
    MarkNotificationReadHandler,
)
from ...application.commands.update_profile_handler import (
    UpdateProfileCommand,
    UpdateProfileHandler,
)
from ...application.queries.count_unread_notifications_handler import (
    CountUnreadNotificationsHandler,
    CountUnreadNotificationsQuery,
)
from ...application.queries.get_user_handler import GetUserHandler, GetUserQuery
from ...application.queries.list_notifications_handler import (
    ListNotificationsHandler,
    ListNotificationsQuery,
)
from ...domain.services.token_service import TokenPayload
from ..schemas.user_schema import (
    AnthropometricSchema,
    NotificationResponse,
    PreferencesSchema,
    UnreadNotificationsResponse,
    UpdateProfileRequest,
    UserResponse,
)
from .dependencies import get_current_user

router = APIRouter(prefix="/api/v1/users", tags=["iam"])

_get_user_handler: GetUserHandler | None = None
_update_profile_handler: UpdateProfileHandler | None = None
_list_notifications_handler: ListNotificationsHandler | None = None
_count_unread_handler: CountUnreadNotificationsHandler | None = None
_mark_read_handler: MarkNotificationReadHandler | None = None
_mark_all_read_handler: MarkAllNotificationsReadHandler | None = None


def set_get_user_handler(handler: GetUserHandler) -> None:
    global _get_user_handler
    _get_user_handler = handler


def set_update_profile_handler(handler: UpdateProfileHandler) -> None:
    global _update_profile_handler
    _update_profile_handler = handler


def set_list_notifications_handler(handler: ListNotificationsHandler) -> None:
    global _list_notifications_handler
    _list_notifications_handler = handler


def set_count_unread_handler(handler: CountUnreadNotificationsHandler) -> None:
    global _count_unread_handler
    _count_unread_handler = handler


def set_mark_read_handler(handler: MarkNotificationReadHandler) -> None:
    global _mark_read_handler
    _mark_read_handler = handler


def set_mark_all_read_handler(handler: MarkAllNotificationsReadHandler) -> None:
    global _mark_all_read_handler
    _mark_all_read_handler = handler


def get_get_user_handler() -> GetUserHandler:
    if _get_user_handler is None:
        raise RuntimeError("GetUserHandler no inicializado")
    return _get_user_handler


def get_update_profile_handler() -> UpdateProfileHandler:
    if _update_profile_handler is None:
        raise RuntimeError("UpdateProfileHandler no inicializado")
    return _update_profile_handler


def get_list_notifications_handler() -> ListNotificationsHandler:
    if _list_notifications_handler is None:
        raise RuntimeError("ListNotificationsHandler no inicializado")
    return _list_notifications_handler


def get_count_unread_handler() -> CountUnreadNotificationsHandler:
    if _count_unread_handler is None:
        raise RuntimeError("CountUnreadNotificationsHandler no inicializado")
    return _count_unread_handler


def get_mark_read_handler() -> MarkNotificationReadHandler:
    if _mark_read_handler is None:
        raise RuntimeError("MarkNotificationReadHandler no inicializado")
    return _mark_read_handler


def get_mark_all_read_handler() -> MarkAllNotificationsReadHandler:
    if _mark_all_read_handler is None:
        raise RuntimeError("MarkAllNotificationsReadHandler no inicializado")
    return _mark_all_read_handler


def _to_user_response(user) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        anthropometric_data=AnthropometricSchema(
            weight_kg=user.anthropometric_data.weight_kg,
            height_cm=user.anthropometric_data.height_cm,
        ),
        preferences=PreferencesSchema(
            email_notifications=user.preferences.email_notifications,
            alert_threshold_minutes=user.preferences.alert_threshold_minutes,
            language=user.preferences.language,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[GetUserHandler, Depends(get_get_user_handler)],
) -> UserResponse:
    user = await handler.execute(GetUserQuery(user_id=current.user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _to_user_response(user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UpdateProfileRequest,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[UpdateProfileHandler, Depends(get_update_profile_handler)],
) -> UserResponse:
    command = UpdateProfileCommand(
        user_id=current.user_id,
        name=request.name,
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
        email_notifications=request.email_notifications,
        alert_threshold_minutes=request.alert_threshold_minutes,
        language=request.language,
    )
    try:
        user = await handler.execute(command)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_user_response(user)


@router.get(
    "/me/notifications/unread-count",
    response_model=UnreadNotificationsResponse,
)
async def count_unread_my_notifications(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[
        CountUnreadNotificationsHandler, Depends(get_count_unread_handler)
    ],
) -> UnreadNotificationsResponse:
    """Devuelve el número de notificaciones sin leer del usuario, para el badge del topbar."""
    count = await handler.execute(CountUnreadNotificationsQuery(user_id=current.user_id))
    return UnreadNotificationsResponse(count=count)


@router.get("/me/notifications", response_model=list[NotificationResponse])
async def list_my_notifications(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[ListNotificationsHandler, Depends(get_list_notifications_handler)],
    limit: int = 20,
    offset: int = 0,
) -> list[NotificationResponse]:
    notifs = await handler.execute(
        ListNotificationsQuery(user_id=current.user_id, limit=limit, offset=offset)
    )
    return [
        NotificationResponse(
            id=str(n.id),
            type=n.type.value,
            message=n.message,
            channel=n.channel.value,
            sent_at=n.sent_at,
            is_read=n.is_read,
        )
        for n in notifs
    ]


@router.patch("/me/notifications/{notification_id}/read", status_code=204)
async def mark_my_notification_read(
    notification_id: UUID,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[
        MarkNotificationReadHandler, Depends(get_mark_read_handler)
    ],
) -> Response:
    """Marca una notificación como leída. Idempotente."""
    await handler.execute(MarkNotificationReadCommand(notification_id=notification_id))
    return Response(status_code=204)


@router.patch("/me/notifications/read-all")
async def mark_all_my_notifications_read(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[
        MarkAllNotificationsReadHandler, Depends(get_mark_all_read_handler)
    ],
) -> dict:
    """Marca todas las notificaciones del usuario como leídas. Devuelve el conteo afectado."""
    count = await handler.execute(MarkAllNotificationsReadCommand(user_id=current.user_id))
    return {"marked_as_read": count}
