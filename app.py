import os
from datetime import date
from itertools import groupby

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from config import get_settings
from data_loader import SCHEDULES, get_data, normalize_key
from db import count_for, delete_by_endpoint, init_db, save_subscription

app = Flask(__name__)
init_db()

WEEKDAYS_PT = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@app.template_filter("br_date")
def br_date(d: date) -> str:
    return d.strftime("%d/%m/%y")


@app.template_filter("weekday_pt")
def weekday_pt(d: date) -> str:
    return WEEKDAYS_PT[d.weekday()]


@app.template_filter("long_date_pt")
def long_date_pt(d: date) -> str:
    return f"{WEEKDAYS_PT[d.weekday()]}, {d.day:02d} {MONTHS_PT[d.month - 1]} {d.year}"


def today() -> date:
    return date.today()


def _group_person_entries(entries):
    """Collapse (ServiceDate, role) pairs into one card per service date."""
    data = get_data()
    by_service = {}
    for sd, role in entries:
        by_service.setdefault(sd.id, {"service": sd, "roles": []})["roles"].append(role)
    groups = list(by_service.values())
    groups.sort(key=lambda g: (g["service"].date, g["service"].schedule_key))
    for g in groups:
        g["roles"].sort(key=data.role_sort_key)
    return groups


@app.route("/")
def index():
    data = get_data()
    q = request.args.get("q", "").strip()
    people = data.people_sorted()
    if q:
        key = normalize_key(q)
        people = [p for p in people if key in normalize_key(p.display_name)]
    return render_template("index.html", people=people, q=q, total=len(data.people))


@app.route("/pessoa/<slug>")
def person(slug):
    data = get_data()
    person = data.people_by_slug.get(slug)
    if person is None:
        abort(404)

    upcoming = _group_person_entries(data.upcoming_for(person, today()))
    past = _group_person_entries([(sd, r) for sd, r in person.entries if sd.date < today()])
    past.reverse()
    return render_template(
        "person.html",
        person=person,
        upcoming=upcoming,
        past=past,
        schedules=SCHEDULES,
    )


@app.route("/escala/<schedule_key>/<iso_date>")
def service(schedule_key, iso_date):
    data = get_data()
    service_id = f"{schedule_key}-{iso_date}"
    sd = data.by_id.get(service_id)
    if sd is None:
        abort(404)

    assignments = sorted(sd.assignments, key=lambda a: (data.role_sort_key(a.role), a.person_display))
    grouped = []
    for role, group in groupby(assignments, key=lambda a: a.role):
        people = []
        for a in group:
            person = data.people.get(a.person_key)
            people.append({"display": a.person_display, "slug": person.slug if person else None})
        grouped.append({"role": role, "people": people})
    return render_template(
        "service_detail.html",
        service=sd,
        grouped=grouped,
        schedule=SCHEDULES[schedule_key],
    )


# ---------------------------------------------------------------------------
# PWA + Web Push
# ---------------------------------------------------------------------------

@app.route("/manifest.webmanifest")
def manifest():
    icons_dir = "icons"
    return jsonify({
        "name": "Escala de Louvor",
        "short_name": "Escala",
        "description": "Consulta da escala do ministério de louvor",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#1a1210",
        "theme_color": "#1a1210",
        "lang": "pt-BR",
        "icons": [
            {"src": url_for("static", filename=f"{icons_dir}/icon-192.png"),
             "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": url_for("static", filename=f"{icons_dir}/icon-512.png"),
             "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": url_for("static", filename=f"{icons_dir}/icon-maskable-512.png"),
             "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    })


@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(app.static_folder, "sw.js")
    resp.headers["Content-Type"] = "application/javascript"
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/api/vapid-public-key")
def vapid_public_key():
    return jsonify({"publicKey": get_settings().vapid_public_key})


@app.route("/api/subscribe", methods=["POST"])
def api_subscribe():
    body = request.get_json(silent=True) or {}
    slug = body.get("slug")
    subscription = body.get("subscription")
    data = get_data()
    if not slug or slug not in data.people_by_slug:
        return jsonify({"error": "pessoa inválida"}), 400
    if not subscription or not subscription.get("endpoint"):
        return jsonify({"error": "subscription inválida"}), 400
    save_subscription(slug, subscription)
    return jsonify({"ok": True, "devices": count_for(slug)})


@app.route("/api/unsubscribe", methods=["POST"])
def api_unsubscribe():
    body = request.get_json(silent=True) or {}
    endpoint = body.get("endpoint")
    if not endpoint:
        return jsonify({"error": "endpoint ausente"}), 400
    delete_by_endpoint(endpoint)
    return jsonify({"ok": True})


@app.route("/api/test-push", methods=["POST"])
def api_test_push():
    from push import notify_person

    body = request.get_json(silent=True) or {}
    slug = body.get("slug")
    data = get_data()
    person = data.people_by_slug.get(slug) if slug else None
    if person is None:
        return jsonify({"error": "pessoa inválida"}), 400
    if count_for(slug) == 0:
        return jsonify({"error": "sem dispositivos inscritos"}), 400
    payload = {
        "title": "Notificação de teste",
        "body": f"Olá, {person.display_name.split()[0]}! As notificações estão funcionando. 🙌",
        "url": url_for("person", slug=slug),
        "tag": "teste",
    }
    sent = notify_person(slug, payload)
    return jsonify({"ok": True, "sent": sent})


@app.route("/tasks/send-reminders", methods=["GET", "POST"])
def tasks_send_reminders():
    from push import send_weekend_reminders

    settings = get_settings()
    token = request.args.get("token") or request.headers.get("X-Token")
    if not settings.reminder_token or token != settings.reminder_token:
        abort(403)
    ref_arg = request.args.get("date")
    ref = date.fromisoformat(ref_arg) if ref_arg else date.today()
    report = send_weekend_reminders(ref)
    return jsonify(report)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
