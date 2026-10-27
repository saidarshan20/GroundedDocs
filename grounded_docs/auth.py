"""Password verification for the three synthetic demo accounts."""

from __future__ import annotations

import tomllib
from pathlib import Path

USERS = ("guest", "alice", "bob")


def demo_hashes(root: Path, cloud_secrets: object) -> dict[str, str]:
    """Prefer this project's local secrets, regardless of Streamlit's launch folder."""
    local_path = root / ".streamlit" / "secrets.toml"
    if local_path.is_file():
        try:
            users = tomllib.loads(local_path.read_text(encoding="utf-8"))["users"]
        except (OSError, ValueError, KeyError) as exc:
            raise ValueError("Project-local demo secrets are missing or invalid.") from exc
    else:
        try:
            users = cloud_secrets["users"]
        except (KeyError, TypeError) as exc:
            raise ValueError("Demo account secrets are not configured.") from exc
    hashes = dict(users)
    if any(not isinstance(hashes.get(f"{user}_hash"), str) for user in USERS):
        raise ValueError("Demo account secrets are incomplete.")
    return hashes


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
