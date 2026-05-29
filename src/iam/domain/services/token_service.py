from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from ..value_objects.role import Role
from ..value_objects.token_pair import TokenPair


@dataclass(frozen=True)
class TokenPayload:
    user_id: UUID
    role: Role
    type: str  # "access" | "refresh"


class TokenService(Protocol):
    def issue(self, user_id: UUID, role: Role) -> TokenPair: ...
    def verify(self, token: str) -> TokenPayload: ...
    def refresh(self, refresh_token: str) -> TokenPair: ...
