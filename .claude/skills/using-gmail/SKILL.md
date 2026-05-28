---
name: using-gmail
description: Use when managing or monitoring Gmail from the command line with the `gmail` CLI — sending mail (with attachments), tailing/streaming messages as JSON, deleting (trash or permanent), marking read/unread, creating & managing labels, moving messages between labels, or exploring an account interactively. Covers auth setup, the subcommand structure, and per-command options.
---

# Using gmail

## Overview

`gmail` is a Gmail management + monitoring CLI. It can stream mail as JSON
(`gmail tail`, like `tail -f`) and also **send, delete, mark read/unread, manage
labels, and move messages**. It's a click **command group**: `gmail <command>`.

Run from this repo with `uv run gmail ...`, or `gmail ...` if installed
(`uv pip install -e .`).

> Formerly `gmailtail` (read-only). `gmailtail --tail` is now `gmail tail --tail`;
> config dir moved `~/.gmailtail/` → `~/.gmail/`.

## Auth & global options (go BEFORE the subcommand)

Auth/global options live on the group, so they come first:
`gmail --credentials creds.json tail --from x@y.com`.

| Option | Use |
|--------|-----|
| `--credentials PATH` | OAuth2 client JSON (desktop app) |
| `--auth-token PATH` | Service account key (servers; domain-wide delegation) |
| `--cached-auth-token PATH` | Token cache (default `~/.gmail/tokens`) |
| `--force-headless` | Console auth when no browser (SSH) |
| `--ignore-token` | Re-authenticate, ignore cache |
| `--config-file PATH` | YAML config (see `gmail.yaml.example`) |
| `--verbose` / `--quiet` | Logging |

**Scope:** uses full `https://mail.google.com/` (needed for send/delete). First
run after upgrading from gmailtail re-authenticates. Set up OAuth in Google Cloud
Console (enable Gmail API → OAuth 2.0 Client ID → Desktop app), then
`gmail --credentials credentials.json profile` once.

## Commands quick reference

| Command | What it does |
|---------|--------------|
| `gmail tail [--tail] [filters] [output]` | Stream/monitor messages as JSON |
| `gmail send --to … --subject … --body …` | Send mail (`--attach` repeatable, `--html`, `--body-file -`) |
| `gmail read <id> [--mark-read]` | Display one message in full (JSON) |
| `gmail mark <id...> --read \| --unread` | Change read state (bulk) |
| `gmail rm <id...> [--permanently] [-y]` | Trash (default) or hard-delete |
| `gmail mv <id...> --to <label> [--from <label>]` | Add `--to` label; remove `--from` if given |
| `gmail label ls\|create <n>\|rm <n>\|rename <old> <new>` | Manage labels |
| `gmail profile` | Account info |
| `gmail repl` | Interactive shell |

Run `gmail <command> --help` for full options.

## Common examples

```bash
# Monitor
gmail tail --tail                                  # follow new mail
gmail tail --once --format json-lines              # one-shot, pipe-friendly
gmail tail --from "noreply@github.com" --tail
gmail tail --format json-lines --tail | jq -r '.from.email + ": " + .subject'

# Send (multiple recipients, attachments, HTML, stdin body)
gmail send --to a@x.com --subject Hi --body "hello"
gmail send --to "a@x.com,b@y.com" --cc boss@x.com --subject Report \
  --body "see attached" --attach report.pdf --attach data.csv
echo "body" | gmail send --to a@x.com --subject Piped --body-file -

# Read state
gmail mark m1 m2 --read
gmail read <id> --mark-read

# Delete (trash is reversible; permanent prompts unless -y)
gmail rm <id>
gmail rm <id> --permanently --yes

# Labels & move
gmail label create Work
gmail mv <id> --to Work --from INBOX   # archive INBOX → Work
gmail mv <id> --to Work                # just tag (no removal)
```

## Architecture (for editing the tool)

- `gmail/cli.py` — the click group; shared options stored in `ctx.obj`.
- `gmail/commands/` — one module per subcommand; `build_config`, `get_service`,
  `get_client` helpers live in `commands/__init__.py`.
- `gmail/messages.py` — `MessageService` (mark/trash/delete/move/send) +
  `build_raw_message` (MIME). `gmail/labels.py` — `LabelService` (CRUD + name→id).
- `gmail/client.py` (read/query/parse, used by tail/repl), `gmail/monitor.py`
  (`Monitor` backing tail), `gmail/auth.py` (scope + token).
- Tests mock the Gmail `service`: `tests/test_services.py`, `tests/test_cli.py`
  (CliRunner). Run `uv run pytest`.

## Common mistakes

- **Putting auth options after the subcommand** → `gmail tail --credentials …`
  fails; credentials/verbose/config-file go *before* the command.
- **Expecting `gmail tail` to stop** → with `--tail` it polls forever; use
  `--once` for scripts.
- **`gmail rm` permanently by default** → no; default is Trash (reversible).
  `--permanently` is the irreversible one and prompts unless `-y`.
- **`mv` without `--from` removes the old label** → no; without `--from` it only
  *adds* the destination label. Pass `--from INBOX` to actually move out of INBOX.
- **Old cached token after upgrade** → scope changed; delete `~/.gmail/tokens` or
  use `--ignore-token` to re-auth.
