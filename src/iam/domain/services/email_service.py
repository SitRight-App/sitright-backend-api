from typing import Protocol


class EmailService(Protocol):
    async def send_password_reset(
        self, to_email: str, to_name: str, reset_link: str
    ) -> None: ...

    async def send_password_changed(self, to_email: str, to_name: str) -> None: ...
