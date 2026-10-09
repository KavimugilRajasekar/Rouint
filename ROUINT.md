# Rouint — Project Specification & Implementation Reference

**Project Name:** Rouint
**Category:** CLI-Based API Endpoint Management and Testing Tool
**Inspiration:** Postman, with cURL as the underlying HTTP execution engine
**Interface:** Interactive, keyboard-driven terminal UI
**Core Philosophy:** Define endpoints once, organize them locally, and test them directly from the terminal.

---

## 1. Project Overview

Rouint is a CLI-based API endpoint testing tool that wraps the system-installed cURL utility. It provides a structured, interactive experience for creating, saving, organizing, editing, and testing API endpoints entirely from the terminal.

Instead of repeatedly constructing cURL commands manually or switching to a graphical API client, users define their endpoints once and reuse them whenever needed — against any registered environment.

Rouint stores endpoint configurations, headers, authentication settings, request bodies, and file attachments inside a `.rouint-data/` directory within the user's project root. When an endpoint is tested, Rouint executes the HTTP request through cURL and displays the request details, response headers, response body, and timing metrics directly in the terminal.

**The primary objective is to make API testing organized, reusable, transparent, and entirely terminal-oriented.**

---

## 2. Core Design Principles

1. **CLI-first** — Every major operation is accessible through a terminal command.
2. **Interactive when useful** — Guide users through endpoint creation and testing without requiring long command arguments.
3. **Persistent storage** — Saved endpoints remain available between sessions.
4. **cURL-powered execution** — Reuse the system's cURL installation rather than implementing an HTTP engine from scratch.
5. **Visible request and response** — Show the effective request and actual server response for debugging.
6. **Local-first storage** — Store all data locally; handle credentials carefully.
7. **Deferred parameter values** — Define placeholders when creating; prompt for values when testing.
8. **Step-back navigation** — Every wizard step supports Esc to go back to the previous step.
9. **Fail loudly on bad input** — Validate base URLs, JSON bodies, and file paths immediately on entry; re-prompt rather than warn.

---

## 3. Implemented Commands

| Command | Description |
|---|---|
| `rouint init` | Initialize the workspace in the current directory |
| `rouint add-base-url` | Add or delete a base URL environment |
| `rouint add-new-api` | Define a new API endpoint interactively |
| `rouint start-test` | Select endpoint + base URL and run the test |
| `rouint list-api` | List, inspect, edit, or delete saved endpoints |
| `rouint clear-token` | Clear the saved temp Bearer token |

---

## 4. Workspace Initialization

### Command

```bash
rouint init
```

Creates the `.rouint-data/` directory structure and a proper `.gitignore`:

```
.rouint-data/
├── .gitignore        # protects environments/, .temp_token, bodies/
├── config.json       # workspace version config
├── registry.json     # maps endpoint IDs → slugs
├── endpoints/        # endpoint JSON files (safe to commit)
├── environments/     # base URL files (gitignored)
└── bodies/           # request body files (gitignored)
```

The `.gitignore` inside `.rouint-data/` protects:

```gitignore
environments/     # real base URLs (local, staging, prod)
.temp_token       # live Bearer token
bodies/           # may contain credentials or PII
*.secret.json     # explicitly sensitive files
```

Safe to commit: `endpoints/`, `registry.json`, `config.json`

---

## 5. Creating a New Endpoint

### Command

```bash
rouint add-new-api
```

A 7-step interactive wizard. **Esc at any step goes back to the previous step.**

### Step 1 — HTTP Method

Choose from: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS.

Method-aware defaults are applied to subsequent steps (e.g. `Content-Type: application/json` added automatically for POST/PUT/PATCH).

### Step 2 — Path

Enter the path with optional `{placeholder}` syntax:

```
/api/v1/users/{id}
/api/v1/users?role={role}&page={page}
/api/v1/orders/{order_id}/tracking
```

Validation:
- Must not be empty
- Auto-prefixed with `/` if missing
- Braces must be balanced
- Placeholder names must be unique within the path

### Step 3 — Headers

Shows method-appropriate defaults:

| Method | Defaults |
|---|---|
| GET, DELETE, HEAD, OPTIONS | `Accept: application/json` |
| POST, PUT, PATCH | `Accept: application/json`, `Content-Type: application/json` |

