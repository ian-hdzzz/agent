"""
PACO CLI configuration.

Manages API URL, credential storage, and token persistence.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PACO_DIR = Path.home() / ".paco"
CREDENTIALS_FILE = PACO_DIR / "credentials.json"
DEFAULT_API_URL = "http://localhost:8000/api"


def get_api_url() -> str:
    """Return the PACO API base URL from config or default."""
    config = _load_config()
    return config.get("api_url", DEFAULT_API_URL)


def set_api_url(url: str) -> None:
    """Persist a custom API URL."""
    config = _load_config()
    config["api_url"] = url.rstrip("/")
    _save_config(config)


def save_credentials(
    access_token: str,
    expires_at: str,
    email: str,
    name: str,
    role: str,
) -> None:
    """Store JWT credentials to ~/.paco/credentials.json."""
    PACO_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "access_token": access_token,
        "expires_at": expires_at,
        "email": email,
        "name": name,
        "role": role,
    }
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2))


def load_credentials() -> Optional[dict]:
    """Load stored credentials. Returns None if missing or expired."""
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        data = json.loads(CREDENTIALS_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    expires_at = data.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                return None
        except ValueError:
            pass

    return data


def get_token() -> Optional[str]:
    """Return the stored access token, or None."""
    creds = load_credentials()
    return creds["access_token"] if creds else None


def clear_credentials() -> None:
    """Remove stored credentials."""
    if CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.unlink()


def _load_config() -> dict:
    config_file = PACO_DIR / "config.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(config: dict) -> None:
    PACO_DIR.mkdir(parents=True, exist_ok=True)
    config_file = PACO_DIR / "config.json"
    config_file.write_text(json.dumps(config, indent=2))
