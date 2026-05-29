from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from ...domain.services.token_service import TokenPayload
from ...domain.value_objects.role import Role
from ...domain.value_objects.token_pair import TokenPair


class InvalidTokenError(Exception):
    pass


class JwtTokenService:
    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        access_expires_seconds: int = 3600,
        refresh_expires_seconds: int = 1209600,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._access_expires = access_expires_seconds
        self._refresh_expires = refresh_expires_seconds

    def issue(self, user_id: UUID, role: Role) -> TokenPair:
        access = self._build_token(user_id, role, "access", self._access_expires)
        refresh = self._build_token(user_id, role, "refresh", self._refresh_expires)
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=self._access_expires,
        )

    def verify(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except JWTError as exc:
            raise InvalidTokenError(f"Token inválido: {exc}") from exc
        return TokenPayload(
            user_id=UUID(payload["sub"]),
            role=Role(payload["role"]),
            type=payload["type"],
        )

    def refresh(self, refresh_token: str) -> TokenPair:
        payload = self.verify(refresh_token)
        if payload.type != "refresh":
            raise InvalidTokenError("Se esperaba un refresh token")
        return self.issue(payload.user_id, payload.role)

    def _build_token(
        self, user_id: UUID, role: Role, token_type: str, expires_in: int
    ) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": str(user_id),
            "role": role.value,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        }
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)
