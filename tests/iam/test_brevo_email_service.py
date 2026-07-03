import logging
from dataclasses import dataclass

import pytest

from src.iam.infrastructure.email.brevo_email_service import BrevoEmailService


@dataclass
class _Cfg:
    brevo_smtp_host: str = "smtp-relay.brevo.com"
    brevo_smtp_port: int = 587
    brevo_smtp_user: str = ""
    brevo_smtp_key: str = ""
    email_sender_name: str = "SitRight"
    email_sender_address: str = ""


LINK = "https://sitright-web-client.netlify.app/reset-password?token=abc"


def test_build_message_incluye_remitente_destino_y_enlace():
    svc = BrevoEmailService(_Cfg(email_sender_address="no-reply@sitright.app"))
    msg = svc._build_message("u@correo.com", "Ana", LINK)
    assert msg["From"] == "SitRight <no-reply@sitright.app>"
    assert "u@correo.com" in msg["To"]
    html = msg.get_body(preferencelist=("html",))
    assert html is not None
    # El enlace debe estar en el contenido HTML decodificado (as_string() lo
    # parte con saltos suaves quoted-printable ahora que el cuerpo tiene tildes).
    assert LINK in html.get_content()


async def test_modo_dev_loguea_el_enlace_si_no_hay_credenciales(caplog):
    svc = BrevoEmailService(_Cfg())  # sin user/key/sender -> modo dev
    with caplog.at_level(logging.INFO):
        await svc.send_password_reset("u@correo.com", "Ana", LINK)
    assert any(LINK in r.message for r in caplog.records)
