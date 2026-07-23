"""Tiny SQLite layer for storing Web Push subscriptions.

One person (identified by their slug) can have several subscriptions - one per
device/browser they enable notifications on.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from config import get_settings


@contextmanager
def _connect():
    path = get_settings().db_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_slug TEXT NOT NULL,
                endpoint TEXT NOT NULL UNIQUE,
                subscription TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_person ON subscriptions(person_slug)"
        )


def save_subscription(person_slug: str, subscription: dict):
    endpoint = subscription.get("endpoint")
    if not endpoint:
        raise ValueError("subscription without endpoint")
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO subscriptions (person_slug, endpoint, subscription, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(endpoint) DO UPDATE SET
                person_slug = excluded.person_slug,
                subscription = excluded.subscription
            """,
            (person_slug, endpoint, json.dumps(subscription), now),
        )


def delete_by_endpoint(endpoint: str):
    with _connect() as conn:
        conn.execute("DELETE FROM subscriptions WHERE endpoint = ?", (endpoint,))


def subscriptions_for(person_slug: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT subscription FROM subscriptions WHERE person_slug = ?",
            (person_slug,),
        ).fetchall()
    return [json.loads(r["subscription"]) for r in rows]


def all_subscriptions() -> list[tuple[str, dict]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT person_slug, subscription FROM subscriptions"
        ).fetchall()
    return [(r["person_slug"], json.loads(r["subscription"])) for r in rows]


def count_for(person_slug: str) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM subscriptions WHERE person_slug = ?",
            (person_slug,),
        ).fetchone()
    return row["n"]
