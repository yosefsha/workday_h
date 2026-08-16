"""Normalizing the identifiers that link the two feeds.

The feeds share no candidate ID and the LinkedIn feed carries no name, so a
normalized email or phone number is the only thing that connects them.
"""

from __future__ import annotations

_DIGITS = frozenset("0123456789")


def email_key(value: str | None) -> str | None:
    """Trimmed and lowercased. `Heisenberg@hotmail.com` must match itself."""
    if not value:
        return None
    key = value.strip().lower()
    return key or None


def phone_key(value: str | None) -> str | None:
    """Digits only.

    The feeds format the same number four different ways: `123-456-7890`,
    `(999) 888-777`, `5555555555`. Stripping to digits is what makes them
    comparable.
    """
    if not value:
        return None
    digits = "".join(character for character in value if character in _DIGITS)
    return digits or None
