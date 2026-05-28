#!/usr/bin/env python3
"""Tests for gmail Config loading and output formatting."""

import json
import os
import tempfile
from datetime import datetime, timezone

from gs.config import Config
from gs.client import GmailClient
from gs.formatter import OutputFormatter


def test_parsed_timestamp_is_timezone_aware():
    """The parsed `timestamp` must carry an offset (not a bare naive string)."""
    config = Config()
    config.cache.enabled = False
    client = GmailClient(config)
    # 2026-05-28T15:50:53Z in epoch milliseconds.
    epoch_ms = int(
        datetime(2026, 5, 28, 15, 50, 53, tzinfo=timezone.utc).timestamp() * 1000
    )
    parsed = client.parse_message(
        {"id": "x", "threadId": "t", "internalDate": str(epoch_ms), "payload": {}}
    )
    ts = parsed["timestamp"]
    assert ts.endswith("Z") or ts[-6] in "+-"
    # Same instant regardless of the machine's local zone.
    assert datetime.fromisoformat(ts).astimezone(timezone.utc) == datetime(
        2026, 5, 28, 15, 50, 53, tzinfo=timezone.utc
    )


def test_default_config():
    config = Config()
    assert config.auth.cached_auth_token.endswith(".gs/tokens")
    assert config.checkpoint.checkpoint_file.endswith(".gs/checkpoint")
    assert config.monitoring.poll_interval == 30


def test_config_from_cli_args():
    config = Config.from_cli_args(
        from_email="test@example.com",
        poll_interval=60,
        output_format="json-lines",
    )
    assert config.filters.from_email == "test@example.com"
    assert config.monitoring.poll_interval == 60
    assert config.output.format == "json-lines"


def test_config_from_yaml():
    yaml_content = """
auth:
  credentials_file: /path/to/creds.json
  cached_auth_token: /custom/token/path

filters:
  query: "label:test"
  unread_only: true

output:
  format: compact
  include_body: true
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        temp_yaml = f.name

    try:
        config = Config.from_file(temp_yaml)
        assert config.auth.credentials == "/path/to/creds.json"
        assert config.auth.cached_auth_token == "/custom/token/path"
        assert config.filters.query == "label:test"
        assert config.filters.unread_only is True
        assert config.output.format == "compact"
        assert config.output.include_body is True
    finally:
        os.unlink(temp_yaml)


def _sample_message():
    return {
        "id": "test123",
        "subject": "Test Subject",
        "from": {"name": "Test Sender", "email": "test@example.com"},
        "timestamp": "2025-07-01T10:30:00Z",
        "body": "Test email body",
    }


def test_format_json():
    config = Config()
    config.output.format = "json"
    out = OutputFormatter(config).format_message(_sample_message())
    parsed = json.loads(out)
    assert parsed["id"] == "test123"
    assert parsed["subject"] == "Test Subject"


def test_format_compact():
    config = Config()
    config.output.format = "compact"
    out = OutputFormatter(config).format_message(_sample_message())
    # Compact reformats the ISO timestamp (drops T/Z) and prefers sender name.
    assert "2025-07-01 10:30:00" in out
    assert "Test Sender" in out
    assert "Test Subject" in out


def test_format_field_filtering():
    config = Config()
    config.output.format = "json"
    config.output.fields = ["id", "subject"]
    out = OutputFormatter(config).format_message(_sample_message())
    parsed = json.loads(out)
    assert set(parsed.keys()) == {"id", "subject"}
