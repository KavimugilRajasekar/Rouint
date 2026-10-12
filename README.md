# Rouint

A CLI-based API endpoint management and testing tool. Define endpoints once, organize them locally, and test them against any environment directly from the terminal — no GUI required.

Rouint stores endpoint configurations (method, path, headers, auth, body, files) in a local `.rouint-data/` directory and executes requests using the system's native HTTP tools — `curl` on Linux/macOS and PowerShell on Windows — giving you the transparency of a raw command with the organization of a professional API client.

## Features

- Define reusable API endpoint templates with `{placeholder}` parameters
- Interactive endpoint creation wizard with step-back navigation (Esc to go back)
- Support for GET, POST, PUT, PATCH, DELETE, HEAD, and OPTIONS methods
- Custom headers with method-aware defaults
- Authentication — Bearer Token (with temp token reuse) and Custom header auth
- JSON request body with inline validation
- **File attachment support** — multipart/form-data uploads
- **Multi-environment support** — add local, staging, and production URLs; choose at test time
- Automatic URL encoding of placeholder values
- Pretty-printed JSON in both REQUEST and RESPONSE boxes
- Full-width terminal panels that adapt to your terminal size
- Input validation — base URLs, JSON bodies, and file paths checked on entry
- Local-first storage — all data stays in your project directory
- `.gitignore` auto-generated to keep environments and tokens out of version control
- **Cross-platform** — native backends for Linux/macOS (cURL) and Windows (PowerShell)

## Requirements

### All platforms

- Python 3.9 or higher

### Linux / macOS

- `curl` installed and available on your `PATH` (pre-installed on most systems)

### Windows

- PowerShell 5.1 (Windows PowerShell, included with Windows 10/11) or PowerShell 7+ (`pwsh`)
- No additional software required — PowerShell is included with Windows

## Platform Backends

Rouint automatically selects the appropriate HTTP backend based on your operating system:

| Platform | Backend | Tool |
|----------|---------|------|
| Linux | cURL | `curl` subprocess |
| macOS | cURL | `curl` subprocess |
| Windows | PowerShell | `Invoke-WebRequest` via `pwsh` or `powershell.exe` |

The backend is selected transparently — all CLI commands and endpoint configurations work identically across platforms.

### Supported PowerShell versions

- **PowerShell 7+** (`pwsh`) — preferred, supports native `-Form` parameter for file uploads
- **Windows PowerShell 5.1** (`powershell.exe`) — supported with .NET-based multipart upload fallback

Rouint prefers `pwsh` (PowerShell 7+) if available, and falls back to `powershell.exe` (Windows PowerShell 5.1). If neither is found, a clear error message is displayed.

### Platform limitations

- On Windows, file uploads on PowerShell 5.1 use a .NET `HttpClient`-based approach which may behave slightly differently from PowerShell 7+'s native `-Form` parameter.
- Request timing on Windows uses a .NET `Stopwatch` which provides millisecond-level accuracy.

## Installation

### From PyPI

**Linux / macOS:**

```bash
pip install rouint
```

**Windows:**

```powershell
py -m pip install rouint
```

### From source (for development)

```bash
git clone https://github.com/KavimugilRajasekar/Rouint.git
cd Rouint
pip install -e ".[dev]"
```

## Quick Start

### 1. Initialize your workspace

```bash
rouint init
```

Creates `.rouint-data/` in your current directory:

```
.rouint-data/
├── .gitignore           # Keeps environments, tokens, and bodies out of git
├── config.json          # Workspace configuration
├── registry.json        # Endpoint registry (maps IDs to slugs)
├── endpoints/           # Endpoint configuration files
├── environments/        # Base URLs (gitignored)
└── bodies/              # Request body files (gitignored)
```

### 2. Add your base URLs

```bash
rouint add-base-url
```

Choose **Add a new base URL**, enter the URL and a label:

```
local      → http://127.0.0.1:8080
staging    → https://staging.myapp.com
production → https://api.myapp.com
```

To remove a URL, choose **Delete an environment**.

### 3. Create an endpoint

```bash
rouint add-new-api
```

A 7-step wizard — press **Esc** at any step to go back to the previous one:

| Step | What you set |
|------|-------------|
| 1 | HTTP method — GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS |
| 2 | Path — with optional `{placeholder}` syntax |
| 3 | Headers — method-aware defaults, add/edit freely |
| 4 | Auth — None, Bearer Token, or Custom header |
| 5 | Body — JSON, validated on entry (POST/PUT/PATCH/DELETE) |
| 6 | Files — multipart attachments (POST/PUT/PATCH/DELETE) |
| 7 | Name — a memorable label |

The endpoint is saved without a base URL — you choose the environment at test time.

### 4. Test an endpoint

```bash
rouint start-test
```

Flow: **Select endpoint → Select base URL → Fill placeholders → Execute**

