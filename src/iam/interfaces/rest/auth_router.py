from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

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
from ...domain.value_objects.role import Role
from ..schemas.auth_schema import (
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


def set_register_handler(handler: RegisterUserHandler) -> None:
    global _register_handler
    _register_handler = handler


def set_login_handler(handler: LoginHandler) -> None:
    global _login_handler
    _login_handler = handler


def set_refresh_handler(handler: RefreshTokenHandler) -> None:
    global _refresh_handler
    _refresh_handler = handler


def get_register_handler() -> RegisterUserHandler:
    if _register_handler is None:
        raise RuntimeError("RegisterUserHandler no inicializado")
    return _register_handler


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
