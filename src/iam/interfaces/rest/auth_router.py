from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ...domain.model.commands.login_command import (
    InactiveAccountError,
    InvalidCredentialsError,
    LoginCommand,
)
from ...domain.model.commands.refresh_token_command import RefreshTokenCommand
from ...domain.model.commands.register_user_command import (
    RegisterUserCommand,
    UserAlreadyExistsError,
)
from ...domain.model.commands.request_password_reset_command import (
    RequestPasswordResetCommand,
)
from ...domain.services.token_service import TokenPayload
from ...domain.services.user_command_service import IUserCommandService
from ...domain.value_objects.role import Role
from ..schemas.auth_schema import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from ..schemas.user_schema import (
    AnthropometricSchema,
    PreferencesSchema,
    UserResponse,
)
from .dependencies import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["iam"])

# Inyección manual del servicio en lugar de un container — alineado con la
# convención simple del proyecto.
_user_command_service: IUserCommandService | None = None


def set_user_command_service(service: IUserCommandService) -> None:
    global _user_command_service
    _user_command_service = service


def get_user_command_service() -> IUserCommandService:
    if _user_command_service is None:
        raise RuntimeError("UserCommandService no inicializado")
    return _user_command_service


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


@router.post("/register", status_code=201, response_model=UserResponse)
async def register(
    request: RegisterRequest,
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> UserResponse:
    try:
        role = Role(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Rol inválido")
    command = RegisterUserCommand(
        name=request.name,
        email=request.email,
        plain_password=request.password,
        role=role,
        weight_kg=request.weight_kg,
        height_cm=request.height_cm,
    )
    try:
        user = await service.handle_register(command)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> TokenResponse:
    command = LoginCommand(email=request.email, plain_password=request.password)
    try:
        _, tokens = await service.handle_login(command)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except InactiveAccountError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )


@router.post("/forgot-password", status_code=202)
async def forgot_password(
    request: ForgotPasswordRequest,
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> dict:
    """HU-27 — solicitar recuperación de contraseña.

    Responde siempre el mismo mensaje genérico para no permitir enumeración
    de cuentas (AC2). Si la cuenta existe, internamente queda registrado
    para que un servicio de correo envíe el enlace (TTL 1 h, AC3).
    """
    await service.handle_request_password_reset(
        RequestPasswordResetCommand(email=request.email)
    )
    return {"message": "Te hemos enviado las instrucciones por correo"}


@router.post("/logout", status_code=204)
async def logout(
    _: Annotated[TokenPayload, Depends(get_current_user)],
) -> Response:
    """HU-25 AC1 — cierre de sesión.

    Los JWT son stateless: el "invalidar token" lo materializa el cliente
    descartando los tokens locales. El endpoint registra la intención del
    cierre (204) y permite que el frontend lo invoque de forma uniforme.
    """
    return Response(status_code=204)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshTokenRequest,
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> TokenResponse:
    try:
        tokens = await service.handle_refresh_token(
            RefreshTokenCommand(refresh_token=request.refresh_token)
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token inválido: {exc}")
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )
