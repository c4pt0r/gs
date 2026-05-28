"""`gs calendar` — list calendars, list/create/delete events."""

import click
from googleapiclient.errors import HttpError

from . import get_calendar_service, http_error_message
from ..calendar_service import CalendarService, parse_when


@click.group()
def calendar():
    """Manage Google Calendar."""


@calendar.command("ls")
@click.pass_context
def calendar_ls(ctx):
    """List your calendars."""
    for cal in CalendarService(get_calendar_service(ctx)).list_calendars():
        primary = " (primary)" if cal.get("primary") else ""
        click.echo(f"{cal.get('id')}  {cal.get('summary')}{primary}")


@calendar.command("events")
@click.option("--calendar", "calendar_id", default="primary", help="Calendar id")
@click.option("--from", "time_from", help="Start of window (ISO, or now/today/+7d)")
@click.option("--to", "time_to", help="End of window (ISO, or now/today/+7d)")
@click.option("--max", "max_results", type=int, default=20, help="Max events")
@click.pass_context
def calendar_events(ctx, calendar_id, time_from, time_to, max_results):
    """List upcoming events in a time window."""
    svc = CalendarService(get_calendar_service(ctx))
    events = svc.list_events(
        calendar_id=calendar_id,
        time_min=parse_when(time_from) if time_from else None,
        time_max=parse_when(time_to) if time_to else None,
        max_results=max_results,
    )
    if not events:
        click.echo("No events found")
        return
    for ev in events:
        start = ev.get("start", {})
        when = start.get("dateTime") or start.get("date") or "?"
        click.echo(f"[{ev.get('id')}] {when}  {ev.get('summary', '(no title)')}")


@calendar.command("add")
@click.option("--summary", required=True, help="Event title")
@click.option("--start", required=True, help="Start (ISO datetime or YYYY-MM-DD)")
@click.option("--end", required=True, help="End (ISO datetime or YYYY-MM-DD)")
@click.option("--calendar", "calendar_id", default="primary", help="Calendar id")
@click.option("--description", help="Event description")
@click.option("--location", help="Event location")
@click.option("--timezone", help="IANA timezone (e.g. America/New_York)")
@click.option(
    "--attendee",
    "attendees",
    multiple=True,
    help="Invite an attendee by email (repeatable; emails an invitation)",
)
@click.pass_context
def calendar_add(
    ctx, summary, start, end, calendar_id, description, location, timezone, attendees
):
    """Create an event (optionally inviting attendees)."""
    created = CalendarService(get_calendar_service(ctx)).add_event(
        summary=summary,
        start=start,
        end=end,
        calendar_id=calendar_id,
        description=description,
        location=location,
        timezone=timezone,
        attendees=list(attendees),
    )
    click.echo(f"Created event {created.get('id')}: {created.get('summary')}")
    if attendees:
        click.echo(f"Invited: {', '.join(attendees)}")


@calendar.command("rm")
@click.argument("event_ids", nargs=-1, required=True)
@click.option("--calendar", "calendar_id", default="primary", help="Calendar id")
@click.pass_context
def calendar_rm(ctx, event_ids, calendar_id):
    """Delete one or more events."""
    svc = CalendarService(get_calendar_service(ctx))
    for eid in event_ids:
        try:
            svc.delete_event(eid, calendar_id=calendar_id)
            click.echo(f"{eid}: deleted")
        except HttpError as e:
            click.echo(f"{eid}: {http_error_message(e)}", err=True)
