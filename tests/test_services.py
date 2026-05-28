#!/usr/bin/env python3
"""Tests for the write-capable Gmail service layer (mocked Gmail API)."""

import base64
import email
from unittest.mock import MagicMock

import pytest

from gs.messages import MessageService, build_raw_message
from gs.labels import LabelService


def make_service():
    """A MagicMock standing in for googleapiclient's Gmail resource.

    Every call like service.users().messages().modify(...).execute() returns a
    MagicMock; we assert on the recorded call args.
    """
    return MagicMock()


# --------------------------------------------------------------------------
# MessageService: read state
# --------------------------------------------------------------------------


def test_mark_read_removes_unread_label():
    service = make_service()
    MessageService(service).mark_read("m1")
    service.users().messages().modify.assert_called_with(
        userId="me", id="m1", body={"removeLabelIds": ["UNREAD"]}
    )


def test_mark_unread_adds_unread_label():
    service = make_service()
    MessageService(service).mark_unread("m1")
    service.users().messages().modify.assert_called_with(
        userId="me", id="m1", body={"addLabelIds": ["UNREAD"]}
    )


# --------------------------------------------------------------------------
# MessageService: delete
# --------------------------------------------------------------------------


def test_trash_calls_trash_endpoint():
    service = make_service()
    MessageService(service).trash("m2")
    service.users().messages().trash.assert_called_with(userId="me", id="m2")


def test_delete_calls_delete_endpoint():
    service = make_service()
    MessageService(service).delete("m3")
    service.users().messages().delete.assert_called_with(userId="me", id="m3")


# --------------------------------------------------------------------------
# MessageService: move
# --------------------------------------------------------------------------


def test_move_adds_and_removes_labels():
    service = make_service()
    MessageService(service).move(
        "m4", add_label_ids=["Label_1"], remove_label_ids=["INBOX"]
    )
    service.users().messages().modify.assert_called_with(
        userId="me",
        id="m4",
        body={"addLabelIds": ["Label_1"], "removeLabelIds": ["INBOX"]},
    )


# --------------------------------------------------------------------------
# build_raw_message
# --------------------------------------------------------------------------


def test_build_raw_message_basic():
    raw = build_raw_message(
        to="a@b.com", subject="Hello", body="hi there", cc="c@d.com"
    )
    decoded = base64.urlsafe_b64decode(raw.encode())
    msg = email.message_from_bytes(decoded)
    assert msg["To"] == "a@b.com"
    assert msg["Cc"] == "c@d.com"
    assert msg["Subject"] == "Hello"
    assert "hi there" in decoded.decode()


def test_build_raw_message_with_attachment(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("file contents")
    raw = build_raw_message(to="a@b.com", subject="S", body="b", attachments=[str(f)])
    decoded = base64.urlsafe_b64decode(raw.encode())
    msg = email.message_from_bytes(decoded)
    assert msg.is_multipart()
    filenames = [p.get_filename() for p in msg.walk() if p.get_filename()]
    assert "note.txt" in filenames


def test_send_calls_send_endpoint():
    service = make_service()
    MessageService(service).send(to="a@b.com", subject="S", body="b")
    args, kwargs = service.users().messages().send.call_args
    assert kwargs["userId"] == "me"
    assert "raw" in kwargs["body"]


# --------------------------------------------------------------------------
# LabelService
# --------------------------------------------------------------------------


def test_list_labels_returns_labels():
    service = make_service()
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "INBOX", "name": "INBOX"}, {"id": "Label_1", "name": "Work"}]
    }
    labels = LabelService(service).list()
    names = [l["name"] for l in labels]
    assert "Work" in names


def test_create_label():
    service = make_service()
    LabelService(service).create("Projects")
    args, kwargs = service.users().labels().create.call_args
    assert kwargs["userId"] == "me"
    assert kwargs["body"]["name"] == "Projects"


def test_resolve_system_label_id():
    service = make_service()
    assert LabelService(service).resolve_id("INBOX") == "INBOX"
    assert LabelService(service).resolve_id("inbox") == "INBOX"


def test_resolve_user_label_id():
    service = make_service()
    service.users().labels().list().execute.return_value = {
        "labels": [{"id": "Label_42", "name": "Work"}]
    }
    assert LabelService(service).resolve_id("Work") == "Label_42"


def test_resolve_unknown_label_raises():
    service = make_service()
    service.users().labels().list().execute.return_value = {"labels": []}
    with pytest.raises(ValueError):
        LabelService(service).resolve_id("Nope")
