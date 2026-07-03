import logging
from dataclasses import dataclass

import pytest

from src.iam.infrastructure.email.brevo_email_service import BrevoEmailService


@dataclass
class _Cfg:
    brevo_api_key: str = ""
    email_sender_name: str = "SitRight"
    email_sender_address: str = ""


LINK = "https://sitright-web-client.netlify.app/reset-password?token=abc"


def test_build_message_incluye_asunto_texto_y_enlace():
    svc = BrevoEmailService(_Cfg())
    subject, text, html = svc._build_message("Ana", LINK)
    assert "SitRight" in subject
    assert LINK in text
    assert LINK in html


async def test_modo_dev_loguea_el_enlace_si_no_hay_credenciales(caplog):
    svc = BrevoEmailService(_Cfg())  # sin api_key/sender -> modo dev
    with caplog.at_level(logging.INFO):
        await svc.send_password_reset("u@correo.com", "Ana", LINK)
    assert any(LINK in r.message for r in caplog.records)
