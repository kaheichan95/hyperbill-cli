# hyperbill-cli

Command-line access to Hyperbill for **your own AI agent**: find billboards, run
campaigns and bidding webhooks, upload media, and read performance, wallet and
fulfillment data. Every command prints JSON; failures print
`{"error": {"code", "message", ...}}` to stderr with a non-zero exit code.

```bash
uv tool install ./hyperbill-cli     # or: pip install ./hyperbill-cli
hyperbill auth login                # once, by a human
hyperbill devices list
```

## Authentication model

The CLI acts **as you**, with exactly the permissions your browser session has.
It holds a Firebase session for your account and nothing else: no admin
credentials, no access to internal services. Firestore/Storage security rules
and the website's API checks apply unchanged.

### Signing in

| Method | Command | Use when |
| --- | --- | --- |
| Browser (recommended) | `hyperbill auth login` | Any account, including Google sign-in |
| Email + password | `hyperbill auth login --email you@example.com` | Headless machine; password is prompted, never taken from args or env |
| Injected session | `HYPERBILL_REFRESH_TOKEN=...` | Sandboxed agent runtimes that can't read `~/.config` |

How the browser login works (RFC 8252 loopback flow):

1. The CLI listens on `127.0.0.1:<random port>` and generates a random `state`.
2. It opens `https://hyperbill.co/en/cli/login?port=…&state=…` and prints a
   confirmation code (for example `C61A-9383`) that the page also shows. Only
   continue if the two codes match.
3. You sign in on that page. It creates a **separate** in-memory Firebase
   session, so your browser's own login is never shared or affected.
4. After you click **Authorize**, the page form-POSTs the new session's refresh
   token to `http://127.0.0.1:<port>/callback`. The host is hard-coded, so
   the token can't leave your machine and never appears in a URL. The
   listener checks `state` (constant-time) and the `Origin` header, accepts a
   single callback, and shuts down after 5 minutes.

### Storage and lifetime

- The refresh token is stored in `~/.config/hyperbill/credentials.json`
  (directory `0700`, file `0600`). ID tokens last one hour and stay in memory.
- Override the location with `HYPERBILL_CONFIG_DIR`.
- `hyperbill auth logout` deletes the local copy. Firebase can't revoke a
  single session from the client. To kill every session, change your
  password; an admin can also revoke them with `revokeRefreshTokens`.
- Tokens are only ever sent over HTTPS. `HYPERBILL_BASE_URL` may point at
  `http://localhost` for development but nowhere else over plain HTTP.

### What the CLI deliberately doesn't do

- **No account changes**: profile, payment methods, auto-recharge settings and
  top-ups stay on the website. The wallet commands are read-only.
- **Webhook tokens are masked** in output unless you pass `--show-token`, so
  they don't end up in agent transcripts.
- **Destructive commands** (`delete`, `terminate`) require `--yes`.

## Commands

```text
auth        login | logout | whoami
devices     list | get | stats | images | locations
campaigns   list | get | create | update | pause | resume | terminate | delete
            stats | simulate | fulfillments | export
webhooks    list | get | create | update | test | delete | stats | fulfillments | export
media       list | get | upload | moderate | download | url | delete | mcc
wallet      balance | transactions | invoice
dashboard
conditions  schema | validate
```

Run `hyperbill <group> <command> --help` for the options.

### Typical agent workflow

```bash
hyperbill devices list --region HK --vision
hyperbill devices stats HK.PEKINGROAD16.000 --days 7 --bucket day      # going price per second
hyperbill media mcc --search dental
hyperbill media upload ad.mp4 --mcc 8021                               # waits for moderation
hyperbill conditions schema                                           # targeting fields
hyperbill campaigns simulate --device HK.PEKINGROAD16.000 --price 0.5 --duration 15 \
  --condition @targeting.json
hyperbill campaigns create --name "Autumn promo" --media <mediaId> \
  --device HK.PEKINGROAD16.000 --budget 500 --price 0.5 --duration 15 \
  --start 2026-10-20T09:00+08:00 --end 2026-11-20T21:00+08:00 --condition @targeting.json
hyperbill campaigns stats <campaignId> --range 24H
```

List commands return `nextPageToken`; pass it back with `--page-token`.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Other failure |
| 2 | Invalid input |
| 3 | Not signed in / session ended: run `hyperbill auth login` |
| 4 | Not found |
| 5 | Conflict, e.g. `insufficient_funds` or a duplicate filename |

## Development

```bash
cd hyperbill-cli && uv venv && uv pip install -e '.[dev]' && .venv/bin/pytest
hyperbill --env dev auth login     # targets http://localhost:3000 + hyperbill-dev
```
