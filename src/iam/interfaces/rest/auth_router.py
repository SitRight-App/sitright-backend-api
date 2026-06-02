from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ...domain.services.token_service import TokenPayload
from .dependencies import get_current_user

from ...application.commands.login_handler import (
    InactiveAccountError,
    InvalidCredentialsError,
    LoginCommand,
    LoginHandler,
)
from ...application.commands.refresh_token_handler import (
    RefreshTokenCommand,
    RefreshTokenHandler,
)
from ...application.commands.register_user_handler import (
    RegisterUserCommand,
    RegisterUserHandler,
)
from ...application.commands.request_password_reset_handler import (
    RequestPasswordResetCommand,
    RequestPasswordResetHandler,
)
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

router = APIRouter(prefix="/api/v1/auth", tags=["iam"])

_register_handler: RegisterUserHandler | None = None
_login_handler: LoginHandler | None = None
_refresh_handler: RefreshTokenHandler | None = None
_forgot_password_handler: RequestPasswordResetHandler | None = None


def set_register_handler(handler: RegisterUserHandler) -> None:
    global _register_handler
    _register_handler = handler


def set_login_handler(handler: LoginHandler) -> None:
    global _login_handler
    _login_handler = handler


def set_refresh_handler(handler: RefreshTokenHandler) -> None:
    global _refresh_handler
    _refresh_handler = handler


def set_forgot_password_handler(handler: RequestPasswordResetHandler) -> None:
    global _forgot_password_handler
    _forgot_password_handler = handler


def get_register_handler() -> RegisterUserHandler:
    if _register_handler is None:
        raise RuntimeError("RegisterUserHandler no inicializado")
    return _register_handler


def get_forgot_password_handler() -> RequestPasswordResetHandler:
    if _forgot_password_handler is None:
        raise RuntimeError("RequestPasswordResetHandler no inicializado")
    return _forgot_password_handler


def get_login_handler() -> LoginHandler:
    if _login_handler is None:
        raise RuntimeError("LoginHandler no inicializado")
    return _login_handler


def get_refresh_handler() -> RefreshTokenHandler:
    if _refresh_handler is None:
        raise RuntimeError("RefreshTokenHandler no inicializado")
    return _refresh_handler


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
    handler: Annotated[RegisterUserHandler, Depends(get_register_handler)],
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
        user = await handler.execute(command)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_user_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    handler: Annotated[LoginHandler, Depends(get_login_handler)],
) -> TokenResponse:
    command = LoginCommand(email=request.email, plain_password=request.password)
    try:
        _, tokens = await handler.execute(command)
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
    handler: Annotated[RequestPasswordResetHandler, Depends(get_forgot_password_handler)],
) -> dict:
    """HU-27 — solicitar recuperación de contraseña.

    Responde siempre el mismo mensaje genérico para no permitir enumeración
    de cuentas (AC2). Si la cuenta existe, internamente queda registrado
    para que un servicio de correo envíe el enlace (TTL 1 h, AC3).
    """
    await handler.execute(RequestPasswordResetCommand(email=request.email))
    return {
        "message": "Te hemos enviado las instrucciones por correo",
    }


@router.post("/logout", status_code=204)
async def logout(
    _: Annotated[TokenPayload, Depends(get_current_user)],
) -> Response:
    """HU-25 AC1 — cierre de sesión.

    Los JWT son stateless: el "invalidar token" lo materializa el cliente
    descartando los tokens locales. El endpoint registra la intención del
    cierre (204) y permite que el frontend lo invoque de forma uniforme
    desde cualquier pantalla.
    """
    return Response(status_code=204)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshTokenRequest,
    handler: Annotated[RefreshTokenHandler, Depends(get_refresh_handler)],
) -> TokenResponse:
    try:
        tokens = handler.execute(RefreshTokenCommand(refresh_token=request.refresh_token))
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token inválido: {exc}")
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
    )
