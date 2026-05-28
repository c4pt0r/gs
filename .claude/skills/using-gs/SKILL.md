---
name: using-gs
description: Use when managing Google Suite from the command line with the `gs` CLI — Gmail (tail/stream as JSON, send with attachments, delete, mark read/unread, labels, move), Google Calendar (list calendars, list/create/delete events, invite attendees), Google Drive (list/upload/download/mkdir/delete), or authentication (gs auth login/logout/status). Covers the nested subcommand structure, combined OAuth scope, and per-command options.
---

# Using gs

## Overview

`gs` is a Google Suite CLI. Structure is `gs <service> <action>`:

```
gs auth      login | logout | status        # one token for all services
gs gmail     tail | send | read | mark | rm | mv | label | profile | repl
gs calendar  ls | events | add | rm
gs drive     ls | upload | download | mkdir | rm
```

Run from this repo with `uv run gs ...`, or `gs ...` if installed
(`uv pip install -e .`).

> Lineage: `gmailtail` → `gmail` → `gs`. `gmailtail --tail` is now `gs gmail tail --tail`.

## Authentication

One combined OAuth scope (Gmail full + Calendar + Drive) → one login covers all.

```bash
gs auth login --credentials credentials.json   # browser once; token at ~/.gs/tokens
gs auth status                                  # who am I / am I logged in
gs auth logout                                  # delete cached token
```

- Enable **Gmail, Calendar, and Drive APIs** in Google Cloud Console; OAuth 2.0
  Client ID (Desktop app) → download JSON.
- `gs auth login --auth-token key.json` for a service account; `--force-headless`
  for SSH/no-browser.
- Other commands reuse the cached token and error with "run gs auth login" if absent.
- Global options (`--credentials`, `--config-file`, `--verbose`, `--quiet`,
  `--ignore-token`, `--cached-auth-token`) go **before** the service:
  `gs --config-file gs.yaml gmail tail`.

## gmail

```bash
gs gmail tail --tail                      # stream new mail as JSON (follow)
gs gmail tail --once --format json-lines  # one-shot, pipe to jq
gs gmail tail --from x@y.com --query "subject:alert" --tail
gs gmail send --to a@x.com --subject Hi --body hello \
  --cc c@x.com --attach f.pdf --html --body-file -    # attach repeatable; - = stdin
gs gmail read <id> --mark-read            # display full JSON, optionally mark read
gs gmail mark <id...> --read|--unread     # bulk read state
gs gmail rm <id...>                       # Trash (reversible)
gs gmail rm <id...> --permanently --yes   # hard delete (prompts without -y)
gs gmail label ls|create <n>|rm <n>|rename <old> <new>
gs gmail mv <id...> --to Work [--from INBOX]   # --from removes source label
gs gmail profile ; gs gmail repl
```

## calendar

```bash
gs calendar ls                                 # list calendars
gs calendar events --from today --to +7d       # window: ISO or now/today/tomorrow/+7d/-2h
gs calendar add --summary "Mtg" --start 2026-06-01T10:00:00Z --end 2026-06-01T11:00:00Z \
  [--calendar <id>] [--location ..] [--timezone America/New_York]
gs calendar add --summary Holiday --start 2026-06-01 --end 2026-06-02   # date-only = all-day
gs calendar add --summary Coffee --start 2026-06-01T10:00:00-07:00 --end 2026-06-01T11:00:00-07:00 \
  --attendee a@x.com --attendee b@y.com    # repeatable; emails invitations (sendUpdates=all)
gs calendar rm <event-id...>
```

Timezones: `today`/`tomorrow` use **local** midnight; `now`/`+7d`/`-2h` are
relative. A `--start/--end` with an offset (`…-07:00`) or `Z` is honored as-is; a
naive value (no offset) is treated as **local** time unless `--timezone` is given.
Gmail message `timestamp` is local time with an explicit offset.

## drive

```bash
gs drive ls ["name contains 'report'"]    # optional Drive query
gs drive upload <local-file> [--parent <folder-id>]
gs drive download <file-id> -o out.pdf
gs drive mkdir <name> [--parent <folder-id>]
gs drive rm <file-id...>                   # Trash (reversible)
gs drive rm <file-id...> --permanently --yes
```

## Architecture (for editing the tool)

- `gs/cli.py` — top group; shared options in `ctx.obj` (propagates to subgroups).
- `gs/commands/` — one module per command; `auth.py`, `gmail_group.py`,
  `calendar.py`, `drive.py` define the subgroups. Helpers in `commands/__init__.py`:
  `build_config`, `get_auth`, `get_service` (gmail), `get_calendar_service`,
  `get_drive_service`, `get_client`.
- `gs/auth.py` — `GoogleAuth`: combined SCOPES, `credentials(allow_login)`,
  `service(api, version)`, `login/logout/status`, `NotAuthenticatedError`.
- Service layers: `gs/messages.py` + `gs/labels.py` (Gmail),
  `gs/calendar_service.py` (+ `parse_when`), `gs/drive_service.py`.
- `gs/client.py`/`gs/monitor.py` back `gs gmail tail`/`repl`.
- Tests mock the Google `service`: `tests/test_services.py`,
  `tests/test_calendar_drive.py`, `tests/test_cli.py` (CliRunner). `uv run pytest`.

## Common mistakes

- **Global options after the service** → `gs gmail tail --credentials …` fails;
  put `--credentials/--config-file/--verbose` before the service name.
- **Skipping `gs auth login`** → other commands won't open a browser; they error
  until you log in once.
- **Expecting `gs gmail tail` to stop** → with `--tail` it follows forever; use `--once`.
- **`rm` default is permanent** → no; default is Trash (Gmail and Drive). `--permanently`
  is irreversible and prompts unless `-y`.
- **`gmail mv` without `--from` removes the old label** → no; it only *adds* `--to`.
- **Stale token after upgrade** → scope changed; `gs auth logout` then `gs auth login`.
