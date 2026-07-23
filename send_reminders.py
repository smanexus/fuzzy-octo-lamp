"""Send the weekend schedule reminders.

Run it on Monday morning (via a Railway Cron service, or any external cron
hitting /tasks/send-reminders). It notifies every subscribed person who is on
the schedule for the coming weekend, telling them the ministry (Ichthus on
Saturday, Doulos on Sunday, or both) and their role(s).

    python send_reminders.py            # uses today as reference
    python send_reminders.py 2026-08-03 # pretend "today" is this date
"""
import json
import sys
from datetime import date

from db import init_db
from push import send_weekend_reminders


def main():
    init_db()
    ref = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    report = send_weekend_reminders(ref)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
