# gs

`gs` is a command-line tool for **Google Suite** — manage Gmail, Google Calendar,
and Google Drive from one CLI. It's organized as nested subcommands:
`gs <service> <action>`.

```
gs auth login|logout|status          # authentication (one token for all services)
gs gmail tail|send|read|mark|rm|mv|label|profile|repl
gs calendar ls|events|add|rm
gs drive ls|upload|download|mkdir|rm
```

> Evolved from `gmailtail` → `gmail` → `gs`. The old `gmailtail --tail` is now
> `gs gmail tail --tail`. See [Migration](#migration).

## Features

- **One sign-in** — a single OAuth consent covers Gmail, Calendar, and Drive
- **Gmail** — stream/monitor as JSON, send (with attachments), delete, mark
  read/unread, manage labels, move messages, interactive REPL
- **Calendar** — list calendars, list events (relative time windows), create &
  delete events
- **Drive** — list/search, upload, download, create folders, delete (trash or permanent)

## Quick Start

```bash
git clone https://github.com/c4pt0r/gs.git
cd gs
uv sync && uv pip install -e .

# Authenticate once (opens a browser, caches a token at ~/.gs/tokens)
gs auth login --credentials credentials.json

gs gmail tail --tail
gs calendar events --from today --to +7d
gs drive ls
```

## Authentication

`gs` uses one combined scope set (Gmail full + Calendar + Drive), so a single
`gs auth login` authorizes everything.

1. In [Google Cloud Console](https://console.cloud.google.com/): create/select a
   project and **enable the Gmail API, Google Calendar API, and Google Drive API**.
2. Create credentials → **OAuth 2.0 Client ID** → *Desktop application*; download the JSON.
3. `gs auth login --credentials credentials.json` (a browser opens once; the token
   is cached at `~/.gs/tokens`).

| Command | |
|---------|--|
| `gs auth login --credentials <file>` | Authenticate and cache a token |
| `gs auth login --auth-token <key.json>` | Service account (servers; domain-wide delegation) |
| `gs auth login --force-headless` | Console-based auth (no browser, e.g. SSH) |
| `gs auth status` | Show whether logged in and as which account |
| `gs auth logout` | Remove the cached token |

Other commands reuse the cached token; if it's missing they tell you to run
`gs auth login`.

### Global options

`--credentials`, `--auth-token`, `--cached-auth-token`, `--ignore-token`,
`--config-file`, `--verbose`, `--quiet` are **global** and go *before* the
service/command:

```bash
gs --config-file gs.yaml gmail tail
```

## Gmail — `gs gmail`

```bash
# Monitor / stream as JSON
gs gmail tail --tail
gs gmail tail --once --format json-lines | jq -r '.from.email + ": " + .subject'
gs gmail tail --from "noreply@github.com" --query "subject:alert" --tail

# Send (attachments repeatable, HTML, stdin body)
gs gmail send --to a@x.com --subject "Hi" --body "hello"
gs gmail send --to "a@x.com,b@y.com" --cc boss@x.com --subject Report \
  --body "see attached" --attach report.pdf --attach data.csv
echo body | gs gmail send --to a@x.com --subject Piped --body-file -

# Read state, display, delete
gs gmail read <id> --mark-read
gs gmail mark <id1> <id2> --read        # or --unread
gs gmail rm <id>                        # Trash (reversible)
gs gmail rm <id> --permanently --yes    # hard delete

# Labels & move
gs gmail label ls
gs gmail label create Work
gs gmail mv <id> --to Work --from INBOX  # archive INBOX → Work

# Interactive
gs gmail repl
```

## Calendar — `gs calendar`

```bash
gs calendar ls                                  # list calendars
gs calendar events --from today --to +7d        # events in a window
gs calendar events --calendar primary --max 50

# Create an event (ISO datetime, or YYYY-MM-DD for all-day)
gs calendar add --summary "Meeting" \
  --start 2026-06-01T10:00:00Z --end 2026-06-01T11:00:00Z \
  --location "Room 1" --timezone America/New_York
gs calendar rm <event-id>
```

Time inputs for `--from/--to` accept ISO 8601 or shortcuts: `now`, `today`,
`tomorrow`, `+7d`, `-2h`.

## Drive — `gs drive`

```bash
gs drive ls                                  # list files
gs drive ls "name contains 'report'"         # Drive query syntax
gs drive upload report.pdf --parent <folder-id>
gs drive download <file-id> -o ./report.pdf
gs drive mkdir "Reports"
gs drive rm <file-id>                         # Trash (reversible)
gs drive rm <file-id> --permanently --yes     # hard delete
```

## Configuration file

```bash
cp gs.yaml.example gs.yaml      # edit it
gs --config-file gs.yaml gmail tail
```

Sections (`auth`, `filters`, `output`, `monitoring`, `checkpoint`) configure
auth and the `gs gmail tail` behavior. See `gs.yaml.example`.

## Migration

- Single command is now **`gs`** with service subgroups; `gmail …` → `gs gmail …`.
- Authentication is now explicit: run **`gs auth login`** once (other commands no
  longer trigger the browser flow themselves).
- Scope expanded to Gmail + Calendar + Drive, so re-authenticate after upgrading.
- Config dir is `~/.gs/`; the config example is `gs.yaml.example`.

## Development

```bash
uv sync --extra dev
uv run pytest                     # tests (mock the Google API)
uv run black . && uv run isort .
uv run flake8 gs/ && uv run mypy gs/
```

## License

MIT License — see LICENSE file.
