"""`gmail label` — list, create, delete, and rename labels."""

import click

from . import get_service
from ..labels import LabelService


@click.group()
def label():
    """Manage Gmail labels."""


@label.command("ls")
@click.pass_context
def label_ls(ctx):
    """List all labels."""
    for lbl in LabelService(get_service(ctx)).list():
        click.echo(f"{lbl.get('name')} ({lbl.get('id')})")


@label.command("create")
@click.argument("name")
@click.pass_context
def label_create(ctx, name):
    """Create a new label called NAME."""
    created = LabelService(get_service(ctx)).create(name)
    click.echo(f"Created label {created.get('name')} ({created.get('id')})")


@label.command("rm")
@click.argument("name")
@click.pass_context
def label_rm(ctx, name):
    """Delete the label called NAME."""
    svc = LabelService(get_service(ctx))
    label_id = svc.resolve_id(name)
    svc.delete(label_id)
    click.echo(f"Deleted label {name}")


@label.command("rename")
@click.argument("old_name")
@click.argument("new_name")
@click.pass_context
def label_rename(ctx, old_name, new_name):
    """Rename label OLD_NAME to NEW_NAME."""
    svc = LabelService(get_service(ctx))
    label_id = svc.resolve_id(old_name)
    svc.rename(label_id, new_name)
    click.echo(f"Renamed {old_name} -> {new_name}")
