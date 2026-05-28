"""Subcommand implementations for the gmail CLI."""

from ..config import Config


def build_config(ctx, **kwargs) -> Config:
    """Build a Config from the group's shared options (ctx.obj) plus the
    subcommand's own options. Subcommand options take precedence."""
    merged = {}
    if ctx.obj:
        merged.update(ctx.obj)
    merged.update({k: v for k, v in kwargs.items() if v is not None and v != ()})
    return Config.from_cli_args(**merged)


def get_service(ctx):
    """Authenticate from the group's shared options and return a raw Gmail
    service resource. Used by write commands that don't need the read client."""
    from ..auth import GmailAuth

    config = build_config(ctx)
    config.ensure_directories()
    return GmailAuth(config).authenticate()


def get_client(ctx):
    """Return a connected GmailClient (read + parse), for commands that display
    message content (e.g. `gmail read`)."""
    from ..client import GmailClient

    config = build_config(ctx)
    config.ensure_directories()
    client = GmailClient(config)
    client.connect()
    return client
