from dataclasses import dataclass

from ...domain.entities.user import User
from ...domain.repositories.user_repository import UserRepository
from ...domain.services.password_service import PasswordService
from ...domain.services.token_service import TokenService
from ...domain.value_objects.token_pair import TokenPair


@dataclass
class LoginCommand:
    email: str
    plain_password: str


class InvalidCredentialsError(Exception):
    pass


class InactiveAccountError(Exception):
    pass


class LoginHandler:
    def __init__(
        self,
        repo: UserRepository,
        password_service: PasswordService,
        token_service: TokenService,
    ) -> None:
        self._repo = repo
        self._password_service = password_service
        self._token_service = token_service

    async def execute(self, command: LoginCommand) -> tuple[User, TokenPair]:
        user = await self._repo.find_by_email(command.email.lower().strip())
        if user is None:
            raise InvalidCredentialsError("Email o contraseña incorrectos")
        if not self._password_service.verify(command.plain_password, user.password_hash):
            raise InvalidCredentialsError("Email o contraseña incorrectos")
        if not user.is_active:
            raise InactiveAccountError("La cuenta está desactivada")

        token_pair = self._token_service.issue(user.id, user.role)
        return user, token_pair
