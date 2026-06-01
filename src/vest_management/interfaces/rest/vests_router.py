from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user, require_admin
from ...application.commands.calibrate_vest_handler import (
    CalibrateVestCommand,
    CalibrateVestHandler,
)
from ...application.commands.link_vest_handler import (
    LinkVestCommand,
    LinkVestHandler,
)
from ...application.commands.register_vest_handler import (
    RegisterVestCommand,
    RegisterVestHandler,
)
from ...application.commands.send_command_handler import (
    SendVestCommand,
    SendVestCommandHandler,
)
from ...application.commands.unlink_vest_handler import (
    UnlinkVestCommand,
    UnlinkVestHandler,
)
from ...application.queries.get_my_vest_handler import (
    GetMyVestHandler,
    GetMyVestQuery,
)
from ...domain.entities.vest_device import VestDevice
from ..schemas.vest_schema import (
    CalibrateVestRequest,
    LinkVestRequest,
    LinkVestResponse,
    RegisterVestRequest,
    SendCommandRequest,
    VestResponse,
)

router = APIRouter(prefix="/api/v1/vests", tags=["vest_management"])

_register_handler: RegisterVestHandler | None = None
_link_handler: LinkVestHandler | None = None
_calibrate_handler: CalibrateVestHandler | None = None
_send_command_handler: SendVestCommandHandler | None = None
_get_my_vest_handler: GetMyVestHandler | None = None
_unlink_handler: UnlinkVestHandler | None = None


def set_register_handler(h: RegisterVestHandler) -> None:
    global _register_handler
    _register_handler = h


def set_link_handler(h: LinkVestHandler) -> None:
    global _link_handler
    _link_handler = h


def set_calibrate_handler(h: CalibrateVestHandler) -> None:
    global _calibrate_handler
    _calibrate_handler = h


def set_send_command_handler(h: SendVestCommandHandler) -> None:
    global _send_command_handler
    _send_command_handler = h


def set_get_my_vest_handler(h: GetMyVestHandler) -> None:
    global _get_my_vest_handler
    _get_my_vest_handler = h


def set_unlink_handler(h: UnlinkVestHandler) -> None:
    global _unlink_handler
    _unlink_handler = h


def get_register_handler() -> RegisterVestHandler:
    if _register_handler is None:
        raise RuntimeError("RegisterVestHandler no inicializado")
    return _register_handler


def get_link_handler() -> LinkVestHandler:
    if _link_handler is None:
        raise RuntimeError("LinkVestHandler no inicializado")
    return _link_handler


def get_calibrate_handler() -> CalibrateVestHandler:
    if _calibrate_handler is None:
        raise RuntimeError("CalibrateVestHandler no inicializado")
    return _calibrate_handler


def get_send_command_handler() -> SendVestCommandHandler:
    if _send_command_handler is None:
        raise RuntimeError("SendVestCommandHandler no inicializado")
    return _send_command_handler


def get_get_my_vest_handler() -> GetMyVestHandler:
    if _get_my_vest_handler is None:
        raise RuntimeError("GetMyVestHandler no inicializado")
    return _get_my_vest_handler


def get_unlink_handler() -> UnlinkVestHandler:
    if _unlink_handler is None:
        raise RuntimeError("UnlinkVestHandler no inicializado")
    return _unlink_handler


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


@router.post("/register", status_code=201, response_model=VestResponse)
async def register_vest(
    request: RegisterVestRequest,
    _: Annotated[TokenPayload, Depends(require_admin)],
    handler: Annotated[RegisterVestHandler, Depends(get_register_handler)],
) -> VestResponse:
    try:
        device = await handler.execute(
            RegisterVestCommand(
                mac_address=request.mac_address,
                firmware_version=request.firmware_version,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_response(device)


@router.post("/link", response_model=LinkVestResponse)
async def link_vest(
    request: LinkVestRequest,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[LinkVestHandler, Depends(get_link_handler)],
) -> LinkVestResponse:
    try:
        device, plain_password = await handler.execute(
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


@router.post("/{vest_id}/calibrate", response_model=VestResponse)
async def calibrate_vest(
    vest_id: UUID,
    request: CalibrateVestRequest,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[CalibrateVestHandler, Depends(get_calibrate_handler)],
) -> VestResponse:
    try:
        device = await handler.execute(
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


@router.post("/{vest_id}/commands", status_code=202)
async def send_command(
    vest_id: UUID,
    request: SendCommandRequest,
    _: Annotated[TokenPayload, Depends(require_admin)],
    handler: Annotated[SendVestCommandHandler, Depends(get_send_command_handler)],
) -> dict:
    try:
        await handler.execute(
            SendVestCommand(
                device_id=vest_id,
                command_type=request.command_type,
                firmware_version=request.firmware_version,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "queued"}


@router.get("/me", response_model=VestResponse)
async def get_my_vest(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[GetMyVestHandler, Depends(get_get_my_vest_handler)],
) -> VestResponse:
    device = await handler.execute(GetMyVestQuery(user_id=current.user_id))
    if device is None:
        raise HTTPException(status_code=404, detail="No tienes un chaleco vinculado")
    return _to_response(device)


@router.post("/{vest_id}/unlink", response_model=VestResponse)
async def unlink_vest(
    vest_id: UUID,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[UnlinkVestHandler, Depends(get_unlink_handler)],
) -> VestResponse:
    """Desvincula el chaleco del usuario actual. Solo el dueño puede ejecutarlo."""
    try:
        device = await handler.execute(
            UnlinkVestCommand(vest_id=vest_id, user_id=current.user_id)
        )
    except ValueError as exc:
        msg = str(exc)
        if "no pertenece" in msg.lower():
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=404, detail=msg)
    return _to_response(device)
