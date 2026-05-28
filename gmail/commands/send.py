"""`gmail send` — compose and send a message, optionally with attachments."""

import sys

import click

from . import get_service
from ..messages import MessageService


@click.command()
@click.option("--to", required=True, help="Recipient address(es), comma-separated")
@click.option("--cc", help="Cc address(es), comma-separated")
@click.option("--bcc", help="Bcc address(es), comma-separated")
@click.option("--subject", default="", help="Subject line")
@click.option("--body", help="Message body text")
@click.option(
    "--body-file",
    type=click.Path(),
    help="Read body from a file (use '-' for stdin)",
)
@click.option("--html", is_flag=True, help="Send the body as HTML")
@click.option(
    "--attach",
    "attachments",
    multiple=True,
    type=click.Path(exists=True),
    help="Attach a file (repeatable)",
)
@click.pass_context
def send(ctx, to, cc, bcc, subject, body, body_file, html, attachments):
    """Compose and send an email."""
    if body is not None and body_file:
        raise click.UsageError("Use only one of --body or --body-file")

    if body_file:
        if body_file == "-":
            body = sys.stdin.read()
        else:
            with open(body_file, "r") as fh:
                body = fh.read()
    if body is None:
        body = ""

    result = MessageService(get_service(ctx)).send(
        to=to,
        subject=subject,
        body=body,
        cc=cc,
        bcc=bcc,
        html=html,
        attachments=list(attachments),
    )
    click.echo(f"Sent (id: {result.get('id', 'unknown')})")
