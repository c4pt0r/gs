"""`gmail profile` — show the authenticated account's profile."""

import click

from . import get_service


@click.command()
@click.pass_context
def profile(ctx):
    """Show account profile (email, message/thread totals, history id)."""
    p = get_service(ctx).users().getProfile(userId="me").execute()
    click.echo(f"Email:          {p.get('emailAddress')}")
    click.echo(f"Messages Total: {p.get('messagesTotal')}")
    click.echo(f"Threads Total:  {p.get('threadsTotal')}")
    click.echo(f"History ID:     {p.get('historyId')}")
