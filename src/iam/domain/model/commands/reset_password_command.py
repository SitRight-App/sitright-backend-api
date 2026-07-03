from dataclasses import dataclass


@dataclass(frozen=True)
class ResetPasswordCommand:
    token: str
    new_password: str


class InvalidResetTokenError(Exception):
    """El token de recuperación es inválido, expiró o ya se usó."""
