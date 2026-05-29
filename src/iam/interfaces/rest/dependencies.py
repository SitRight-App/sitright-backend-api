from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException

from ...domain.services.token_service import TokenPayload, TokenService
from ...domain.value_objects.role import Role


_token_service: TokenService | None = None


def set_token_service(service: TokenService) -> None:
    global _token_service
    _token_service = service


def get_token_service() -> TokenService:
    if _token_service is None:
        raise RuntimeError("TokenService no inicializado")
    return _token_service


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    token_service: Annotated[TokenService, Depends(get_token_service)] = None,
) -> TokenPayload:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta header Authorization Bearer")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = token_service.verify(token)
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
