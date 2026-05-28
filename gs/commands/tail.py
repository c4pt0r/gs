"""`gs gmail tail` — stream/monitor messages as JSON (the original tail behavior)."""

import os

import click

from . import build_config
from ..monitor import Monitor


@click.command()
# Filter and query options
@click.option("--query", help="Gmail search query syntax")
@click.option(
    "--label", multiple=True, help="Filter by label (can be used multiple times)"
)
@click.option("--from", "from_email", help="Filter by sender email")
@click.option("--to", help="Filter by recipient email")
@click.option("--subject", help="Filter by subject pattern (regex supported)")
@click.option(
    "--has-attachment", is_flag=True, help="Only monitor emails with attachments"
)
@click.option("--unread-only", is_flag=True, help="Only monitor unread emails")
@click.option("--since", help="Start from specified datetime (ISO 8601 format)")
# Checkpoint options
@click.option(
    "--checkpoint-file",
    type=click.Path(),
    default=lambda: os.path.expanduser("~/.gs/checkpoint"),
    help="Checkpoint file path",
)
@click.option(
    "--checkpoint-interval",
    type=int,
    default=60,
    help="Checkpoint save interval in seconds",
)
@click.option("--resume", is_flag=True, help="Resume from last checkpoint")
@click.option(
    "--reset-checkpoint",
    is_flag=True,
    help="Reset checkpoint and start from current time",
)
# Output format options
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "json-lines", "compact"]),
    default="json",
    help="Output format",
)
@click.option("--fields", help="Output fields list (comma-separated)")
@click.option("--include-body", is_flag=True, help="Include email body")
@click.option(
    "--include-attachments", is_flag=True, help="Include attachment information"
)
@click.option(
    "--max-body-length", type=int, help="Maximum email body length in characters"
)
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output")
# Monitoring options
@click.option(
    "--poll-interval", type=int, default=30, help="Polling interval in seconds"
)
@click.option(
    "--batch-size", type=int, default=10, help="Number of emails to fetch per batch"
)
@click.option(
    "--tail",
    "-t",
    "tail",
    is_flag=True,
    help="Continuous monitoring mode (like tail -f)",
)
@click.option("--once", is_flag=True, help="Run once, do not continue monitoring")
@click.option("--max-messages", type=int, help="Maximum number of messages to process")
# Cache options
@click.option("--no-cache", is_flag=True, help="Disable caching entirely")
@click.option("--cache-file", type=click.Path(), help="Cache database file path")
@click.option(
    "--cache-max-age-days", type=int, default=30, help="Maximum cache age in days"
)
@click.option("--clear-cache", is_flag=True, help="Clear cache before running")
@click.option("--dry-run", is_flag=True, help="Simulate run without actual processing")
@click.pass_context
def tail(ctx, **kwargs):
    """Stream matching messages as JSON; with --tail, follow continuously."""
    config = build_config(ctx, **kwargs)
    Monitor(config).run()
