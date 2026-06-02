from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user, require_admin
from ...domain.entities.vest_device import VestDevice
from ...domain.model.commands.calibrate_vest_command import CalibrateVestCommand
from ...domain.model.commands.link_vest_command import LinkVestCommand
from ...domain.model.commands.register_vest_command import RegisterVestCommand
from ...domain.model.commands.send_vest_command_command import SendVestCommand
from ...domain.model.commands.unlink_vest_command import UnlinkVestCommand
from ...domain.model.queries.get_my_vest_query import GetMyVestQuery
from ...domain.services.vest_command_service import IVestCommandService
from ...domain.services.vest_query_service import IVestQueryService
from ..schemas.vest_schema import (
    CalibrateVestRequest,
    LinkVestRequest,
    LinkVestResponse,
    RegisterVestRequest,
    SendCommandRequest,
    VestResponse,
)
from ....shared.openapi_responses import (
    FORBIDDEN_ADMIN_ONLY,
    NOT_FOUND_VEST,
    PYDANTIC_VALIDATION,
    UNAUTHORIZED,
)

router = APIRouter(prefix="/api/v1/vests", tags=["vest_management"])

_command_service: IVestCommandService | None = None
_query_service: IVestQueryService | None = None


def set_command_service(service: IVestCommandService) -> None:
    global _command_service
    _command_service = service


def set_query_service(service: IVestQueryService) -> None:
    global _query_service
    _query_service = service


def get_command_service() -> IVestCommandService:
    if _command_service is None:
        raise RuntimeError("VestCommandService no inicializado")
    return _command_service


def get_query_service() -> IVestQueryService:
    if _query_service is None:
        raise RuntimeError("VestQueryService no inicializado")
    return _query_service


def _to_response(d: VestDevice) -> VestResponse:
    return VestResponse(
        id=str(d.id),
        mac_address=d.mac_address,
        user_id=str(d.user_id) if d.user_id else None,
        firmware_version=d.firmware_version,
        battery_level=d.battery_level,
        is_active=d.is_active,
        is_calibrated=d.is_calibrated(),
        is_linked=d.is_linked(),
        linked_at=d.linked_at,
        created_at=d.created_at,
    )


