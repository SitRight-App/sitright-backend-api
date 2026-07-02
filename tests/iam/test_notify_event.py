from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from src.iam.application.internal.commandservices.user_command_service import (
    UserCommandService,
)
from src.iam.domain.entities.notification import NotificationChannel, NotificationType
from src.iam.domain.entities.user import User
from src.iam.domain.model.commands.notify_event_command import (
    InvalidNotificationEventError,
    NotifyEventCommand,
)
from src.iam.domain.value_objects.preferences import Preferences
from src.iam.domain.value_objects.role import Role

NOW = datetime(2026, 7, 1, 12, 0, 0)


class _UserRepo:
    def __init__(self, users):
        self._by_id = {u.id: u for u in users}

    async def find_by_id(self, uid):
        return self._by_id.get(uid)

    async def save(self, user):
        self._by_id[user.id] = user


class _NotificationRepo:
    def __init__(self):
        self.saved = []

    async def save(self, notification):
        self.saved.append(notification)

    async def find_latest_by_type(self, user_id, type_):
        matches = [
            n for n in self.saved if n.user_id == user_id and n.type == type_
        ]
        if not matches:
            return None
        return max(matches, key=lambda n: n.sent_at)


class _Email:
    def __init__(self):
        self.posture_alerts = []
        self.break_reminders = []

    async def send_posture_alert(self, to_email, to_name):
        self.posture_alerts.append((to_email, to_name))

    async def send_break_reminder(self, to_email, to_name):
        self.break_reminders.append((to_email, to_name))


def _user(**kw) -> User:
    base = dict(
        id=uuid4(), name="Ana", email="ana@correo.com", password_hash="hashed:old",
        role=Role.WORKER, created_at=NOW, updated_at=NOW, is_active=True,
    )
    base.update(kw)
    return User(**base)


def _service(users):
    user_repo = _UserRepo(users)
    notif_repo = _NotificationRepo()
    email = _Email()
    svc = UserCommandService(
        user_repository=user_repo,
        notification_repository=notif_repo,
        password_service=None,
        token_service=None,
        reset_token_repository=None,
        email_service=email,
        app_base_url="https://app.test",
        reset_token_ttl_seconds=3600,
    )
    return svc, user_repo, notif_repo, email


async def test_alerta_postura_con_email_activado_guarda_y_envia_correo():
    user = _user(preferences=Preferences(email_notifications=True))
    svc, _ur, notif_repo, email = _service([user])
    await svc.handle_notify_event(
        NotifyEventCommand(user_id=user.id, event_type="bad_posture_alert")
    )
    assert len(notif_repo.saved) == 1
    saved = notif_repo.saved[0]
    assert saved.type == NotificationType.BAD_POSTURE_ALERT
    assert saved.channel == NotificationChannel.EMAIL
    assert email.posture_alerts == [(user.email, user.name)]


async def test_email_desactivado_guarda_in_app_y_no_envia_correo():
    user = _user(preferences=Preferences(email_notifications=False))
    svc, _ur, notif_repo, email = _service([user])
    await svc.handle_notify_event(
        NotifyEventCommand(user_id=user.id, event_type="break_reminder")
    )
    assert len(notif_repo.saved) == 1
    saved = notif_repo.saved[0]
    assert saved.type == NotificationType.BREAK_REMINDER
    assert saved.channel == NotificationChannel.IN_APP
    assert email.break_reminders == []
    assert email.posture_alerts == []


async def test_segunda_llamada_en_cooldown_no_duplica_ni_reenvia():
    user = _user(preferences=Preferences(email_notifications=True))
    svc, _ur, notif_repo, email = _service([user])
    await svc.handle_notify_event(
        NotifyEventCommand(user_id=user.id, event_type="bad_posture_alert")
    )
    await svc.handle_notify_event(
        NotifyEventCommand(user_id=user.id, event_type="bad_posture_alert")
    )
    assert len(notif_repo.saved) == 1
    assert len(email.posture_alerts) == 1


async def test_evento_invalido_lanza_error():
    user = _user()
    svc, _ur, _nr, _email = _service([user])
    with pytest.raises(InvalidNotificationEventError):
        await svc.handle_notify_event(
            NotifyEventCommand(user_id=user.id, event_type="no_existe")
        )


async def test_usuario_inexistente_es_no_op():
    svc, _ur, notif_repo, email = _service([])
    await svc.handle_notify_event(
        NotifyEventCommand(user_id=uuid4(), event_type="bad_posture_alert")
    )
    assert notif_repo.saved == []
    assert email.posture_alerts == []
