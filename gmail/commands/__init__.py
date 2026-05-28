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
