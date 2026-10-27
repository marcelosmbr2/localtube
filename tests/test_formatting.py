from datetime import datetime

from localtube.core.formatting import (
    fmt_clock,
    fmt_day,
    fmt_duration,
    fmt_relative,
    fmt_size,
    fmt_speed,
    fmt_upload_date,
    parse_clock,
    plural,
)


def test_fmt_size_uses_decimal_comma():
    assert fmt_size(2_410_000_000) == "2,41 GB"
    assert fmt_size(412_000_000) == "412 MB"
    assert fmt_size(21_400_000) == "21,4 MB"
    assert fmt_size(5_000) == "5 KB"
    assert fmt_size(None) == "—"


def test_fmt_speed():
    assert fmt_speed(8_400_000) == "8,4 MB/s"


def test_durations_and_clock():
    assert fmt_duration(1122) == "18:42"
    assert fmt_duration(4113) == "1:08:33"
    assert fmt_clock(1122) == "00:18:42"
    assert parse_clock("00:18:42") == 1122
    assert parse_clock("1:02") == 62
    assert parse_clock("aa:bb") is None


def test_dates():
    assert fmt_upload_date("20260912") == "12 set. 2026"
    assert fmt_upload_date(None) == ""
    now = datetime(2026, 10, 27, 15, 0).timestamp()
    assert fmt_day(datetime(2026, 10, 27, 10, 42).timestamp(), now) == "Hoje, 10:42"
    assert fmt_day(datetime(2026, 10, 26, 22, 0).timestamp(), now) == "Ontem"
    assert fmt_day(datetime(2026, 10, 23, 9, 0).timestamp(), now) == "23 out."
    assert fmt_day(datetime(2025, 10, 23, 9, 0).timestamp(), now) == "23 out. 2025"
    assert fmt_relative(now - 30, now) == "Agora mesmo"
    assert fmt_relative(now - 7200, now) == "há 2 h"


def test_plural():
    assert plural(1, "arquivo") == "1 arquivo"
    assert plural(3, "arquivo") == "3 arquivos"
