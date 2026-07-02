from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response

from ...domain.model.commands.change_password_command import (
    ChangePasswordCommand,
    InvalidCurrentPasswordError,
)
from ...domain.model.commands.mark_all_notifications_read_command import (
    MarkAllNotificationsReadCommand,
)
from ...domain.model.commands.mark_notification_read_command import (
    MarkNotificationReadCommand,
)
from ...domain.model.commands.notify_event_command import (
    InvalidNotificationEventError,
    NotifyEventCommand,
)
from ...domain.model.commands.update_profile_command import UpdateProfileCommand
from ...domain.model.queries.count_unread_notifications_query import (
    CountUnreadNotificationsQuery,
)
from ...domain.model.queries.get_user_query import GetUserQuery
from ...domain.model.queries.list_notifications_query import ListNotificationsQuery
from ...domain.services.token_service import TokenPayload
from ...domain.services.user_command_service import IUserCommandService
from ...domain.services.user_query_service import IUserQueryService
from ....shared.openapi_responses import (
    NOT_FOUND_USER,
    PYDANTIC_VALIDATION,
    UNAUTHORIZED,
)
from ..schemas.auth_schema import ChangePasswordRequest
from ..schemas.user_schema import (
    AnthropometricSchema,
    NotificationResponse,
    NotifyEventRequest,
    PreferencesSchema,
    UnreadNotificationsResponse,
    UpdateProfileRequest,
    UserResponse,
)
from .dependencies import get_current_user

router = APIRouter(prefix="/api/v1/users", tags=["iam"])

_user_command_service: IUserCommandService | None = None
_user_query_service: IUserQueryService | None = None


def set_user_command_service(service: IUserCommandService) -> None:
    global _user_command_service
    _user_command_service = service


def set_user_query_service(service: IUserQueryService) -> None:
    global _user_query_service
    _user_query_service = service


def get_user_command_service() -> IUserCommandService:
    if _user_command_service is None:
        raise RuntimeError("UserCommandService no inicializado")
    return _user_command_service


def get_user_query_service() -> IUserQueryService:
    if _user_query_service is None:
        raise RuntimeError("UserQueryService no inicializado")
    return _user_query_service


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
            break_reminder_minutes=user.preferences.break_reminder_minutes,
            language=user.preferences.language,
        ),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener mi perfil",
    responses={200: {"description": "Perfil completo del usuario actual."}, **UNAUTHORIZED, **NOT_FOUND_USER},
)
async def get_me(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IUserQueryService, Depends(get_user_query_service)],
) -> UserResponse:
    user = await service.handle_get_user(GetUserQuery(user_id=current.user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _to_user_response(user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Actualizar mi perfil",
    responses={
        200: {"description": "Perfil actualizado."},
        400: {
            "description": (
                "datos antropométricos fuera de rango razonable "
                "(estatura 100-250 cm, peso 25-300 kg)."
            ),
            "content": {
                "application/json": {
                    "example": {"detail": "La estatura debe estar entre 100 y 250 cm"}
                }
            },
        },
        **UNAUTHORIZED,
        **PYDANTIC_VALIDATION,
    },
)
async def update_me(
    request: UpdateProfileRequest,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> UserResponse:
    command = UpdateProfileCommand(
        user_id=current.user_id,
        name=request.name,
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
        email_notifications=request.email_notifications,
        alert_threshold_minutes=request.alert_threshold_minutes,
        break_reminder_minutes=request.break_reminder_minutes,
        language=request.language,
    )
    try:
        user = await service.handle_update_profile(command)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_user_response(user)


@router.post(
    "/me/password",
    status_code=204,
    summary="Cambiar mi contraseña",
    responses={
        204: {"description": "Contraseña actualizada."},
        400: {
            "description": "la contraseña actual proporcionada no coincide.",
            "content": {
                "application/json": {
                    "example": {"detail": "La contraseña actual es incorrecta"}
                }
            },
        },
        **UNAUTHORIZED,
        **PYDANTIC_VALIDATION,
    },
)
async def change_my_password(
    request: ChangePasswordRequest,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> Response:
    """cambio de contraseña desde el perfil del usuario actual."""
    try:
        await service.handle_change_password(
            ChangePasswordCommand(
                user_id=current.user_id,
                current_password=request.current_password,
                new_password=request.new_password,
            )
        )
    except InvalidCurrentPasswordError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return Response(status_code=204)


@router.get(
    "/me/notifications/unread-count",
    response_model=UnreadNotificationsResponse,
    summary="Contar notificaciones no leídas (badge del topbar)",
    responses={200: {"content": {"application/json": {"example": {"count": 3}}}}, **UNAUTHORIZED},
)
async def count_unread_my_notifications(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IUserQueryService, Depends(get_user_query_service)],
) -> UnreadNotificationsResponse:
    count = await service.handle_count_unread_notifications(
        CountUnreadNotificationsQuery(user_id=current.user_id)
    )
    return UnreadNotificationsResponse(count=count)


@router.get(
    "/me/notifications",
    response_model=list[NotificationResponse],
    summary="Listar mis notificaciones",
    responses={200: {"description": "Notificaciones del usuario, ordenadas por `sent_at` descendente."}, **UNAUTHORIZED},
)
async def list_my_notifications(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IUserQueryService, Depends(get_user_query_service)],
    limit: int = 20,
    offset: int = 0,
) -> list[NotificationResponse]:
    notifs = await service.handle_list_notifications(
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


@router.patch(
    "/me/notifications/{notification_id}/read",
    status_code=204,
    summary="Marcar una notificación como leída",
    responses={204: {"description": "Idempotente — marcar dos veces no hace nada extra."}, **UNAUTHORIZED},
)
async def mark_my_notification_read(
    notification_id: UUID,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> Response:
    """Marca una notificación como leída. Idempotente."""
    await service.handle_mark_notification_read(
        MarkNotificationReadCommand(notification_id=notification_id)
    )
    return Response(status_code=204)


@router.patch(
    "/me/notifications/read-all",
    summary="Marcar todas mis notificaciones como leídas",
    responses={
        200: {
            "content": {"application/json": {"example": {"marked_as_read": 5}}},
            "description": "Conteo de notificaciones que pasaron de no-leídas a leídas.",
        },
        **UNAUTHORIZED,
    },
)
async def mark_all_my_notifications_read(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> dict:
    """Marca todas las notificaciones del usuario como leídas."""
    count = await service.handle_mark_all_notifications_read(
        MarkAllNotificationsReadCommand(user_id=current.user_id)
    )
    return {"marked_as_read": count}


@router.post(
    "/me/notifications",
    status_code=204,
    summary="Notificar un evento de postura/pausa (alerta o recordatorio)",
    responses={
        204: {"description": "Evento procesado (puede omitirse por cooldown anti-spam)."},
        **UNAUTHORIZED,
        **PYDANTIC_VALIDATION,
    },
)
async def notify_my_event(
    request: NotifyEventRequest,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> Response:
    """El frontend calcula las alertas y notifica el evento aquí (postura mala
    prolongada o recordatorio de pausa activa)."""
    try:
        await service.handle_notify_event(
            NotifyEventCommand(user_id=current.user_id, event_type=request.type)
        )
    except InvalidNotificationEventError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return Response(status_code=204)