User can add or edit headers. Entering `Key: Value` in one shot is caught and rejected with a hint.

If files are attached in step 6, `Content-Type` is automatically removed — curl sets it to `multipart/form-data` with the correct boundary.

### Step 4 — Authentication

| Type | Behaviour |
|---|---|
| None | No auth header |
| Bearer Token | Token prompted at test time; temp token offered if available |
| Custom | Prompts for header name + value; stored in endpoint config and added to headers |

### Step 5 — Body

Shown for: POST, PUT, PATCH, DELETE.

- "Does this request have a body?" confirm (default: Yes if body exists, No otherwise)
- JSON body validated immediately — re-prompts on invalid JSON, never accepts bad data
- Empty body not accepted if user said Yes

### Step 6 — File Attachments

Shown for: POST, PUT, PATCH, DELETE.

- "Attach files to this request?" confirm
- Each file: absolute path (validated to exist) + form field name
- Multiple files supported
- Sent as `multipart/form-data` via `curl -F`
- `Content-Type` auto-removed from headers when files are present

### Step 7 — Name

A memorable label for the endpoint. Required, re-prompts if empty.

---

## 6. Managing Base URLs

### Command

```bash
rouint add-base-url
```

Single-action command — pick one action and exit:

- **Add a new base URL** — enter URL (validated: must start with `http://` or `https://`), enter label
- **Delete an environment** — select from list, confirm (default: Yes)

Examples of valid environments:
```
local      → http://127.0.0.1:8080
staging    → https://staging.myapp.com
production → https://api.myapp.com
```

If no base URLs are configured when running `rouint start-test`, the user is directed to run `rouint add-base-url` first.

---

## 7. Testing an Endpoint

### Command

```bash
rouint start-test [--no-metrics]
```

**Flow:** Select endpoint → Select base URL → Fill placeholders → Execute → View results → Loop back

### Endpoint Selection

Endpoints listed with method badges aligned in a vertical column:

```
❯ Login           [POST]
  Get My Profile  [GET]
  List Users      [GET]
  Get User By ID  [GET]
  — Exit —
```

### Placeholder Resolution

For each `{placeholder}` in the path, the user is prompted for a value:

- Empty value → re-prompted
- Esc → loops back to endpoint selection
- Values are URL-encoded before being inserted into the URL

### Request Execution

Constructs the final URL, validates it, then executes via cURL.

**REQUEST box** shows:
- Method + path + HTTP version
- Effective headers (Authorization shown as `[REDACTED]`)
- File attachments (multipart mode)
- Request body (pretty-printed JSON)

**RESPONSE box** shows:
- Status line
- Response headers
- Response body (pretty-printed JSON if parseable, raw otherwise)

**METRICS box** shows (hidden with `--no-metrics`):
- HTTP status code
- Response time (ms)
- Response size (B or KB)

All panels expand to full terminal width dynamically.

### Token Capture

After each response, Rouint scans for tokens in:
- Response body JSON: `access_token`, `token`, `accessToken`, `jwt`, `auth_token`, `id_token`, `data.token`, `data.access_token`
- Response headers: `Authorization: Bearer <token>`, `Set-Cookie: token=<value>`

If found: "Save as temp token?" → saved to `.rouint-data/.temp_token` (chmod 0600).

On the next Bearer-auth request: "Use saved temp token?" → auto-filled.

### Error Handling

- Bad URL → clean error message, loops back
- File not found → clean error, loops back
- cURL error → shown in red RESPONSE box, loops back
- Ctrl+C / Esc → "Cancelled." exits cleanly
- Any unexpected error → friendly message + GitHub issues link, no traceback shown

---

## 8. Managing Endpoints

### Command

```bash
rouint list-api
```

Select any endpoint, then choose:

- **Edit Endpoint** — re-runs the 7-step wizard with existing values pre-filled; Esc steps back
- **View Configuration** — prints the raw JSON config
- **Delete Endpoint** — confirms then permanently removes
- **Back** — returns to endpoint list

Delete uses the endpoint's stored ID (not name) to find the file, so renames don't cause mismatches.

---

## 9. Clearing the Temp Token

```bash
rouint clear-token
```

Deletes `.rouint-data/.temp_token` if it exists.

