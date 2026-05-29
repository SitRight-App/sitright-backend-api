from dataclasses import dataclass


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
