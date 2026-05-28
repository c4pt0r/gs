# gmail

A command-line tool to **manage and monitor Gmail**. Stream messages as JSON for
automation (`gmail tail`), and send, delete, label, and organize mail directly
from the terminal.

> Formerly `gmailtail` (a read-only monitor). It is now a full management CLI
> built around subcommands. See [Migration](#migration-from-gmailtail).

## Features

- **Real-time monitoring** — stream new mail as JSON with `gmail tail` (like `tail -f`)
- **Send mail** — compose and send, with attachments and HTML bodies
- **Delete** — move to Trash (default, reversible) or permanently delete
- **Mark read / unread** — change read state in bulk
- **Label management** — create, delete, rename, list labels
- **Move between labels** — add/remove labels on messages
- **Flexible filtering** — sender, subject, labels, attachments, Gmail search syntax
- **Multiple output formats** — JSON, JSON Lines, compact
- **Interactive REPL** — explore and query your account
- **Checkpoints & config files** — resume monitoring; YAML config for complex setups

## Quick Start

```bash
# Install (uv recommended)
git clone https://github.com/c4pt0r/gmail.git
cd gmail
uv sync
uv pip install -e .

# First run authenticates in the browser and caches a token at ~/.gmail/tokens
gmail --credentials credentials.json profile
```

## Authentication

`gmail` requires the full Gmail scope (`https://mail.google.com/`) because it can
send and delete mail.

1. Go to [Google Cloud Console](https://console.cloud.google.com/), create/select
   a project, and **enable the Gmail API**.
2. Create credentials → **OAuth 2.0 Client ID** → *Desktop application*; download the JSON.
3. First run: `gmail --credentials credentials.json profile`. A browser opens for
   consent; the token is cached at `~/.gmail/tokens` and reused afterward.

| Option | Use |
|--------|-----|
| `--credentials PATH` | OAuth2 client JSON (interactive/personal use) |
| `--auth-token PATH` | Service account key (servers; needs domain-wide delegation) |
| `--cached-auth-token PATH` | Token cache location (default `~/.gmail/tokens`) |
| `--force-headless` | Console-based auth when no browser is available (e.g. SSH) |
| `--ignore-token` | Ignore the cached token and re-authenticate |

These (plus `--verbose`, `--quiet`, `--config-file`, `--log-file`) are **global
options** and go *before* the subcommand:

```bash
gmail --credentials credentials.json tail --from "noreply@github.com"
```

## Commands

| Command | Purpose |
|---------|---------|
| `gmail tail` | Stream/monitor messages as JSON (the original behavior) |
| `gmail send` | Compose and send mail (attachments, HTML) |
| `gmail read <id>` | Display one message in full (optionally `--mark-read`) |
| `gmail mark <id...>` | Mark messages `--read` or `--unread` |
| `gmail rm <id...>` | Trash (default) or `--permanently` delete |
| `gmail mv <id...>` | Move/tag between labels (`--to`, `--from`) |
| `gmail label ...` | `ls` / `create` / `rm` / `rename` labels |
| `gmail profile` | Show account info |
| `gmail repl` | Interactive shell |

Run `gmail <command> --help` for full options.

### Monitoring — `gmail tail`

```bash
# Stream all new mail continuously
gmail tail --tail

# One-shot dump (run once, then exit) — good for piping
gmail tail --once --format json-lines

# Filters
gmail tail --from "noreply@github.com" --tail
gmail tail --query "subject:alert OR subject:error" --tail
gmail tail --unread-only --has-attachment --include-attachments --tail
gmail tail --since "2025-01-01T00:00:00Z" --once

# Output control
gmail tail --include-body --max-body-length 500 --once
gmail tail --fields "id,subject,from,timestamp" --format json-lines --once

# Resume from checkpoint
gmail tail --resume --tail
```

Pipe `json-lines` into `jq`:

```bash
gmail tail --format json-lines --tail | jq -r '.from.email + ": " + .subject'
gmail tail --format json-lines --once | jq -r '.from.email' | sort | uniq -c | sort -nr
```

### Sending — `gmail send`

```bash
# Simple text email
gmail send --to alice@example.com --subject "Hi" --body "Hello there"

# Multiple recipients, cc/bcc, attachments (repeat --attach)
gmail send --to "a@x.com,b@y.com" --cc boss@x.com --subject "Report" \
  --body "See attached." --attach report.pdf --attach data.csv

# HTML body, or read the body from a file / stdin
gmail send --to a@x.com --subject "Newsletter" --html --body "<h1>Hi</h1>"
echo "body text" | gmail send --to a@x.com --subject "Piped" --body-file -
```

### Read state — `gmail mark` / `gmail read`

```bash
gmail mark 18c5b2a4f2e1d8f0 --read
gmail mark m1 m2 m3 --unread          # bulk
gmail read 18c5b2a4f2e1d8f0           # display full message as JSON
gmail read 18c5b2a4f2e1d8f0 --mark-read
```

### Deleting — `gmail rm`

```bash
gmail rm 18c5b2a4f2e1d8f0             # move to Trash (reversible)
gmail rm m1 m2 m3                     # bulk trash
gmail rm m1 --permanently             # prompts for confirmation, then hard-deletes
gmail rm m1 --permanently --yes       # skip the prompt
```

### Labels — `gmail label` / `gmail mv`

```bash
gmail label ls
gmail label create "Work"
gmail label rename "Work" "Work/2026"
gmail label rm "Work/2026"

# Move = add destination label, optionally remove source label
gmail mv 18c5b2a4f2e1d8f0 --to "Work"               # just tag with Work
gmail mv 18c5b2a4f2e1d8f0 --to "Work" --from INBOX  # archive out of INBOX into Work
```

## Configuration file

```bash
cp gmail.yaml.example gmail.yaml   # edit it
gmail --config-file gmail.yaml tail
```

Sections: `auth`, `filters`, `output`, `monitoring`, `checkpoint`, plus top-level
`verbose`/`quiet`/`log_file`. See `gmail.yaml.example`.

## Interactive REPL

```bash
gmail --credentials credentials.json repl
```

Commands inside the REPL: `ls [--unread] [LABEL] [N]`, `tail`, `unread`,
`query <gmail-search>`, `read <id>`, `use <LABEL>`, `labels`, `profile`,
`config`, `help`, `exit`. The `ls` command parses args by type — numbers are
limits, text is a label (`ls work 15` and `ls 15 work` both work).

## Output format

Each message is a JSON object: `id`, `threadId`, `timestamp`, `subject`,
`from {name,email}`, `to [...]`, `labels [...]`, `snippet`, and (when requested)
`body`, `attachments [{filename,mimeType,size}]`.

## Migration from gmailtail

- The command is now `gmail` with **subcommands**; the old `gmailtail --tail`
  becomes `gmail tail --tail`.
- The config directory moved from `~/.gmailtail/` to `~/.gmail/`.
- The OAuth scope expanded to `https://mail.google.com/`, so the **first run
  re-authenticates** (the old cached token is no longer valid).
- The config-example file is now `gmail.yaml.example`.

## Development

```bash
uv sync --extra dev
uv run pytest                 # tests
uv run black . && uv run isort .
uv run flake8 gmail/ && uv run mypy gmail/
```

## License

MIT License — see LICENSE file.
