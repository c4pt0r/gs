"""`gmail mv` — move/tag messages between labels."""

import click

from . import get_service
from ..messages import MessageService
from ..labels import LabelService


@click.command()
@click.argument("message_ids", nargs=-1, required=True)
@click.option("--to", "to_label", required=True, help="Destination label to add")
@click.option(
    "--from",
    "from_label",
    help="Source label to remove (omit to just add the destination label)",
)
@click.pass_context
def mv(ctx, message_ids, to_label, from_label):
    """Add the --to label to MESSAGE_IDS; with --from, remove that label too."""
    service = get_service(ctx)
    labels = LabelService(service)
    messages = MessageService(service)

    add_ids = [labels.resolve_id(to_label)]
    remove_ids = [labels.resolve_id(from_label)] if from_label else None

    for mid in message_ids:
        messages.move(mid, add_label_ids=add_ids, remove_label_ids=remove_ids)
        if from_label:
            click.echo(f"{mid}: {from_label} -> {to_label}")
        else:
            click.echo(f"{mid}: + {to_label}")