Displays three panels:

- **REQUEST** — method, path, headers, body (pretty-printed JSON)
- **RESPONSE** — status, headers, body (pretty-printed JSON)
- **METRICS** — HTTP status, response time, response size

Use `--no-metrics` to hide the metrics panel:

```bash
rouint start-test --no-metrics
```

If a token is detected in the response (Bearer/JWT), Rouint offers to save it as a temp token and automatically reuses it on subsequent Bearer-auth requests.

### 5. Manage your collection

```bash
rouint list-api
```

Select any endpoint to:
- **Edit** — re-run the wizard with existing values pre-filled; Esc steps back
- **View Configuration** — print the raw JSON
- **Delete** — remove permanently after confirmation

## Placeholder System

Use `{name}` syntax anywhere in the path or query string:

| Path | Placeholders | Example input |
|------|-------------|---------------|
| `/users/{id}` | `id` | `usr-101` |
| `/search?q={query}` | `query` | `hello world` → URL-encoded |
| `/users/{id}/posts/{post_id}` | `id`, `post_id` | `123`, `456` |

Rules:
- Names must match `[a-zA-Z0-9_]`
- Names must be unique within an endpoint
- Braces must be balanced
- Values are URL-encoded automatically at test time

## File Attachments

For POST/PUT/PATCH/DELETE endpoints, you can attach files during creation:

```
File path: /home/user/photo.jpg
Form field name: avatar
```

At test time, Rouint sends the request as `multipart/form-data`:
- **Linux/macOS:** via `curl -F` (curl sets the correct boundary automatically)
- **Windows:** via PowerShell's `-Form` parameter (PS 7+) or .NET `MultipartFormDataContent` (PS 5.1)

## Authentication

| Type | Behaviour |
|------|-----------| 
| None | No auth header added |
| Bearer Token | Prompts for token; offers saved temp token if available |
| Custom | Prompts for header name and value; saved in endpoint config |

**Temp token workflow:**
1. Login endpoint returns a token → Rouint detects it
2. "Save as temp token?" → saved to `.rouint-data/.temp_token`
3. Next Bearer-auth request → "Use saved temp token?" → auto-filled
4. `rouint clear-token` → removes it

## Git Safety

`rouint init` creates `.rouint-data/.gitignore` that protects:

```gitignore
environments/    # real base URLs
.temp_token      # live Bearer tokens
bodies/          # may contain credentials
*.secret.json    # explicitly sensitive files
```

Safe to commit: `endpoints/`, `registry.json`, `config.json`

## Commands Reference

| Command | Description |
|---------|-------------|
| `rouint init` | Initialize the Rouint workspace |
| `rouint add-base-url` | Add or delete a base URL environment |
| `rouint add-new-api` | Define a new API endpoint interactively |
| `rouint start-test` | Select an endpoint + base URL and run the test |
| `rouint list-api` | List, inspect, edit, or delete saved endpoints |
| `rouint clear-token` | Clear the saved temp Bearer token |

## Workflow at a Glance

```
rouint init          # set up workspace (once per project)
rouint add-base-url  # register: local → http://127.0.0.1:8080
rouint add-new-api   # define: POST /api/v1/auth/login
rouint start-test    # pick endpoint → pick URL → test!
rouint list-api      # manage saved endpoints
```

## Project Structure

```
Rouint/
├── pyproject.toml
├── LICENSE
├── README.md
├── rouint/
│   ├── __init__.py             # Package init, exposes __version__
│   ├── cli.py                  # Click CLI commands and interactive flows
│   ├── core/
│   │   ├── executor.py         # Shared execution interface & platform dispatch
│   │   ├── manager.py          # Endpoint CRUD (save, list, delete)
│   │   └── parser.py           # Placeholder extraction, resolution, validation
│   ├── platforms/
│   │   ├── __init__.py         # Platform detection
│   │   ├── linux/
│   │   │   └── executor.py     # cURL-based HTTP backend
│   │   └── windows/
│   │       └── executor.py     # PowerShell-based HTTP backend
│   ├── utils/
│   │   └── config.py           # Workspace init, data paths, .gitignore generation
│   └── ui/
│       └── components.py       # Banner, header, box_width
└── tests/
    ├── test_executor.py        # Shared + platform executor tests
    ├── test_parser.py          # Placeholder/path tests
    ├── test_manager.py         # Endpoint CRUD tests
    ├── test_platform.py        # Platform detection tests
    └── test_windows.py         # Windows-specific backend tests
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## Development

### Setup

```bash
git clone https://github.com/KavimugilRajasekar/Rouint.git
cd Rouint
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -e ".[dev]"
```

### Running tests

```bash
# All platforms
pytest tests/ -v

# Build and validate package
python -m build
python -m twine check dist/*
```

## Supported Python Versions

- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

Kavimugil Rajasekar (kavimugil28@gmail.com)
