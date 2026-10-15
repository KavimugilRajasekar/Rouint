# Rouint Wiki

> **CLI-Based API Endpoint Management & Testing Tool**  
> Define endpoints once. Test them anywhere. No GUI required.

---

## What is Rouint?

Rouint is a terminal-native API client that replaces the GUI workflow of tools like Postman with a clean, keyboard-driven CLI experience. You define your API endpoints once through an interactive wizard, store them locally in your project, and fire them against any environment — all without leaving the terminal.

Under the hood, Rouint uses your system's native HTTP tooling:

- **Linux / macOS** — `curl` subprocess
- **Windows** — PowerShell `Invoke-WebRequest`

Everything stays local. No accounts, no cloud sync, no telemetry.

---

## Quick Start

```bash
# 1. Install
pip install rouint

# 2. Initialize workspace in your project directory
rouint init

# 3. Add a base URL
rouint add-base-url
#  → label: local
#  → URL:   http://127.0.0.1:8080

# 4. Create an endpoint
rouint add-new-api
#  → method: POST
#  → path:   /api/v1/auth/login
#  → name:   Login

# 5. Run your first test
rouint start-test
```

---

## Core Workflow

```
rouint init            ← set up workspace (once per project)
rouint add-base-url    ← register environments: local, staging, prod
rouint add-new-api     ← define endpoint templates with {placeholders}
rouint start-test      ← pick endpoint → pick env → fill values → run
rouint list-api        ← manage, edit, or delete saved endpoints
rouint clear-token     ← remove saved Bearer token
```

---

## Key Features at a Glance

| Feature | Description |
|---------|-------------|
| **Endpoint wizard** | 7-step interactive creation with Esc step-back navigation |
| **Placeholder system** | `{id}`, `{query}` in paths — values prompted at test time |
| **Multi-environment** | Switch between local / staging / production with one selection |
| **Authentication** | Bearer Token (with temp token reuse) and Custom header auth |
| **File uploads** | `multipart/form-data` via `curl -F` or PowerShell `-Form` |
| **Request / Response panels** | Pretty-printed JSON, full terminal width |
| **Metrics panel** | HTTP status, response time (ms), response size |
| **Cross-platform** | Linux, macOS, Windows — same commands, native backends |
| **Local-first storage** | All data in `.rouint-data/` — safe to keep in your project |
| **Git-safe** | Auto-generated `.gitignore` protects tokens and environment URLs |

---

## Wiki Pages

| Page | What it covers |
|------|----------------|
| [Installation](Installation.md) | PyPI, from source, platform requirements |
| [Commands Reference](Commands-Reference.md) | All 6 commands with flags and examples |
| [Endpoint Wizard](Endpoint-Wizard.md) | Step-by-step breakdown of `add-new-api` |
| [Placeholder System](Placeholder-System.md) | `{syntax}`, validation rules, URL encoding |
| [Authentication](Authentication.md) | Bearer Token, Custom header, temp token workflow |
| [Environments](Environments.md) | Base URL management, multi-environment setup |
| [File Attachments](File-Attachments.md) | multipart/form-data uploads, field names |
| [Platform Backends](Platform-Backends.md) | cURL vs PowerShell internals, version support |
| [Architecture](Architecture.md) | Module map, data flow, design principles |
| [Storage Format](Storage-Format.md) | `.rouint-data/` layout, endpoint JSON schema |
| [Contributing](Contributing.md) | Dev setup, tests, CI pipeline, PyPI release |
| [Changelog](Changelog.md) | Version history summary |

---

## Current Version

**v1.1.3** — Wrapper view (`--show-wrapper`), `--version` flag, auto clipboard copy, launcher improvements  
Released: 2026-10-15

See the full [Changelog](Changelog.md) for version history.

---

## Project Links

- **PyPI** — [pypi.org/project/rouint](https://pypi.org/project/rouint/)
- **GitHub** — [github.com/KavimugilRajasekar/Rouint](https://github.com/KavimugilRajasekar/Rouint)
- **Issues** — [github.com/KavimugilRajasekar/Rouint/issues](https://github.com/KavimugilRajasekar/Rouint/issues)

---

*Rouint is MIT licensed. Built by [Kavimugil Rajasekar](mailto:kavimugil28@gmail.com).*
