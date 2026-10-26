"""Create ignored local bcrypt secrets for the fictional public demo accounts."""

from pathlib import Path

import bcrypt

ROOT = Path(__file__).resolve().parents[1]
PASSWORDS = {"guest": "guest-demo-2026", "alice": "alice-demo-2026", "bob": "bob-demo-2026"}


def main() -> None:
    path = ROOT / ".streamlit" / "secrets.toml"
    if path.exists():
        raise SystemExit("Secrets already exist; remove them yourself before regenerating.")
    lines = ["[users]"]
    for user, password in PASSWORDS.items():
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        lines.append(f'{user}_hash = "{hashed}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Created ignored .streamlit/secrets.toml for the published synthetic demo accounts.")


if __name__ == "__main__":
    main()
