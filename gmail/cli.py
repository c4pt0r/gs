#!/usr/bin/env python3
"""
Command line interface for gmail — a Gmail management and monitoring CLI.

`cli` is a click group; each subcommand lives in gmail/commands/ and is
registered here. Authentication and global options live on the group and are
stored in ``ctx.obj`` so every subcommand can build a Config from them.
"""

import os
import sys

import click

from . import __version__


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=__version__)
# Authentication options (shared by all subcommands)
@click.option(
    "--credentials", type=click.Path(exists=True), help="OAuth2 credentials file path"
)
@click.option(
    "--auth-token",
    type=click.Path(exists=True),
    help="Service account authentication token file path",
)
@click.option(
    "--cached-auth-token",
    type=click.Path(),
    default=lambda: os.path.expanduser("~/.gmail/tokens"),
    help="Cached authentication token file path",
)
@click.option(
    "--force-headless",
    is_flag=True,
    help="Force headless authentication mode (console-based)",
)
@click.option(
    "--ignore-token",
    is_flag=True,
    help="Ignore cached authentication token and force re-authentication",
)
# Global options
@click.option(
    "--config-file", type=click.Path(exists=True), help="Configuration file path"
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output mode")
@click.option("--quiet", is_flag=True, help="Quiet mode, only output email JSON")
@click.option("--log-file", type=click.Path(), help="Log file path")
@click.pass_context
def cli(ctx, **kwargs):
    """gmail - Manage and monitor Gmail from the command line.

    \b
    Examples:
        gmail tail --from "noreply@github.com"
        gmail send --to a@b.com --subject Hi --body "hello" --attach report.pdf
        gmail read <id> --mark-read
        gmail rm <id>
        gmail label create Work
        gmail mv <id> --to Work --from INBOX
        gmail repl
    """
    ctx.ensure_object(dict)
    ctx.obj.update(kwargs)


# Register subcommands
from .commands.tail import tail  # noqa: E402
from .commands.repl import repl  # noqa: E402
from .commands.read import read  # noqa: E402
from .commands.mark import mark  # noqa: E402
from .commands.send import send  # noqa: E402
from .commands.rm import rm  # noqa: E402
from .commands.mv import mv  # noqa: E402
from .commands.label import label  # noqa: E402
from .commands.profile import profile  # noqa: E402

for _cmd in (tail, repl, read, mark, send, rm, mv, label, profile):
    cli.add_command(_cmd)


def main():
    """Entry point that maps interrupts to a clean exit code."""
    try:
        cli(standalone_mode=True)
    except KeyboardInterrupt:
        click.echo("\nStopped by user", err=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
