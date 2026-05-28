"""Google Calendar operations: list calendars, list/create/delete events.

`CalendarService` wraps an authenticated Calendar v3 resource. `parse_when`
turns human inputs ("now", "today", "+7d", or ISO 8601) into an RFC 3339 UTC
timestamp for the events time window.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from dateutil.parser import parse as parse_date


_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RELATIVE = re.compile(r"^([+-]\d+)([dhm])$")


def _local_tz():
    """The machine's local timezone (a fixed-offset tzinfo for the current moment)."""
    return datetime.now().astimezone().tzinfo


def parse_when(value: str) -> str:
    """Return an RFC 3339 UTC timestamp for a human time expression.

    "today"/"tomorrow" anchor to *local* midnight; "now" and relative offsets
    (+7d, -2h) are relative to the current instant.
    """
    v = value.strip().lower()
    now = datetime.now(timezone.utc)
    local_now = now.astimezone(_local_tz())

    if v in ("now",):
        dt = now
    elif v == "today":
        dt = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif v == "tomorrow":
        dt = (local_now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        m = _RELATIVE.match(v)
        if m:
            amount = int(m.group(1))
            unit = m.group(2)
            delta = {
                "d": timedelta(days=amount),
                "h": timedelta(hours=amount),
                "m": timedelta(minutes=amount),
            }[unit]
            dt = now + delta
        else:
            # Pass through valid ISO/RFC3339 unchanged; otherwise parse it.
            parsed = parse_date(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return value if _is_rfc3339_z(value) else _to_z(parsed)

    return _to_z(dt)


def _is_rfc3339_z(value: str) -> bool:
    return value.endswith("Z") and "T" in value


def _to_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _has_offset(value: str) -> bool:
    """True if a timed value already carries a UTC offset or Z."""
    return value.endswith("Z") or re.search(r"[+-]\d{2}:\d{2}$", value) is not None


def _time_field(value: str, tz: Optional[str]) -> Dict[str, str]:
    """Build a Calendar start/end object: all-day date vs timed dateTime.

    For timed values, ensure the API always gets a zone: an explicit
    ``--timezone`` wins; an offset already in the string is kept as-is; a naive
    value is interpreted as local time and emitted with the local offset (the
    API rejects a zoneless dateTime).
    """
    if _DATE_ONLY.match(value):
        return {"date": value}
    if tz:
        return {"dateTime": value, "timeZone": tz}
    if _has_offset(value):
        return {"dateTime": value}
    local = parse_date(value).replace(tzinfo=_local_tz())
    return {"dateTime": local.isoformat()}


class CalendarService:
    """List calendars and list/create/delete events."""

    def __init__(self, service):
        self.service = service

    def list_calendars(self) -> List[Dict[str, Any]]:
        return self.service.calendarList().list().execute().get("items", [])

    def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        params = {
            "calendarId": calendar_id,
            "singleEvents": True,
            "orderBy": "startTime",
            "maxResults": max_results,
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        return self.service.events().list(**params).execute().get("items", [])

    def add_event(
        self,
        summary: str,
        start: str,
        end: str,
        calendar_id: str = "primary",
        description: Optional[str] = None,
        location: Optional[str] = None,
        timezone: Optional[str] = None,
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        body = {
            "summary": summary,
            "start": _time_field(start, timezone),
            "end": _time_field(end, timezone),
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        if attendees:
            body["attendees"] = [{"email": e} for e in attendees]
        # Email invitations to attendees, but stay silent for solo events.
        send_updates = "all" if attendees else "none"
        return (
            self.service.events()
            .insert(calendarId=calendar_id, body=body, sendUpdates=send_updates)
            .execute()
        )

    def delete_event(self, event_id: str, calendar_id: str = "primary"):
        return (
            self.service.events()
            .delete(calendarId=calendar_id, eventId=event_id)
            .execute()
        )
