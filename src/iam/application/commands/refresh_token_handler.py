from dataclasses import dataclass

from ...domain.services.token_service import TokenService
from ...domain.value_objects.token_pair import TokenPair


@dataclass
class RefreshTokenCommand:
    refresh_token: str


class RefreshTokenHandler:
    def __init__(self, token_service: TokenService) -> None:
        self._token_service = token_service

    def execute(self, command: RefreshTokenCommand) -> TokenPair:
        return self._token_service.refresh(command.refresh_token)
