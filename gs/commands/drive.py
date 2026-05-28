"""`gs drive` — list, upload, download, delete files and create folders."""

import os

import click
from googleapiclient.errors import HttpError

from . import get_drive_service, http_error_message
from ..drive_service import DriveService


@click.group()
def drive():
    """Manage Google Drive."""


@drive.command("ls")
@click.argument("query", required=False)
@click.option("--max", "max_results", type=int, default=100, help="Max files")
@click.pass_context
def drive_ls(ctx, query, max_results):
    """List files. QUERY is a Drive search query (e.g. "name contains 'report'")."""
    files = DriveService(get_drive_service(ctx)).list_files(
        query=query, max_results=max_results
    )
    if not files:
        click.echo("No files found")
        return
    for f in files:
        size = f.get("size", "-")
        click.echo(f"{f.get('id')}  {f.get('mimeType', '')}  {size}  {f.get('name')}")


@drive.command("upload")
@click.argument("path", type=click.Path(exists=True))
@click.option("--parent", help="Parent folder id")
@click.pass_context
def drive_upload(ctx, path, parent):
    """Upload a local file to Drive."""
    created = DriveService(get_drive_service(ctx)).upload(path, parent=parent)
    click.echo(f"Uploaded {created.get('name')} (id: {created.get('id')})")


@drive.command("download")
@click.argument("file_id")
@click.option("--output", "-o", help="Output path (default: ./<file_id>)")
@click.pass_context
def drive_download(ctx, file_id, output):
    """Download a file by id."""
    out = output or os.path.join(".", file_id)
    DriveService(get_drive_service(ctx)).download(file_id, out)
    click.echo(f"Downloaded to {out}")


@drive.command("mkdir")
@click.argument("name")
@click.option("--parent", help="Parent folder id")
@click.pass_context
def drive_mkdir(ctx, name, parent):
    """Create a folder."""
    created = DriveService(get_drive_service(ctx)).mkdir(name, parent=parent)
    click.echo(f"Created folder {created.get('name')} (id: {created.get('id')})")


@drive.command("rm")
@click.argument("file_ids", nargs=-1, required=True)
@click.option(
    "--permanently",
    is_flag=True,
    help="Permanently delete instead of moving to Trash (irreversible)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt")
@click.pass_context
def drive_rm(ctx, file_ids, permanently, yes):
    """Delete files. Moves to Trash unless --permanently is given."""
    if permanently and not yes:
        click.confirm(
            f"Permanently delete {len(file_ids)} file(s)? This cannot be undone.",
            abort=True,
        )
    svc = DriveService(get_drive_service(ctx))
    for fid in file_ids:
        try:
            svc.delete(fid, permanent=permanently)
            click.echo(f"{fid}: {'permanently deleted' if permanently else 'trashed'}")
        except HttpError as e:
            click.echo(f"{fid}: {http_error_message(e)}", err=True)
