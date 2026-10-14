# Commands Reference

> **[← Installation](Installation.md)** · Commands Reference · [Endpoint Wizard →](Endpoint-Wizard.md)

---

## Overview

Rouint exposes six commands. You can also launch an interactive menu by running `rouint` with no arguments.

| Command | One-line description |
|---------|---------------------|
| [`rouint init`](#rouint-init) | Initialize the workspace in the current directory |
| [`rouint add-base-url`](#rouint-add-base-url) | Add or delete a named base URL environment |
| [`rouint add-new-api`](#rouint-add-new-api) | Define a new API endpoint interactively |
| [`rouint start-test`](#rouint-start-test) | Select an endpoint and run an HTTP test |
| [`rouint list-api`](#rouint-list-api) | Browse, inspect, edit, or delete saved endpoints |
| [`rouint clear-token`](#rouint-clear-token) | Remove the saved temporary Bearer token |

---

## Interactive Launcher

Running `rouint` without any subcommand opens a keyboard-navigable menu:

```bash
rouint
```

```
◆  Command Launcher

  init            Initialize the Rouint workspace in current directory
  add-base-url    Add & manage global base URLs  (required — no URLs configured yet)
  add-new-api     Define a new API endpoint      (required — no endpoints saved yet)
  start-test      Run a test request             (disabled until URLs and endpoints exist)
  list-api        Browse saved endpoints         (disabled — no endpoints yet)
  clear-token     Clear saved Bearer token       (no token saved)
  help            Show inline command reference
  Exit
```

The menu reflects your workspace state dynamically — disabled items are shown with context hints. Press `Esc` or select **Exit** to quit.

---

## `rouint init`

Initializes the Rouint workspace in the current directory.

```bash
rouint init
```

Creates the following structure:

```
.rouint-data/
├── .gitignore       ← protects tokens, envs, and bodies from git
├── config.json      ← workspace version and default environment
├── registry.json    ← maps endpoint IDs to slugs
├── endpoints/       ← endpoint JSON files (safe to commit)
├── environments/    ← base URL files (gitignored)
└── bodies/          ← request body files (gitignored)
```

On **Windows**, `.rouint-data/` is automatically marked as a hidden directory so it behaves like `.git` in File Explorer.

**Notes:**
- Run once per project, in your project root
- Re-running on an initialized workspace prints a message and exits safely
- No flags or options

---

## `rouint add-base-url`

Adds or removes a named base URL environment.

```bash
rouint add-base-url
```

You will be prompted to choose one action:

```
? What would you like to do?
❯ Add a new base URL
  Delete an environment
  Cancel
```

### Adding a URL

```
? Enter the base URL:  https://api.myapp.com
? Enter a label for this environment:  production
```

The URL is validated — it must start with `http://` or `https://` and have a host. Trailing slashes are stripped automatically.

**Example environments:**

```
local       →  http://127.0.0.1:8080
staging     →  https://staging.myapp.com
production  →  https://api.myapp.com
```

### Deleting a URL

Select an environment from the list and confirm deletion.

**Notes:**
- Environment files are stored in `.rouint-data/environments/` and are gitignored
- You can add as many environments as you need
- The environment is selected at test time, not when defining the endpoint

---

## `rouint add-new-api`

Launches the 7-step interactive endpoint creation wizard.

```bash
rouint add-new-api
```

At every step, press **Esc** to go back to the previous step.

The wizard collects:

| Step | What you define |
|------|----------------|
| 1 | HTTP method |
| 2 | Path (with optional `{placeholders}`) |
| 3 | Headers |
| 4 | Authentication |
| 5 | Request body |
| 6 | File attachments |
| 7 | Endpoint name |

See the [Endpoint Wizard](Endpoint-Wizard.md) page for a complete walkthrough.

---

## `rouint start-test`

Selects an endpoint and base URL, resolves placeholders, executes the request, and displays results.

```bash
rouint start-test
```

**With the metrics panel hidden:**

```bash
rouint start-test --no-metrics
```

### Flags

| Flag | Description |
|------|-------------|
| `--no-metrics` | Hide the METRICS panel (status, time, size) |

### Flow

```
Select endpoint  →  Select base URL  →  Fill {placeholders}  →  Execute  →  View results
```

### Output panels

```
┌─ REQUEST ──────────────────────────────────────────┐
│  POST /api/v1/auth/login HTTP/1.1                  │
│  Accept: application/json                          │
│  Content-Type: application/json                    │
│  Authorization: [REDACTED]                         │
│                                                    │
│  {                                                 │
│    "username": "alice",                            │
│    "password": "secret"                            │
│  }                                                 │
└────────────────────────────────────────────────────┘

┌─ RESPONSE ─────────────────────────────────────────┐
│  HTTP/1.1 200 OK                                   │
│  content-type: application/json                    │
│                                                    │
│  {                                                 │
│    "access_token": "eyJhbGci..."                   │
│  }                                                 │
└────────────────────────────────────────────────────┘

┌─ METRICS ──────────────────────────────────────────┐
│  Status   200 OK                                   │
│  Time     142 ms                                   │
│  Size     1.2 KB                                   │
└────────────────────────────────────────────────────┘
```

If a token is detected in the response, Rouint offers to save it as a temp token for reuse. See [Authentication](Authentication.md) for details.

---

## `rouint list-api`

Lists all saved endpoints and lets you manage them.

```bash
rouint list-api
```

```
? Select an endpoint:
❯ Login            [POST]   /api/v1/auth/login
  Get User By ID   [GET]    /api/v1/users/{id}
  List Users        [GET]    /api/v1/users
  — Exit —
```

Select an endpoint to see its action menu:

```
? What would you like to do?
❯ Edit Endpoint
  View Configuration
  Delete Endpoint
  Back
```

| Action | Behaviour |
|--------|-----------|
| **Edit** | Re-runs the 7-step wizard with existing values pre-filled |
| **View Configuration** | Prints the raw JSON config for the endpoint |
| **Delete** | Asks for confirmation, then permanently removes the endpoint |
| **Back** | Returns to the endpoint list |

---

## `rouint clear-token`

Removes the saved temporary Bearer token.

```bash
rouint clear-token
```

Deletes `.rouint-data/.temp_token` if it exists. Prints a confirmation message either way.

Use this when:
- Your token has expired and you want to re-authenticate cleanly
- You are switching to a different user account
- You want to clear credentials before committing or sharing

---

## Getting Help

```bash
rouint --help
rouint <command> --help
```

Example:

```bash
rouint start-test --help
```

```
Usage: rouint start-test [OPTIONS]

  Select an endpoint and base URL, then execute the HTTP request.

Options:
  --no-metrics  Hide the metrics panel from the output.
  --help        Show this message and exit.
```
