from dataclasses import dataclass


@dataclass(frozen=True)
class ResetPasswordCommand:
    token: str
    new_password: str


class InvalidResetTokenError(Exception):
    """HU-27 — el token de recuperación es inválido, expiró o ya se usó."""
