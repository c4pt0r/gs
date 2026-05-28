#!/usr/bin/env python3
"""CLI wiring tests using click's CliRunner with mocked Google services.

Commands now live under sibling subgroups: `gs gmail ...`, `gs calendar ...`,
`gs drive ...`, `gs auth ...`.
"""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from gs.cli import cli


def run(args, service=None):
    """Invoke the CLI with the gmail get_service helpers patched."""
    service = service or MagicMock()
    runner = CliRunner()
    with patch("gs.commands.get_service", return_value=service), patch(
        "gs.commands.mark.get_service", return_value=service
    ), patch("gs.commands.rm.get_service", return_value=service), patch(
        "gs.commands.mv.get_service", return_value=service
    ), patch(
        "gs.commands.send.get_service", return_value=service
    ), patch(
        "gs.commands.label.get_service", return_value=service
    ):
        result = runner.invoke(cli, args)
    return result, service


def run_calendar(args, service=None):
    service = service or MagicMock()
    with patch("gs.commands.calendar.get_calendar_service", return_value=service):
        result = CliRunner().invoke(cli, args)
    return result, service


def run_drive(args, service=None):
    service = service or MagicMock()
    with patch("gs.commands.drive.get_drive_service", return_value=service):
        result = CliRunner().invoke(cli, args)
    return result, service


# --------------------------------------------------------------------------
# top-level structure
# --------------------------------------------------------------------------


def test_help_lists_subgroups():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    for group in ["auth", "gmail", "calendar", "drive"]:
        assert group in result.output


def test_gmail_help_lists_commands():
    result = CliRunner().invoke(cli, ["gmail", "--help"])
    assert result.exit_code == 0
    for cmd in ["tail", "send", "read", "mark", "rm", "mv", "label", "profile"]:
        assert cmd in result.output


# --------------------------------------------------------------------------
# gmail subgroup
# --------------------------------------------------------------------------


def test_gmail_mark_read():
    result, service = run(["gmail", "mark", "m1", "--read"])
    assert result.exit_code == 0
    service.users().messages().modify.assert_called_with(
        userId="me", id="m1", body={"removeLabelIds": ["UNREAD"]}
    )


def test_gmail_rm_trashes_by_default():
    result, service = run(["gmail", "rm", "m1"])
    assert result.exit_code == 0
    service.users().messages().trash.assert_called_with(userId="me", id="m1")


def test_gmail_rm_permanently_with_yes():
    result, service = run(["gmail", "rm", "m1", "--permanently", "--yes"])
    assert result.exit_code == 0
    service.users().messages().delete.assert_called_with(userId="me", id="m1")


def test_gmail_mv_resolves_and_moves():
    service = MagicMock()
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "Label_9", "name": "Work"}]
    }
    result, _ = run(
        ["gmail", "mv", "m1", "--to", "Work", "--from", "INBOX"], service=service
    )
    assert result.exit_code == 0
    service.users().messages().modify.assert_called_with(
        userId="me",
        id="m1",
        body={"addLabelIds": ["Label_9"], "removeLabelIds": ["INBOX"]},
    )


def test_gmail_send_basic():
    result, service = run(
        ["gmail", "send", "--to", "a@b.com", "--subject", "Hi", "--body", "yo"]
    )
    assert result.exit_code == 0
    _, kwargs = service.users().messages().send.call_args
    assert "raw" in kwargs["body"]


# --------------------------------------------------------------------------
# calendar subgroup
# --------------------------------------------------------------------------


def test_calendar_ls():
    service = MagicMock()
    service.calendarList().list().execute.return_value = {
        "items": [{"id": "primary", "summary": "Me"}]
    }
    result, _ = run_calendar(["calendar", "ls"], service=service)
    assert result.exit_code == 0
    assert "primary" in result.output


def test_calendar_add():
    result, service = run_calendar(
        [
            "calendar",
            "add",
            "--summary",
            "Mtg",
            "--start",
            "2026-06-01T10:00:00Z",
            "--end",
            "2026-06-01T11:00:00Z",
        ]
    )
    assert result.exit_code == 0
    _, kwargs = service.events().insert.call_args
    assert kwargs["body"]["summary"] == "Mtg"


def test_calendar_rm():
    result, service = run_calendar(["calendar", "rm", "ev1"])
    assert result.exit_code == 0
    service.events().delete.assert_called_with(calendarId="primary", eventId="ev1")


def test_calendar_rm_already_deleted_is_graceful():
    from googleapiclient.errors import HttpError

    resp = type("Resp", (), {"status": 410, "reason": "Gone"})()
    err = HttpError(resp, b'{"error": {"message": "Resource has been deleted"}}')

    service = MagicMock()
    service.events().delete().execute.side_effect = err
    result, _ = run_calendar(["calendar", "rm", "ev1"], service=service)
    # No traceback: clean exit, friendly message, id mentioned.
    assert result.exit_code == 0
    assert "ev1" in result.output
    assert "Traceback" not in result.output


# --------------------------------------------------------------------------
# drive subgroup
# --------------------------------------------------------------------------


def test_drive_ls():
    service = MagicMock()
    service.files().list().execute.return_value = {
        "files": [{"id": "f1", "name": "doc.txt", "mimeType": "text/plain"}]
    }
    result, _ = run_drive(["drive", "ls"], service=service)
    assert result.exit_code == 0
    assert "doc.txt" in result.output


def test_drive_mkdir():
    result, service = run_drive(["drive", "mkdir", "Reports"])
    assert result.exit_code == 0
    _, kwargs = service.files().create.call_args
    assert kwargs["body"]["mimeType"] == "application/vnd.google-apps.folder"


def test_drive_rm_trashes_by_default():
    result, service = run_drive(["drive", "rm", "f1"])
    assert result.exit_code == 0
    service.files().update.assert_called_with(fileId="f1", body={"trashed": True})
