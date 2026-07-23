"""Loads the worship team schedule from the CSV files in data/ into memory.

The spreadsheets are exported from a shared sheet: each row is a role/function,
each column (after the first) is a service date, and the cell is who's serving
that role on that date. The same person commonly appears in more than one role
on the same date - that's one service with multiple assignments, not two.
"""
import csv
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

SCHEDULES = {
    "ichthus": {
        "key": "ichthus",
        "name": "Ichthus",
        "weekday": "Sábado",
        "csv": "ichthus.csv",
    },
    "doulos": {
        "key": "doulos",
        "name": "Doulos",
        "weekday": "Domingo",
        "csv": "doulos.csv",
    },
}

ROLE_DISPLAY = {
    "Vocal Mas.": "Vocal Masculino",
}

# Same person spelled differently across the sheets -> canonical key.
NAME_ALIASES = {
    "giovana": "giovanna",
    "gian": "gianlucca",
}

ROLE_ORDER = [
    "Ministro",
    "Violão",
    "Guitarra",
    "Teclado",
    "Baixo",
    "Bateria",
    "Vocal Masculino",
    "Vocal Soprano",
    "Vocal Meso",
    "Vocal Contralto",
]


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_key(name: str) -> str:
    name = " ".join(name.strip().split())
    key = strip_accents(name).lower()
    return NAME_ALIASES.get(key, key)


def slugify(name: str) -> str:
    key = normalize_key(name)
    key = re.sub(r"[^a-z0-9\s-]", "", key)
    return re.sub(r"\s+", "-", key.strip())


def _name_score(name: str):
    accents = sum(1 for c in name if ord(c) > 127)
    starts_upper = name[:1].isupper()
    return (accents, starts_upper, len(name))


@dataclass
class Assignment:
    role: str
    person_key: str
    person_display: str


@dataclass
class ServiceDate:
    schedule_key: str
    date: date
    assignments: list = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.schedule_key}-{self.date.isoformat()}"


@dataclass
class Person:
    key: str
    display_name: str
    slug: str
    entries: list = field(default_factory=list)  # list of (ServiceDate, role)


def _parse_date(cell: str) -> date:
    return datetime.strptime(cell.strip(), "%d/%m/%y").date()


def _load_schedule(schedule_key: str) -> list[ServiceDate]:
    conf = SCHEDULES[schedule_key]
    path = DATA_DIR / conf["csv"]
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))

    header, *role_rows = rows
    dates = [_parse_date(cell) for cell in header[1:] if cell.strip()]
    service_dates = [ServiceDate(schedule_key=schedule_key, date=d) for d in dates]

    for row in role_rows:
        if not row or not row[0].strip():
            continue
        role = ROLE_DISPLAY.get(row[0].strip(), row[0].strip())
        for i, service_date in enumerate(service_dates):
            if i >= len(row) - 1:
                break
            raw_name = row[i + 1].strip()
            if not raw_name:
                continue
            service_date.assignments.append(
                Assignment(role=role, person_key=normalize_key(raw_name), person_display=raw_name)
            )
    return service_dates


class ScheduleData:
    def __init__(self):
        self.service_dates: list[ServiceDate] = []
        self.people: dict[str, Person] = {}
        self.people_by_slug: dict[str, Person] = {}
        self.by_id: dict[str, ServiceDate] = {}
        self._load()

    def _load(self):
        for schedule_key in SCHEDULES:
            self.service_dates.extend(_load_schedule(schedule_key))
        self.service_dates.sort(key=lambda sd: (sd.date, sd.schedule_key))

        for sd in self.service_dates:
            self.by_id[sd.id] = sd
            for a in sd.assignments:
                person = self.people.get(a.person_key)
                if person is None:
                    person = Person(key=a.person_key, display_name=a.person_display, slug=slugify(a.person_display))
                    self.people[a.person_key] = person
                elif _name_score(a.person_display) > _name_score(person.display_name):
                    person.display_name = a.person_display
                person.entries.append((sd, a.role))

        for person in self.people.values():
            self.people_by_slug[person.slug] = person

    def people_sorted(self) -> list[Person]:
        return sorted(self.people.values(), key=lambda p: normalize_key(p.display_name))

    def upcoming_for(self, person: Person, today: date):
        return [(sd, role) for sd, role in person.entries if sd.date >= today]

    def role_sort_key(self, role: str) -> int:
        try:
            return ROLE_ORDER.index(role)
        except ValueError:
            return len(ROLE_ORDER)


_data: ScheduleData | None = None


def get_data() -> ScheduleData:
    global _data
    if _data is None:
        _data = ScheduleData()
    return _data