---

## 10. Placeholder System

Use `{name}` syntax in path or query string:

| Path | Placeholders | Example |
|---|---|---|
| `/users/{id}` | `id` | `usr-101` |
| `/search?q={query}` | `query` | `hello world` → `hello%20world` |
| `/users/{id}/posts/{post_id}` | `id`, `post_id` | `123`, `456` |

Rules:
- Names: `[a-zA-Z0-9_]` only
- Must be unique within an endpoint
- Braces must be balanced
- Values URL-encoded automatically at test time

---

## 11. Endpoint Configuration Format

Each endpoint is stored as a JSON file under `.rouint-data/endpoints/`:

```json
{
  "id": "ep_get-user-by-id",
  "name": "Get User By ID",
  "method": "GET",
  "path": "/api/v1/users/{id}",
  "base_url_ref": null,
  "headers": {
    "Accept": "application/json"
  },
  "auth": {
    "type": "none"
  },
  "body": null,
  "files": []
}
```

For a POST with Bearer auth:

```json
{
  "id": "ep_login",
  "name": "Login",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "base_url_ref": null,
  "headers": {
    "Accept": "application/json",
    "Content-Type": "application/json"
  },
  "auth": {
    "type": "bearer token"
  },
  "body": "{\"username\": \"alice_admin\", \"password\": \"password123\"}",
  "files": []
}
```

---

## 12. `.rouint-data/` Directory Structure

```
project-root/
└── .rouint-data/
    ├── .gitignore           # auto-generated by rouint init
    ├── config.json          # workspace version + default env
    ├── registry.json        # { "ep_login": "login", ... }
    ├── endpoints/
    │   ├── login.json
    │   ├── get-user-by-id.json
    │   └── list-users.json
    ├── environments/        # gitignored
    │   ├── local.json       # { "base_url": "http://127.0.0.1:8080" }
    │   └── production.json
    ├── bodies/              # gitignored
    └── .temp_token          # gitignored, chmod 0600
```

---

## 13. Input Validation Summary

| Input | Validation | Behaviour on failure |
|---|---|---|
| Base URL | Must start with `http://` or `https://`, must have a host | Re-prompt |
| Endpoint path | Non-empty, balanced braces, unique placeholders | Re-prompt |
| JSON body | Must be valid parseable JSON | Re-prompt |
| File path | Must exist and be a regular file | Re-prompt |
| Placeholder values | Non-empty | Re-prompt |
| Endpoint name | Non-empty | Re-prompt |

---

## 14. Security Considerations

- `.rouint-data/.temp_token` created with `0600` permissions (owner read/write only)
- Token values shown as `[REDACTED]` in the REQUEST box
- Temp token stored only in the local workspace directory
- `Authorization` and `auth` headers redacted in all terminal output
- cURL invoked via `subprocess.run` with a list (no shell=True, no string concatenation)
- No tracebacks exposed to end users — unexpected errors show a friendly message

---

## 15. Project Structure

```
Rouint/
├── pyproject.toml
├── LICENSE
├── README.md
├── ROUINT.md
├── rouint/
│   ├── __init__.py         # exposes __version__
│   ├── cli.py              # all CLI commands and interactive flows
│   ├── core/
│   │   ├── executor.py     # curl wrapper, file upload, URL/file validation
│   │   ├── manager.py      # endpoint CRUD (save, list, delete)
│   │   └── parser.py       # placeholder extraction, resolution, validation
│   ├── utils/
│   │   └── config.py       # workspace init, data paths, .gitignore generation
│   └── ui/
│       └── components.py   # banner, header, box_width
└── tests/
    ├── test_executor.py
    ├── test_parser.py
    └── test_manager.py
```

---

## 16. Development

```bash
git clone https://github.com/KavimugilRajasekar/Rouint.git
cd Rouint
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
python -m build
twine upload dist/*
```

---

## Final Product Definition

**Rouint is a local-first, CLI-based API endpoint management and testing tool that uses cURL as its execution engine and provides an interactive terminal interface for defining, organizing, reusing, and testing HTTP requests.**

Its key workflow: create a reusable endpoint template once, supply dynamic placeholder values at test time, execute through cURL, and inspect the result — all without leaving the terminal.
