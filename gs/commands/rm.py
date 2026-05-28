"""`gs gmail rm` — trash (default) or permanently delete one or more messages."""

import click
from googleapiclient.errors import HttpError

from . import get_service, http_error_message
from ..messages import MessageService


@click.command()
@click.argument("message_ids", nargs=-1, required=True)
@click.option(
    "--permanently",
    is_flag=True,
    help="Permanently delete instead of moving to Trash (irreversible)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt")
@click.pass_context
def rm(ctx, message_ids, permanently, yes):
    """Delete MESSAGE_IDS. Moves to Trash unless --permanently is given."""
    if permanently and not yes:
        click.confirm(
            f"Permanently delete {len(message_ids)} message(s)? This cannot be undone.",
            abort=True,
        )

    svc = MessageService(get_service(ctx))
    for mid in message_ids:
        try:
            if permanently:
                svc.delete(mid)
                click.echo(f"{mid}: permanently deleted")
            else:
                svc.trash(mid)
                click.echo(f"{mid}: moved to Trash")
        except HttpError as e:
            click.echo(f"{mid}: {http_error_message(e)}", err=True)
