from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...domain.services.token_service import TokenPayload, TokenService
from ...domain.value_objects.role import Role

# Esquema declarado para que Swagger UI muestre el botón "Authorize" y
# permita pegar el access_token una sola vez por sesión del navegador.
_bearer_scheme = HTTPBearer(
    bearerFormat="JWT",
    description="Pegar aquí el `access_token` devuelto por /api/v1/auth/login.",
    auto_error=False,
)

_token_service: TokenService | None = None


def set_token_service(service: TokenService) -> None:
    global _token_service
    _token_service = service


def get_token_service() -> TokenService:
    if _token_service is None:
        raise RuntimeError("TokenService no inicializado")
    return _token_service


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ] = None,
    token_service: Annotated[TokenService, Depends(get_token_service)] = None,
) -> TokenPayload:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Falta header Authorization Bearer")
    try:
        payload = token_service.verify(credentials.credentials)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token inválido: {exc}")
    if payload.type != "access":
        raise HTTPException(status_code=401, detail="Se requiere un access token")
    return payload


async def require_admin(
    current: Annotated[TokenPayload, Depends(get_current_user)],
) -> TokenPayload:
    if current.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Se requiere rol administrador")
    return current
