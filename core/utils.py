"""
Shared utilities — parsing, formatting, rate-limiting, anti-duplicate guard.
All state is module-level so it is shared across every cog.
"""
from __future__ import annotations

import re
import time
from typing import Optional

# ── In-memory rate limiter ───────────────────────────────────────────────────
_cooldowns: dict[tuple[int, str], float] = {}
_active: set[tuple[int, str]] = set()


def check_cooldown(uid: int, command: str, seconds: float) -> float:
    """Return remaining cooldown seconds, or 0.0 if the user is clear."""
    key = (uid, command)
    last = _cooldowns.get(key)
    if last is None:
        return 0.0
    remaining = seconds - (time.monotonic() - last)
    return max(0.0, remaining)


def set_cooldown(uid: int, command: str) -> None:
    _cooldowns[(uid, command)] = time.monotonic()


def is_processing(uid: int, command: str) -> bool:
    """Return True if this user is already running this command."""
    return (uid, command) in _active


def set_processing(uid: int, command: str) -> None:
    _active.add((uid, command))


def clear_processing(uid: int, command: str) -> None:
    _active.discard((uid, command))


# ── Amount parser ─────────────────────────────────────────────────────────────
def parse_amount(raw: str, balance: int) -> Optional[int]:
    """
    Convert a user-supplied string into an integer coin amount.
    Supports: plain numbers, k/m suffix, 'all', 'max', 'half'.
    Returns None on bad input.
    """
    s = raw.lower().strip().replace(",", "")

    if s in ("all", "max"):
        return balance
    if s == "half":
        return balance // 2

    match = re.fullmatch(r"([\d]+(?:\.\d+)?)([km]?)", s)
    if not match:
        return None

    num_str, suffix = match.groups()
    try:
        val = float(num_str)
        if suffix == "k":
            val *= 1_000
        elif suffix == "m":
            val *= 1_000_000
        return max(0, int(val))
    except ValueError:
        return None


# ── Formatting helpers ────────────────────────────────────────────────────────
def fmt_coins(amount: int) -> str:
    return f"🪙 {amount:,}"


def fmt_signed(amount: int) -> str:
    sign = "+" if amount >= 0 else ""
    return f"{sign}{amount:,}"


def fmt_percent(value: float) -> str:
    return f"{value:.1f}%"


def win_rate(wins: int, games: int) -> float:
    return (wins / games * 100) if games > 0 else 0.0


def rank_emoji(pos: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, f"`#{pos}`")
