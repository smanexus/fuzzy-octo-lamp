"""Runtime configuration, including the VAPID keys used for Web Push.

In production set VAPID_PRIVATE_KEY (see gen_vapid.py). For local development,
if it's absent we generate a key once and cache it in .vapid_dev.json so that
push subscriptions survive server restarts on your machine.
"""
import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01

BASE_DIR = Path(__file__).parent
DEV_VAPID_FILE = BASE_DIR / ".vapid_dev.json"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _application_server_key(vapid: Vapid01) -> str:
    """The public key the browser needs, as a base64url raw uncompressed point."""
    raw = vapid.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return _b64url(raw)


def _raw_private(vapid: Vapid01) -> str:
    value = vapid.private_key.private_numbers().private_value
    return _b64url(value.to_bytes(32, "big"))


def _load_vapid() -> Vapid01:
    env_key = os.environ.get("VAPID_PRIVATE_KEY")
    if env_key:
        return Vapid01.from_raw(env_key.strip().encode())

    if DEV_VAPID_FILE.exists():
        priv = json.loads(DEV_VAPID_FILE.read_text())["private"]
        return Vapid01.from_raw(priv.encode())

    vapid = Vapid01()
    vapid.generate_keys()
    DEV_VAPID_FILE.write_text(json.dumps({"private": _raw_private(vapid)}))
    return vapid


class Settings:
    def __init__(self):
        self.vapid = _load_vapid()
        self.vapid_public_key = _application_server_key(self.vapid)
        self.vapid_claim_email = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@example.com")
        self.reminder_token = os.environ.get("REMINDER_TOKEN")
        self.reminder_days = int(os.environ.get("REMINDER_DAYS", "1"))
        self.db_path = os.environ.get("DB_PATH", str(BASE_DIR / "data" / "push.db"))
        self.using_dev_keys = not bool(os.environ.get("VAPID_PRIVATE_KEY"))


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
