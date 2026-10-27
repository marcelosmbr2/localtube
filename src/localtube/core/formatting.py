"""Formatação de tamanhos, durações e datas em pt-BR (vírgula decimal)."""

import time
from datetime import datetime, timedelta

MONTHS = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]


def _dec(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def fmt_size(num_bytes: float | None) -> str:
    if not num_bytes:
        return "—"
    mb = num_bytes / 1_000_000
    if mb >= 1000:
        return _dec(mb / 1000, 2) + " GB"
    if mb >= 100:
        return f"{round(mb)} MB"
    if mb >= 0.1:
        return _dec(mb, 1) + " MB"
    return f"{max(1, round(num_bytes / 1000))} KB"


def fmt_speed(bytes_per_s: float | None) -> str:
    return _dec((bytes_per_s or 0) / 1_000_000, 1) + " MB/s"


def fmt_duration(seconds: float | None) -> str:
    """18:42 ou 1:08:33."""
    if seconds is None:
        return "—"
    s = max(0, round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_clock(seconds: float | None) -> str:
    """00:18:42, usado nos campos de intervalo."""
    s = max(0, round(seconds or 0))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def parse_clock(text: str) -> int | None:
    parts = text.strip().split(":")
    if not parts or not all(p.isdigit() for p in parts) or len(parts) > 3:
        return None
    total = 0
    for p in parts:
        total = total * 60 + int(p)
    return total


def fmt_upload_date(yyyymmdd: str | None) -> str:
    if not yyyymmdd or len(yyyymmdd) != 8 or not yyyymmdd.isdigit():
        return ""
    return f"{int(yyyymmdd[6:])} {MONTHS[int(yyyymmdd[4:6]) - 1]} {yyyymmdd[:4]}"


def fmt_day(ts: float, now: float | None = None) -> str:
    """Hoje, 10:42 · Ontem · 23 out. · 23 out. 2025."""
    when = datetime.fromtimestamp(ts)
    today = datetime.fromtimestamp(now if now is not None else time.time()).date()
    if when.date() == today:
        return f"Hoje, {when:%H:%M}"
    if when.date() == today - timedelta(days=1):
        return "Ontem"
    label = f"{when.day} {MONTHS[when.month - 1]}"
    return label if when.year == today.year else f"{label} {when.year}"


def fmt_relative(ts: float, now: float | None = None) -> str:
    """Agora mesmo · há 12 min · há 2 h · Ontem · 24 out."""
    now = now if now is not None else time.time()
    delta = now - ts
    if delta < 60:
        return "Agora mesmo"
    if delta < 3600:
        return f"há {int(delta // 60)} min"
    if datetime.fromtimestamp(ts).date() == datetime.fromtimestamp(now).date():
        return f"há {int(delta // 3600)} h"
    return fmt_day(ts, now)


def plural(n: int, singular: str, plural_form: str | None = None) -> str:
    return f"{n} {singular if n == 1 else (plural_form or singular + 's')}"
