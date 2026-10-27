from pathlib import Path

import bcrypt
import pytest

from grounded_docs.auth import authenticate, demo_hashes


def test_project_local_hashes_override_other_streamlit_secrets(tmp_path: Path):
    secrets_dir = tmp_path / ".streamlit"
    secrets_dir.mkdir()
    passwords = {"guest": "guest-demo-2026", "alice": "alice-demo-2026", "bob": "bob-demo-2026"}
    lines = ["[users]"]
    for user, password in passwords.items():
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        lines.append(f'{user}_hash = "{hashed}"')
    (secrets_dir / "secrets.toml").write_text("\n".join(lines), encoding="utf-8")

    other_secrets = {"users": {f"{user}_hash": "wrong" for user in passwords}}
    hashes = demo_hashes(tmp_path, other_secrets)
    assert all(authenticate(user, password, hashes) == user for user, password in passwords.items())


def test_cloud_hashes_used_when_no_local_file(tmp_path: Path):
    hashed = bcrypt.hashpw(b"guest-demo-2026", bcrypt.gensalt()).decode()
    secrets = {"users": {"guest_hash": hashed, "alice_hash": "placeholder", "bob_hash": "placeholder"}}
    assert authenticate("guest", "guest-demo-2026", demo_hashes(tmp_path, secrets)) == "guest"


def test_missing_demo_secrets_report_configuration_error(tmp_path: Path):
    with pytest.raises(ValueError, match="not configured"):
        demo_hashes(tmp_path, {})
