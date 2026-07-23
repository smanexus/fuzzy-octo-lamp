"""Sends Web Push notifications and builds the weekend reminder payloads."""
import json
from dataclasses import dataclass
from datetime import date, timedelta

from pywebpush import WebPushException, webpush

from config import get_settings
from data_loader import get_data
from db import all_subscriptions, delete_by_endpoint


def send_to_subscription(subscription: dict, payload: dict) -> bool:
    """Returns True if delivered, False if the subscription is gone (410/404)."""
    settings = get_settings()
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=settings.vapid,
            vapid_claims={"sub": settings.vapid_claim_email},
            ttl=60 * 60 * 12,
        )
        return True
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        if status in (404, 410):
            delete_by_endpoint(subscription.get("endpoint", ""))
        else:
            raise
        return False


def notify_person(person_slug: str, payload: dict) -> int:
    """Send a payload to every device a person subscribed. Returns count sent."""
    from db import subscriptions_for

    sent = 0
    for sub in subscriptions_for(person_slug):
        if send_to_subscription(sub, payload):
            sent += 1
    return sent


# ---------------------------------------------------------------------------
# Weekend reminders
# ---------------------------------------------------------------------------

@dataclass
class WeekendDuty:
    schedule_name: str  # "Ichthus" / "Doulos"
    weekday: str        # "Sábado" / "Domingo"
    roles: list[str]


def weekend_bounds(ref: date) -> tuple[date, date]:
    """Saturday and Sunday of the weekend belonging to ref's week (Mon-anchored)."""
    saturday = ref + timedelta(days=(5 - ref.weekday()))
    sunday = ref + timedelta(days=(6 - ref.weekday()))
    return saturday, sunday


def duties_by_person(saturday: date, sunday: date) -> dict[str, list[WeekendDuty]]:
    """Map person slug -> their duties across that weekend's services."""
    data = get_data()
    result: dict[str, list[WeekendDuty]] = {}
    for sd in data.service_dates:
        if sd.date not in (saturday, sunday):
            continue
        conf = data_schedule_conf(sd.schedule_key)
        # collapse a person's roles on this service into one WeekendDuty
        per_person: dict[str, list[str]] = {}
        for a in sd.assignments:
            per_person.setdefault(a.person_key, []).append(a.role)
        for person_key, roles in per_person.items():
            person = data.people.get(person_key)
            if person is None:
                continue
            roles = sorted(set(roles), key=data.role_sort_key)
            result.setdefault(person.slug, []).append(
                WeekendDuty(schedule_name=conf["name"], weekday=conf["weekday"], roles=roles)
            )
    return result


def data_schedule_conf(schedule_key: str) -> dict:
    from data_loader import SCHEDULES

    return SCHEDULES[schedule_key]


def _join_roles(roles: list[str]) -> str:
    if len(roles) == 1:
        return roles[0]
    return ", ".join(roles[:-1]) + " e " + roles[-1]


def build_reminder(display_name: str, duties: list[WeekendDuty]) -> dict:
    """Compose the notification title/body from a person's weekend duties."""
    duties = sorted(duties, key=lambda d: 0 if d.weekday == "Sábado" else 1)
    lines = []
    for d in duties:
        lines.append(f"{d.weekday} ({d.schedule_name}): {_join_roles(d.roles)}")

    first = display_name.split()[0]
    if len(duties) == 1:
        d = duties[0]
        intro = f"Você está na escala deste fim de semana pelo {d.schedule_name} ({d.weekday})"
    else:
        # keep weekday order (Sábado first) and de-duplicate ministry names
        seen = []
        for d in duties:
            if d.schedule_name not in seen:
                seen.append(d.schedule_name)
        names = " e ".join(seen)
        intro = f"Você está na escala deste fim de semana pelos ministérios {names}"

    body = f"Olá, {first}! {intro}, para servir em:\n" + "\n".join(lines)
    body += "\nQue Deus te use com graça! 🙌"

    return {
        "title": "Escala deste fim de semana",
        "body": body,
        "url": "/",
        "tag": "escala-fds",
    }


def send_weekend_reminders(ref: date) -> dict:
    """Send reminders to every subscribed person on duty this weekend."""
    saturday, sunday = weekend_bounds(ref)
    duties = duties_by_person(saturday, sunday)
    data = get_data()

    subscribed_slugs = {slug for slug, _ in all_subscriptions()}
    report = {"weekend": [saturday.isoformat(), sunday.isoformat()], "notified": [], "sent": 0}

    for slug in subscribed_slugs:
        person_duties = duties.get(slug)
        if not person_duties:
            continue
        person = data.people_by_slug.get(slug)
        if person is None:
            continue
        payload = build_reminder(person.display_name, person_duties)
        sent = notify_person(slug, payload)
        if sent:
            report["notified"].append({"slug": slug, "name": person.display_name, "devices": sent})
            report["sent"] += sent
    return report
