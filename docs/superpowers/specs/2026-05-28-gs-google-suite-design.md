# Design: gmail → gs (Google Suite CLI)

Date: 2026-05-28
Status: Approved (key decisions confirmed via AskUserQuestion)

## Goal

Rename the project to `gs` (Google Suite) and turn it into a multi-service CLI.
`gmail` becomes one service subgroup; add sibling subgroups `calendar` and
`drive`; promote authentication to a first-class `auth` subgroup.

## Confirmed decisions

- Package/command `gs`; config dir `~/.gs/`.
- **Single combined OAuth scope** (Gmail full + Calendar + Drive) — one
  `gs auth login` covers everything.
- Calendar surface: **core CRUD** (ls / events / add / rm).
- Drive surface: **core file ops** (ls / upload / download / rm / mkdir).
- Unauthenticated commands prompt to run `gs auth login` (no implicit browser flow).

## CLI structure

```
gs auth      login | logout | status
gs gmail     tail | send | read | mark | rm | mv | label | profile | repl
gs calendar  ls | events | add | rm
gs drive     ls | upload | download | mkdir | rm
```

`gs/cli.py` is the top click group; shared auth/global options live there and
propagate via `ctx.obj`. Each service is a click group in `gs/commands/`
(`auth.py`, `gmail_group.py`, `calendar.py`, `drive.py`).

## Auth

`gs/auth.py` `GoogleAuth`:
- `SCOPES = [mail.google.com, calendar, drive]`.
- `credentials(allow_login=False)` — cached token → refresh → service-account →
  (if allowed) OAuth flow; else `NotAuthenticatedError`.
- `service(api, version)` builds any API resource from the shared credentials.
- `login()`, `logout()`, `status()` back the `gs auth` commands.

## Service layers

- Gmail: existing `gs/messages.py`, `gs/labels.py`, `gs/client.py`, `gs/monitor.py`.
- Calendar: `gs/calendar_service.py` (`CalendarService` + `parse_when` relative
  time helper) over Calendar v3.
- Drive: `gs/drive_service.py` (`DriveService`, trash-by-default delete) over
  Drive v3, using `MediaFileUpload` / `MediaIoBaseDownload`.

No new dependencies (google-api-python-client already covers all three APIs).

## Testing (TDD)

Mock the Google `service` resource. `tests/test_services.py` (Gmail),
`tests/test_calendar_drive.py` (Calendar/Drive), `tests/test_cli.py` (nested
CliRunner wiring). `uv run pytest`.

## Phases

G1 rename → G2 auth refactor + auth group → G3 CLI restructure (gmail subgroup)
→ G4 calendar → G5 drive → G6 docs (README, skill `using-gs`, config example,
install/Makefile).