@router.post(
    "/register",
    status_code=201,
    response_model=VestResponse,
    summary="Registrar un chaleco nuevo en el catálogo (solo admin)",
    responses={
        201: {"description": "Chaleco creado, aún no vinculado a ningún usuario."},
        400: {
            "description": "MAC con formato inválido o ya registrada.",
            "content": {"application/json": {"example": {"detail": "MAC address inválida"}}},
        },
        **UNAUTHORIZED,
        **FORBIDDEN_ADMIN_ONLY,
        **PYDANTIC_VALIDATION,
    },
)
async def register_vest(
    request: RegisterVestRequest,
    _: Annotated[TokenPayload, Depends(require_admin)],
    service: Annotated[IVestCommandService, Depends(get_command_service)],
) -> VestResponse:
    try:
        device = await service.handle_register_vest(
            RegisterVestCommand(
                mac_address=request.mac_address,
                firmware_version=request.firmware_version,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_response(device)


@router.post(
    "/link",
    response_model=LinkVestResponse,
    summary="Vincular un chaleco a mi cuenta",
    responses={
        200: {
            "description": (
                "Chaleco vinculado. Devuelve credenciales MQTT que el firmware "
                "debe configurar (la contraseña no se vuelve a mostrar)."
            )
        },
        400: {
            "description": "Código de emparejamiento inválido, MAC no registrada, o ya vinculado a otro usuario.",
            "content": {
                "application/json": {
                    "example": {"detail": "El chaleco ya está vinculado a otro usuario"}
                }
            },
        },
        **UNAUTHORIZED,
        **PYDANTIC_VALIDATION,
    },
)
async def link_vest(
    request: LinkVestRequest,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IVestCommandService, Depends(get_command_service)],
) -> LinkVestResponse:
    try:
        device, plain_password = await service.handle_link_vest(
            LinkVestCommand(
                mac_address=request.mac_address,
                user_id=current.user_id,
                pairing_code=request.pairing_code,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return LinkVestResponse(
        vest=_to_response(device),
        mqtt_username=device.mqtt_credentials.username,
        mqtt_password=plain_password,
    )


@router.post(
    "/{vest_id}/calibrate",
    response_model=VestResponse,
    summary="Calibrar postura neutra",
    responses={
        200: {
            "description": (
                "Calibración almacenada. El cliente envía el promedio de 5 s "
                "de muestreo previo de `/readings/latest/raw`."
            )
        },
        400: {
            "description": "Chaleco no encontrado o no vinculado.",
            "content": {
                "application/json": {
                    "example": {"detail": "Solo se puede calibrar un chaleco vinculado"}
                }
            },
        },
        **UNAUTHORIZED,
        **PYDANTIC_VALIDATION,
    },
)
async def calibrate_vest(
    vest_id: UUID,
    request: CalibrateVestRequest,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IVestCommandService, Depends(get_command_service)],
) -> VestResponse:
    try:
        device = await service.handle_calibrate_vest(
            CalibrateVestCommand(
                device_id=vest_id,
                cervical=request.cervical.as_tuple(),
                dorsal=request.dorsal.as_tuple(),
                lumbar=request.lumbar.as_tuple(),
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_response(device)


@router.post(
    "/{vest_id}/commands",
    status_code=202,
    summary="Enviar comando al firmware del chaleco vía MQTT (solo admin)",
    responses={
        202: {"content": {"application/json": {"example": {"status": "queued"}}}},
        400: {
            "description": (
                "Comando desconocido o `firmware_version` faltante en "
                "`firmware_update`."
            ),
            "content": {"application/json": {"example": {"detail": "Comando desconocido: foo"}}},
        },
        **UNAUTHORIZED,
        **FORBIDDEN_ADMIN_ONLY,
        **PYDANTIC_VALIDATION,
    },
)
async def send_command(
    vest_id: UUID,
    request: SendCommandRequest,
    _: Annotated[TokenPayload, Depends(require_admin)],
    service: Annotated[IVestCommandService, Depends(get_command_service)],
) -> dict:
    try:
        await service.handle_send_vest_command(
            SendVestCommand(
                device_id=vest_id,
                command_type=request.command_type,
                firmware_version=request.firmware_version,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "queued"}


@router.get(
    "/me",
    response_model=VestResponse,
    summary="Obtener mi chaleco vinculado",
    responses={200: {"description": "Datos del chaleco vinculado al usuario actual."}, **UNAUTHORIZED, **NOT_FOUND_VEST},
)
async def get_my_vest(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IVestQueryService, Depends(get_query_service)],
) -> VestResponse:
    device = await service.handle_get_my_vest(GetMyVestQuery(user_id=current.user_id))
    if device is None:
        raise HTTPException(status_code=404, detail="No tienes un chaleco vinculado")
    return _to_response(device)


@router.post(
    "/{vest_id}/unlink",
    response_model=VestResponse,
    summary="Desvincular mi chaleco",
    responses={
        200: {
            "description": (
                "Chaleco desvinculado. Las lecturas históricas se conservan "
                "asociadas al usuario (AC1)."
            )
        },
        403: {
            "description": "El chaleco pertenece a otro usuario.",
            "content": {
                "application/json": {
                    "example": {"detail": "El chaleco no pertenece al usuario actual"}
                }
            },
        },
        404: {
            "description": "El chaleco no existe en el sistema.",
            "content": {"application/json": {"example": {"detail": "Chaleco no encontrado"}}},
        },
        **UNAUTHORIZED,
    },
)
async def unlink_vest(
    vest_id: UUID,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IVestCommandService, Depends(get_command_service)],
) -> VestResponse:
    """Desvincula el chaleco del usuario actual. Solo el dueño puede ejecutarlo."""
    try:
        device = await service.handle_unlink_vest(
            UnlinkVestCommand(vest_id=vest_id, user_id=current.user_id)
        )
    except ValueError as exc:
        msg = str(exc)
        if "no pertenece" in msg.lower():
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=404, detail=msg)
    return _to_response(device)
