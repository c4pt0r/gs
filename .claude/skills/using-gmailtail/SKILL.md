---
name: using-gmailtail
description: Use when monitoring, tailing, filtering, or exporting Gmail messages as JSON from the command line, or when exploring a Gmail account interactively — covers gmailtail auth setup, CLI flags, filters, output formats, checkpoints, caching, and REPL commands.
---

# Using gmailtail

## Overview

`gmailtail` monitors a Gmail inbox and streams matching messages to stdout as JSON — like `tail -f` for email. It's built for piping into `jq` and automation. It also has an interactive REPL for ad-hoc searches.

Two modes:
- **Stream mode** (default) — fetch/monitor messages, print JSON, exit or keep polling.
- **REPL mode** (`--repl` / `-i`) — interactive shell for browsing labels and running queries.

Run from this repo with `uv run gmailtail ...`, or `gmailtail ...` if installed.

## First-time setup

1. In [Google Cloud Console](https://console.cloud.google.com/): create a project, enable the **Gmail API**, create an **OAuth 2.0 Client ID** for a *Desktop application*, download the JSON.
2. First run opens a browser for consent: `gmailtail --credentials credentials.json --once`.
3. The token is cached at `~/.gmailtail/tokens`, so later runs don't need `--credentials` again.

| Auth flag | Use |
|-----------|-----|
| `--credentials PATH` | OAuth2 client JSON (interactive/personal use) |
| `--auth-token PATH` | Service account key (servers; needs domain-wide delegation) |
| `--cached-auth-token PATH` | Token cache location (default `~/.gmailtail/tokens`) |
| `--force-headless` | Console-based auth when no browser is available (e.g. SSH) |
| `--ignore-token` | Ignore cached token and re-authenticate |

## Quick reference — common runs

```bash
# Stream all new mail continuously
gmailtail --tail

# One-shot dump (run once, then exit) — good for piping
gmailtail --once --format json-lines

# Filter by sender, with a Gmail search query
gmailtail --from "noreply@github.com" --tail
gmailtail --query "subject:alert OR subject:error" --tail

# Unread only / with attachments / since a date
gmailtail --unread-only --tail
gmailtail --has-attachment --include-attachments --tail
gmailtail --since "2025-01-01T00:00:00Z" --once

# Include body, pick fields
gmailtail --include-body --max-body-length 500 --once
gmailtail --fields "id,subject,from,timestamp" --once

# Resume where you left off
gmailtail --resume --tail
```

## Key flags

**Filtering:** `--query` (full Gmail search syntax), `--from`, `--to`, `--subject` (regex), `--label` (repeatable), `--has-attachment`, `--unread-only`, `--since` (ISO 8601).

**Output:** `--format {json,json-lines,compact}` (default `json`), `--pretty`, `--fields a,b,c`, `--include-body`, `--max-body-length N`, `--include-attachments`.

**Monitoring:** `--tail`/`-t` (continuous), `--once` (run once and exit), `--poll-interval N` (default 30s), `--batch-size N` (default 10), `--max-messages N`.

**Checkpoint** (resume across restarts): `--resume`, `--reset-checkpoint`, `--checkpoint-file PATH` (default `~/.gmailtail/checkpoint`), `--checkpoint-interval N`.

**Cache:** `--no-cache`, `--cache-file PATH`, `--cache-max-age-days N` (default 30), `--clear-cache`.

**Other:** `--config-file PATH` (YAML), `--verbose`/`-v`, `--quiet` (only email JSON), `--log-file PATH`, `--dry-run`, `--repl`/`-i`.

Run `gmailtail --help` for the authoritative list.

> **Watch out:** `--tail` is `-t` (not `-f`), and `--repl` is `-i`. The README mislabels the tail short flag and calls the service-account flag `--service-account` — the actual flag is `--auth-token`.

## Output shape

Each message is a JSON object: `id`, `threadId`, `timestamp`, `subject`, `from {name,email}`, `to [...]`, `labels [...]`, `snippet`, and (when requested) `body`, `attachments [{filename,mimeType,size}]`.

Pipe `json-lines` into `jq`:
```bash
gmailtail --format json-lines --tail | jq -r '.from.email + ": " + .subject'
gmailtail --format json-lines --once | jq -r '.from.email' | sort | uniq -c | sort -nr
```

## Config file

For complex/repeated setups, use a YAML config instead of long flag lists:
```bash
cp gmailtail.yaml.example gmailtail.yaml   # edit it
gmailtail --config-file gmailtail.yaml
```
Sections: `auth`, `filters`, `output`, `monitoring`, `checkpoint`, plus top-level `verbose`/`quiet`/`log_file`. See `gmailtail.yaml.example` in the repo root.

## REPL mode

`gmailtail --credentials credentials.json --repl` opens an interactive shell. Commands:

| Command | What it does |
|---------|--------------|
| `ls [N]` / `ls LABEL [N]` | List recent emails (default 10) from current/given label |
| `ls --unread` / `ls -u [LABEL] [N]` | List unread emails |
| `tail [LABEL] [N]` | Alias for `ls` |
| `unread [LABEL] [N]` | Show unread emails |
| `query <gmail-search>` | Run a Gmail search query |
| `read <id> [without-body]` | Show one message in full detail |
| `use <LABEL>` | Switch the current label context |
| `labels` | List all labels |
| `profile` | Show account info (totals, history ID) |
| `config` | Show current configuration |
| `help` / `exit` / `quit` / Ctrl-D | Help / leave |

`ls` parses args by type: numbers are limits, text is a label (`ls 15 work` and `ls work 15` both work). Quote numeric label names: `ls "123" 5`.

## Common mistakes

- **No `--credentials` on first run** → no token to cache, auth fails. Pass it once; subsequent runs reuse `~/.gmailtail/tokens`.
- **Expecting `--tail` to stop** → it polls forever. Use `--once` for scripts/pipelines.
- **`--include-attachments` without it actually fetching** → also requires the data to be present; pair with `--has-attachment` to filter.
- **`-f` for tail** → that's wrong; the short flag is `-t`.
- **Headless server hangs on browser auth** → add `--force-headless`.
