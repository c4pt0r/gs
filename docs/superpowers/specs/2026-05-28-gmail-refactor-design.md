# Design: gmailtail → c4pt0r/gmail (full Gmail management CLI)

Date: 2026-05-28
Status: Approved (architectural decisions confirmed via AskUserQuestion)

## Goal

Refactor the read-only `gmailtail` monitoring tool into `gmail` — a full Gmail
management CLI that can also **send (with attachments), delete, mark read/unread,
create & manage labels, and move messages between labels**, while preserving the
existing `tail` (streaming monitor) and `repl` (interactive) capabilities.

## Confirmed decisions

1. **CLI shape:** `click` command **group** with subcommands (not flat flags).
2. **Delete semantics:** default = move to Trash (reversible); `--permanently` = hard delete.
3. **OAuth scope:** single full scope `https://mail.google.com/`.
4. **Rename:** clean break — command/package/config dir all become `gmail`
   (`~/.gmail/`); no `gmailtail` alias retained.

## 1. Rename / project skeleton

- Package dir `gmailtail/` → `gmail/`; console command `gmailtail` → `gmail`.
- Config dir `~/.gmailtail/` → `~/.gmail/` (tokens, checkpoint, cache.db).
- Update: `pyproject.toml` (name, scripts, packages, sdist, coverage source,
  isort known_first_party, mypy), `install.sh`, `Makefile`, `README.md`,
  `gmailtail.yaml.example` → `gmail.yaml.example`, `tests/`, and the existing
  skill `.claude/skills/using-gmailtail/` → `using-gmail/`.

## 2. CLI: single command → click group

`gmail/cli.py` becomes `@click.group()`. Shared options (auth
`--credentials/--auth-token/--cached-auth-token/--force-headless/--ignore-token`,
plus `--verbose/--quiet/--config-file`) live on the group and are stored in
`ctx.obj`. Each subcommand is its own module under `gmail/commands/` to keep
files small and focused.

| Subcommand | Purpose |
|------------|---------|
| `gmail tail` | Existing streaming monitor (all current flags preserved) |
| `gmail repl` | Existing interactive shell |
| `gmail read <id> [--mark-read]` | Display one message in full; optionally mark read |
| `gmail mark <id...> --read \| --unread` | Change read state only (no display) |
| `gmail send --to --cc --bcc --subject --body/--body-file --attach(repeat) --html` | Compose & send, multiple attachments, HTML body |
| `gmail rm <id...> [--permanently]` | Trash by default; permanent delete with flag |
| `gmail label ls\|create <n>\|rm <n>\|rename <old> <new>` | Label CRUD |
| `gmail mv <id...> --to <label> [--from <label>]` | Add `--to` label; remove `--from` label if given |
| `gmail profile` | Account info (promoted from REPL) |

## 3. Service-layer refactor (write capability)

Split the 491-line read-only `gmail_client.py` into focused modules:

- `gmail/client.py` — connection + read/query/parse (migrated existing logic; used by tail/repl).
- `gmail/messages.py` — `MessageService`: `send`, `trash`, `delete`,
  `mark_read`/`mark_unread`, `move` (built on `users.messages.modify` to
  add/remove `labelIds`).
- `gmail/labels.py` — `LabelService`: `list`/`create`/`delete`/`rename`, plus
  label name ↔ ID resolution (reusing existing `_convert_label_ids`).

All services take an authenticated `service` (or the client) so they are unit
testable with a mocked Gmail API.

## 4. Authentication

`auth.py` `SCOPES` → `['https://mail.google.com/']`. Cached token invalidated by
both rename and scope change → first run re-authenticates. README documents the
one-time re-auth. Service-account path unchanged (uses same SCOPES).

## 5. Sending email

Build a MIME message with `email.mime` (`MIMEMultipart` when attachments/HTML),
base64url-encode, then `service.users().messages().send(userId='me', body={'raw': ...})`.
- `--body-file -` reads body from stdin.
- `--html` sends body as `text/html`.
- `--attach` repeatable; guess MIME type via `mimetypes`.

## 6. Behavioral defaults (decided)

- `mv` without `--from` only adds the target label (tagging); with `--from`
  removes the source label too (true move, e.g. `--from INBOX` archives).
- `read`/`mark`/`rm`/`mv` accept multiple message ids (batch).
- `rm --permanently` requires the full scope (already chosen); plain `rm` uses trash.

## 7. Testing & quality (TDD)

- Each new capability: write a failing test first (mock the Gmail `service`
  object), then implement. RED → GREEN.
- Update existing `tests/test_config.py` references `gmailtail` → `gmail`; keep
  green after rename.
- Closeout: `uv run pytest`, `uv run black .`, `uv run flake8 gmail/`.

## 8. Implementation phases

0. Rename + command-group skeleton (tail/repl working, tests green).
1. OAuth scope upgrade to full mail scope.
2. Read-state: `mark` + `read` display.
3. Labels CRUD + `mv`.
4. Delete `rm` (trash / permanent).
5. `send` with attachments.
6. Docs: README, skill (`using-gmail`), install.sh, `gmail.yaml.example`.
