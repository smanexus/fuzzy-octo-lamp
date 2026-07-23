import os
from datetime import date
from itertools import groupby

from flask import Flask, abort, render_template, request

from data_loader import SCHEDULES, get_data, normalize_key

app = Flask(__name__)

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


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
