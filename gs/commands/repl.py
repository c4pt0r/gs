"""`gmail repl` — interactive shell for exploring a Gmail account."""

import click

from . import build_config
from ..repl import GmailREPL


@click.command()
@click.pass_context
def repl(ctx):
    """Start an interactive REPL for browsing labels and running queries."""
    config = build_config(ctx)
    GmailREPL(config).run()
