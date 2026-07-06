from datetime import datetime, timedelta

from src.shared.datetime_utils import ensure_utc, now_utc, parse_utc


def test_parse_una_marca_sin_zona_se_asume_utc():
    d = parse_utc("2026-07-04T20:30:00")
    assert d.tzinfo is not None
    assert d.utcoffset() == timedelta(0)


def test_parse_respeta_la_zona_existente():
    assert parse_utc("2026-07-04T15:30:00-05:00") == parse_utc("2026-07-04T20:30:00")


def test_now_utc_es_aware():
    assert now_utc().tzinfo is not None


def test_ensure_utc_normaliza_naive_a_utc():
    assert ensure_utc(datetime(2026, 7, 4, 20, 30, 0)).utcoffset() == timedelta(0)
