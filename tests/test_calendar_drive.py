#!/usr/bin/env python3
"""Tests for CalendarService and DriveService (mocked Google API)."""

from unittest.mock import MagicMock, patch

from gs.calendar_service import CalendarService, parse_when
from gs.drive_service import DriveService


def svc():
    return MagicMock()


# --------------------------------------------------------------------------
# CalendarService
# --------------------------------------------------------------------------


def test_list_calendars():
    s = svc()
    s.calendarList().list().execute.return_value = {
        "items": [{"id": "primary", "summary": "Me"}]
    }
    cals = CalendarService(s).list_calendars()
    assert cals[0]["id"] == "primary"


def test_list_events_passes_time_window():
    s = svc()
    s.events().list().execute.return_value = {"items": []}
    CalendarService(s).list_events(
        time_min="2026-01-01T00:00:00Z", time_max="2026-01-08T00:00:00Z"
    )
    _, kwargs = s.events().list.call_args
    assert kwargs["timeMin"] == "2026-01-01T00:00:00Z"
    assert kwargs["timeMax"] == "2026-01-08T00:00:00Z"
    assert kwargs["singleEvents"] is True


def test_add_event_datetime():
    s = svc()
    CalendarService(s).add_event(
        summary="Meeting", start="2026-06-01T10:00:00Z", end="2026-06-01T11:00:00Z"
    )
    _, kwargs = s.events().insert.call_args
    body = kwargs["body"]
    assert body["summary"] == "Meeting"
    assert body["start"] == {"dateTime": "2026-06-01T10:00:00Z"}
    assert body["end"] == {"dateTime": "2026-06-01T11:00:00Z"}


def test_add_event_all_day_uses_date():
    s = svc()
    CalendarService(s).add_event(
        summary="Holiday", start="2026-06-01", end="2026-06-02"
    )
    _, kwargs = s.events().insert.call_args
    assert kwargs["body"]["start"] == {"date": "2026-06-01"}


def test_add_event_with_attendees_sends_invites():
    s = svc()
    CalendarService(s).add_event(
        summary="Coffee",
        start="2026-05-29T10:00:00-07:00",
        end="2026-05-29T11:00:00-07:00",
        attendees=["guest@example.com"],
    )
    _, kwargs = s.events().insert.call_args
    assert kwargs["body"]["attendees"] == [{"email": "guest@example.com"}]
    assert kwargs["sendUpdates"] == "all"


def test_delete_event():
    s = svc()
    CalendarService(s).delete_event("ev1")
    s.events().delete.assert_called_with(calendarId="primary", eventId="ev1")


def test_parse_when_passthrough_iso():
    assert parse_when("2026-06-01T10:00:00Z") == "2026-06-01T10:00:00Z"


def test_parse_when_relative_returns_utc():
    assert parse_when("now").endswith("Z")
    assert parse_when("+7d").endswith("Z")


def test_parse_when_today_is_local_midnight():
    from datetime import datetime, timezone

    # "today" must anchor to LOCAL midnight, expressed in UTC.
    local_now = datetime.now().astimezone()
    expected = (
        local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    assert parse_when("today") == expected


def test_add_event_naive_start_gets_local_offset():
    # A naive datetime (no offset) and no --timezone must still carry a zone,
    # otherwise the Calendar API rejects it.
    s = svc()
    CalendarService(s).add_event(
        summary="Mtg", start="2026-06-01T10:00:00", end="2026-06-01T11:00:00"
    )
    _, kwargs = s.events().insert.call_args
    dt = kwargs["body"]["start"]["dateTime"]
    # Has an explicit offset (±HH:MM) or Z — not a bare naive timestamp.
    assert dt.endswith("Z") or dt[-6] in "+-"
    assert "timeZone" not in kwargs["body"]["start"]


# --------------------------------------------------------------------------
# DriveService
# --------------------------------------------------------------------------


def test_drive_list_files():
    s = svc()
    s.files().list().execute.return_value = {"files": [{"id": "f1", "name": "doc.txt"}]}
    files = DriveService(s).list_files(query="name contains 'doc'")
    assert files[0]["name"] == "doc.txt"
    _, kwargs = s.files().list.call_args
    assert kwargs["q"] == "name contains 'doc'"


def test_drive_mkdir():
    s = svc()
    DriveService(s).mkdir("Reports")
    _, kwargs = s.files().create.call_args
    assert kwargs["body"]["name"] == "Reports"
    assert kwargs["body"]["mimeType"] == "application/vnd.google-apps.folder"


def test_drive_upload(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("a,b,c")
    s = svc()
    DriveService(s).upload(str(f))
    _, kwargs = s.files().create.call_args
    assert kwargs["body"]["name"] == "data.csv"
    assert kwargs["media_body"] is not None


def test_drive_delete_trashes_by_default():
    s = svc()
    DriveService(s).delete("f1")
    s.files().update.assert_called_with(fileId="f1", body={"trashed": True})


def test_drive_delete_permanent():
    s = svc()
    DriveService(s).delete("f1", permanent=True)
    s.files().delete.assert_called_with(fileId="f1")


def test_drive_download(tmp_path):
    s = svc()
    out = tmp_path / "out.bin"

    class FakeDownloader:
        def __init__(self, fh, request):
            pass

        def next_chunk(self):
            return (None, True)

    with patch("gs.drive_service.MediaIoBaseDownload", FakeDownloader):
        result = DriveService(s).download("f1", str(out))
    s.files().get_media.assert_called_with(fileId="f1")
    assert result == str(out)
