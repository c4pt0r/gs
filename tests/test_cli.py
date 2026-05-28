#!/usr/bin/env python3
"""CLI wiring tests using click's CliRunner with a mocked Gmail service."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from gmail.cli import cli


def run(args, service=None):
    """Invoke the CLI with get_service/get_client patched to return `service`."""
    service = service or MagicMock()
    runner = CliRunner()
    with patch("gmail.commands.get_service", return_value=service), patch(
        "gmail.commands.mark.get_service", return_value=service
    ), patch("gmail.commands.rm.get_service", return_value=service), patch(
        "gmail.commands.mv.get_service", return_value=service
    ), patch(
        "gmail.commands.send.get_service", return_value=service
    ), patch(
        "gmail.commands.label.get_service", return_value=service
    ):
        result = runner.invoke(cli, args)
    return result, service


def test_help_lists_all_commands():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ["tail", "repl", "read", "mark", "send", "rm", "mv", "label", "profile"]:
        assert cmd in result.output


def test_mark_read():
    result, service = run(["mark", "m1", "--read"])
    assert result.exit_code == 0
    service.users().messages().modify.assert_called_with(
        userId="me", id="m1", body={"removeLabelIds": ["UNREAD"]}
    )


def test_mark_requires_state():
    result, _ = run(["mark", "m1"])
    assert result.exit_code != 0


def test_rm_trashes_by_default():
    result, service = run(["rm", "m1"])
    assert result.exit_code == 0
    service.users().messages().trash.assert_called_with(userId="me", id="m1")


def test_rm_permanently_with_yes():
    result, service = run(["rm", "m1", "--permanently", "--yes"])
    assert result.exit_code == 0
    service.users().messages().delete.assert_called_with(userId="me", id="m1")


def test_rm_permanently_aborts_without_confirmation():
    runner = CliRunner()
    service = MagicMock()
    with patch("gmail.commands.rm.get_service", return_value=service):
        result = runner.invoke(cli, ["rm", "m1", "--permanently"], input="n\n")
    assert result.exit_code != 0
    service.users().messages().delete.assert_not_called()


def test_mv_resolves_and_moves():
    service = MagicMock()
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "Label_9", "name": "Work"}]
    }
    result, _ = run(["mv", "m1", "--to", "Work", "--from", "INBOX"], service=service)
    assert result.exit_code == 0
    service.users().messages().modify.assert_called_with(
        userId="me",
        id="m1",
        body={"addLabelIds": ["Label_9"], "removeLabelIds": ["INBOX"]},
    )


def test_label_create():
    result, service = run(["label", "create", "Projects"])
    assert result.exit_code == 0
    _, kwargs = service.users().labels().create.call_args
    assert kwargs["body"]["name"] == "Projects"


def test_label_ls():
    service = MagicMock()
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "Label_1", "name": "Work"}]
    }
    result, _ = run(["label", "ls"], service=service)
    assert result.exit_code == 0
    assert "Work" in result.output


def test_send_basic():
    result, service = run(
        ["send", "--to", "a@b.com", "--subject", "Hi", "--body", "yo"]
    )
    assert result.exit_code == 0
    _, kwargs = service.users().messages().send.call_args
    assert "raw" in kwargs["body"]
