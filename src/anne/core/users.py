"""V1 demo user identifiers — deterministic, password-free, non-auth.

Code names are recognition keys only. Display names are used in greetings.
Memory isolation uses stable user_id. This is not an account system.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserIdentity:
    """Resolved session identity for V1 demo / open actors."""

    user_id: str
    display_name: str
    code_name: str
    is_demo: bool
    greeting: str


_DEMO: dict[str, tuple[str, str]] = {
    "dönerci mıstık": ("mustafa", "Mustafa Bey"),
    "donerci mistik": ("mustafa", "Mustafa Bey"),
    "dönerci mistik": ("mustafa", "Mustafa Bey"),
    "donerci mıstık": ("mustafa", "Mustafa Bey"),
    "gügü baba": ("gurhan", "Gürhan Bey"),
    "gugu baba": ("gurhan", "Gürhan Bey"),
    "gügu baba": ("gurhan", "Gürhan Bey"),
    "gugü baba": ("gurhan", "Gürhan Bey"),
}


def _normalize(raw: str) -> str:
    return " ".join(raw.strip().casefold().split())


def resolve_user(actor: str) -> UserIdentity:
    """Map actor string to a stable user_id and display hitap.

    Unknown actors keep their own isolated bucket (user_id = normalized actor).
    """
    normalized = _normalize(actor) or "anonymous"
    if normalized in _DEMO:
        user_id, display = _DEMO[normalized]
        return UserIdentity(
            user_id=user_id,
            display_name=display,
            code_name=actor.strip(),
            is_demo=True,
            greeting=f"Hoş geldiniz {display}. Nasıl yardımcı olabilirim?",
        )
    display = actor.strip() or "Misafir"
    return UserIdentity(
        user_id=f"actor:{normalized}",
        display_name=display,
        code_name=actor.strip(),
        is_demo=False,
        greeting="",
    )


__all__ = ["UserIdentity", "resolve_user"]
