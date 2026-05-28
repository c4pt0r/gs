"""`gmail mark` — change the read state of one or more messages."""

import click

from . import get_service
from ..messages import MessageService


@click.command()
@click.argument("message_ids", nargs=-1, required=True)
@click.option("--read", "state", flag_value="read", help="Mark messages as read")
@click.option("--unread", "state", flag_value="unread", help="Mark messages as unread")
@click.pass_context
def mark(ctx, message_ids, state):
    """Mark MESSAGE_IDS as --read or --unread."""
    if not state:
        raise click.UsageError("Specify --read or --unread")

    svc = MessageService(get_service(ctx))
    for mid in message_ids:
        if state == "read":
            svc.mark_read(mid)
        else:
            svc.mark_unread(mid)
        click.echo(f"{mid}: marked {state}")
