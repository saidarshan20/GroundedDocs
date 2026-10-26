"""Password verification for the three synthetic demo accounts."""

from __future__ import annotations

USERS = ("guest", "alice", "bob")


def authenticate(username: str, password: str, hashes: dict[str, str]) -> str | None:
    """Return the principal only when its stored bcrypt hash matches."""
    import bcrypt

    principal = username.strip().lower()
    if principal not in USERS or not password:
        return None
    stored = hashes.get(f"{principal}_hash")
    if not stored:
        return None
    try:
        return principal if bcrypt.checkpw(password.encode(), stored.encode()) else None
    except ValueError:
        return None
