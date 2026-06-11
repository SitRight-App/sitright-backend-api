"""Tests del tope de jornada (ADR-007): una sesión olvidada se autocierra.

Sin I/O: repo de sesiones y agregador en memoria.
"""
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from src.session_history.application.internal.commandservices.session_command_service import (
    SessionCommandService,
)
from src.session_history.domain.entities.posture_session import PostureSession
from src.session_history.domain.model.commands.start_session_command import (
    StartSessionCommand,
)
from src.session_history.domain.value_objects.session_summary import SessionSummary


class _FakeSessionRepo:
    def __init__(self) -> None:
        self.sessions: dict[UUID, PostureSession] = {}

    async def find_active_by_user(self, user_id: UUID) -> PostureSession | None:
        for s in self.sessions.values():
            if s.user_id == user_id and s.is_active():
                return s
        return None

    async def find_by_id(self, session_id: UUID) -> PostureSession | None:
        return self.sessions.get(session_id)

    async def save(self, session: PostureSession) -> None:
        self.sessions[session.id] = session


class _FakeAggregator:
    def __init__(self, last_ts: datetime | None = None) -> None:
        self._last = last_ts

    async def aggregate_for_session(self, session_id: UUID) -> SessionSummary:
        return SessionSummary(
            total_readings=0,
            valid_readings=0,
            adequate_percentage=0.0,
            dominant_deviation=None,
            total_minutes=0.0,
            counts_by_class={},
        )

    async def last_reading_at(self, session_id: UUID) -> datetime | None:
        return self._last


def _svc(last_ts: datetime | None = None) -> tuple[SessionCommandService, _FakeSessionRepo]:
    repo = _FakeSessionRepo()
    return SessionCommandService(session_repository=repo, readings_aggregator=_FakeAggregator(last_ts)), repo


def _cmd(uid: UUID, vid: UUID) -> StartSessionCommand:
    return StartSessionCommand(user_id=uid, vest_device_id=vid)


async def test_idempotente_dentro_del_tope():
    svc, _ = _svc()
    uid, vid = uuid4(), uuid4()
    s1 = await svc.handle_start_session(_cmd(uid, vid))
    s2 = await svc.handle_start_session(_cmd(uid, vid))
    assert s1.id == s2.id  # misma sesión activa


async def test_sesion_excedida_se_autocierra_en_la_ultima_lectura():
    last = datetime(2026, 6, 6, 17, 0, 0)
    svc, repo = _svc(last_ts=last)
    uid, vid = uuid4(), uuid4()
    old = PostureSession(
        id=uuid4(), user_id=uid, vest_device_id=vid,
        started_at=datetime.utcnow() - timedelta(hours=72),  # abierta desde hace 3 días
    )
    await repo.save(old)

    new = await svc.handle_start_session(_cmd(uid, vid))

    closed = repo.sessions[old.id]
    assert not closed.is_active()         # la vieja se cerró
    assert closed.ended_at == last        # en la hora de la última lectura real
    assert new.id != old.id and new.is_active()  # y arrancó una nueva


async def test_excedida_sin_lecturas_cierra_en_started_at():
    svc, repo = _svc(last_ts=None)
    uid, vid = uuid4(), uuid4()
    started = datetime.utcnow() - timedelta(hours=20)
    old = PostureSession(id=uuid4(), user_id=uid, vest_device_id=vid, started_at=started)
    await repo.save(old)

    new = await svc.handle_start_session(_cmd(uid, vid))

    closed = repo.sessions[old.id]
    assert not closed.is_active()
    assert closed.ended_at == started
    assert new.id != old.id
