"""Subcommand implementations for the gs CLI."""

from ..config import Config


def http_error_message(error) -> str:
    """Turn a googleapiclient HttpError into a short, friendly message."""
    status = getattr(getattr(error, "resp", None), "status", None)
    if status in (404, 410):
        return "not found (already deleted?)"
    try:
        reason = error._get_reason()  # parses the API error body
        return f"{status}: {reason}" if status else reason
    except Exception:
        return str(error)


def build_config(ctx, **kwargs) -> Config:
    """Build a Config from the group's shared options (ctx.obj) plus the
    subcommand's own options. Subcommand options take precedence."""
    merged = {}
    if ctx.obj:
        merged.update(ctx.obj)
    merged.update({k: v for k, v in kwargs.items() if v is not None and v != ()})
    return Config.from_cli_args(**merged)


def get_auth(ctx, **kwargs):
    """Return a GoogleAuth configured from shared + subcommand options."""
    from ..auth import GoogleAuth

    config = build_config(ctx, **kwargs)
    config.ensure_directories()
    return GoogleAuth(config)


def get_service(ctx):
    """Authenticated Gmail service (raw resource) for write commands."""
    return get_auth(ctx).service("gmail", "v1")


def get_calendar_service(ctx):
    """Authenticated Calendar v3 service."""
    return get_auth(ctx).service("calendar", "v3")


def get_drive_service(ctx):
    """Authenticated Drive v3 service."""
    return get_auth(ctx).service("drive", "v3")


def get_client(ctx):
    """Return a connected GmailClient (read + parse), for commands that display
    message content (e.g. `gs gmail read`)."""
    from ..client import GmailClient

    config = build_config(ctx)
    config.ensure_directories()
    client = GmailClient(config)
    client.connect()
    return client
