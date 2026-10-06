"""Today's events from a Google Calendar secret iCal URL."""
from datetime import date, datetime

import httpx
import icalendar
import recurring_ical_events


def get_events(cfg: dict) -> list[dict]:
    url = (cfg.get("ical_url") or "").strip()
    if not url:
        return []
    r = httpx.get(url, timeout=20, follow_redirects=True)
    r.raise_for_status()
    cal = icalendar.Calendar.from_ical(r.content)
    today = date.today()
    events = []
    for ev in recurring_ical_events.of(cal).at(today):
        start = ev.get("DTSTART").dt
        all_day = not isinstance(start, datetime)
        if not all_day:
            start = start.astimezone()  # local time
        events.append({
            "title": str(ev.get("SUMMARY", "Untitled")),
            "time": "all day" if all_day else start.strftime("%I:%M %p").lstrip("0"),
            "location": str(ev.get("LOCATION", "")) or None,
            "_sort": "" if all_day else start.strftime("%H:%M"),
        })
    events.sort(key=lambda e: e["_sort"])
    for e in events:
        del e["_sort"]
    return events


if __name__ == "__main__":
    from app.config import load_config
    print(get_events(load_config()))
