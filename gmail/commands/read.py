"""`gmail read` — display a single message in full, optionally marking it read."""

import json

import click

from . import get_client
from ..messages import MessageService


@click.command()
@click.argument("message_id")
@click.option("--mark-read", is_flag=True, help="Also mark the message as read")
@click.pass_context
def read(ctx, message_id, mark_read):
    """Display MESSAGE_ID in full (headers, body, attachments) as JSON."""
    client = get_client(ctx)
    # Force full content for a single-message view.
    client.config.output.include_body = True
    client.config.output.include_attachments = True
    client.config.output.max_body_length = None

    message = client.get_parsed_message(message_id)
    if not message:
        raise click.ClickException(f"Message not found: {message_id}")

    click.echo(json.dumps(message, ensure_ascii=False, indent=2))

    if mark_read:
        MessageService(client.service).mark_read(message_id)
        click.echo(f"\n{message_id}: marked read", err=True)
