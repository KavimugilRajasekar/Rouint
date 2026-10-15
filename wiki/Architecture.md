# Architecture

> **[← Platform Backends](Platform-Backends.md)** · Architecture · [Storage Format →](Storage-Format.md)

---

## Overview

Rouint is structured into five layers. Each layer has a single responsibility, and layers communicate through well-defined interfaces. The CLI layer orchestrates everything; the platform backends are completely isolated from each other.

```
┌──────────────────────────────────────────────────┐
│                  CLI  (cli.py)                   │  ← Click commands, wizard flows
├──────────────────────────────────────────────────┤
│          UI  (ui/screens.py, ui/components.py)   │  ← Rich panels, Questionary menus
├──────────────────────────────────────────────────┤
│   Core  (core/executor.py, manager.py, parser.py)│  ← Dispatch, CRUD, placeholder logic
├──────────────────────────────────────────────────┤
│  Platforms  (platforms/linux, platforms/windows) │  ← OS-native HTTP backends
├──────────────────────────────────────────────────┤
│         Utils  (utils/config.py)                 │  ← Workspace init, paths
└──────────────────────────────────────────────────┘
                        │
             .rouint-data/  (local storage)
```

---

## Project Structure

```
Rouint/
├── pyproject.toml               ← package metadata, dependencies, entry point
├── LICENSE
├── README.md
├── CHANGELOG.md
├── ROUINT.md                    ← internal project spec
│
├── rouint/
│   ├── __init__.py              ← exposes __version__
│   ├── cli.py                   ← all 6 CLI commands and wizard flows
│   │
│   ├── core/
│   │   ├── executor.py          ← HttpResponse dataclass, URL/file validation, platform dispatch
│   │   ├── manager.py           ← EndpointManager: save, list, get, delete
│   │   └── parser.py            ← placeholder extraction, validation, resolution
│   │
│   ├── platforms/
│   │   ├── __init__.py          ← platform detection: get_platform()
│   │   ├── linux/
│   │   │   └── executor.py      ← cURL-based HTTP backend
│   │   └── windows/
│   │       └── executor.py      ← PowerShell-based HTTP backend
│   │
│   ├── ui/
│   │   ├── __init__.py          ← re-exports public UI symbols
│   │   ├── components.py        ← banner, header, box_width, session state
│   │   ├── screens.py           ← interactive launcher, workspace state, menu items
│   │   └── controls.py          ← custom keyboard controls for Questionary
│   │
│   └── utils/
│       ├── config.py            ← workspace init, path helpers, .gitignore generation
│       └── logger.py            ← minimal logging stub
│
└── tests/
    ├── test_executor.py         ← shared + platform executor tests
    ├── test_parser.py           ← placeholder and path validation tests
    ├── test_manager.py          ← endpoint CRUD tests
    ├── test_platform.py         ← platform detection tests
    ├── test_windows.py          ← Windows backend-specific tests
    ├── test_cli.py              ← CLI command smoke tests
    └── test_launcher.py         ← interactive launcher and workspace state tests
```

---

## Module Responsibilities

### `rouint/cli.py`

The main entry point. Implements all six Click commands and orchestrates wizard flows.

- Calls `utils/config.py` for workspace operations
- Calls `core/manager.py` for endpoint CRUD
- Calls `core/parser.py` for placeholder extraction and resolution
- Calls `core/executor.py` to dispatch HTTP requests
- Calls `ui/` for rendering and interactive prompts

### `rouint/core/executor.py`

Shared execution interface — the bridge between CLI and platform backends.

- Defines `HttpResponse` dataclass (used by all backends)
- Provides `validate_url()` and `validate_files()` — called before dispatch
- `execute_request()` — validates inputs, then delegates to the correct backend
- `CurlResponse` — backward-compatible alias for `HttpResponse`

### `rouint/core/manager.py`

Endpoint CRUD. Manages the lifecycle of endpoint JSON files.

| Method | Description |
|--------|-------------|
| `save_endpoint(...)` | Writes endpoint to `endpoints/<slug>.json`, updates registry |
| `get_endpoint(slug)` | Reads and validates a single endpoint config |
| `list_endpoints()` | Reads registry, loads all endpoint configs |
| `delete_endpoint(slug)` | Removes file and registry entry |

### `rouint/core/parser.py`

Placeholder logic. Pure functions with no side effects.

| Function | Description |
|----------|-------------|
| `extract_placeholders(path)` | Returns list of `{name}` values from a path string |
| `validate_path(path)` | Checks balanced braces and uniqueness |
| `resolve_placeholders(path, values)` | Substitutes and URL-encodes values |

### `rouint/platforms/__init__.py`

Runtime platform detection. Returns `"linux"`, `"windows"`, or `"unsupported"`. Used by tests and the dispatch logic.

### `rouint/platforms/linux/executor.py`

cURL backend. Builds a `subprocess.run` command, executes it, and parses curl's output into an `HttpResponse`.

### `rouint/platforms/windows/executor.py`

PowerShell backend. Generates a PowerShell script string, runs it via subprocess, and parses the output into an `HttpResponse`. Handles PS 7+ and PS 5.1 separately for file uploads.

### `rouint/ui/components.py`

Rich-based rendering components.

| Function | Description |
|----------|-------------|
| `display_header(subtitle)` | Prints the ASCII art banner (once per session) |
| `display_banner()` | Full landing page with available commands table |
| `box_width(console)` | Returns current terminal width for full-width panels |
| `set_in_launcher(val)` | Marks whether CLI is inside the interactive launcher |

### `rouint/ui/screens.py`

Interactive launcher and workspace state detection.

| Symbol | Description |
|--------|-------------|
| `WorkspaceState` | Dataclass: initialized, has_urls, has_endpoints, has_token |
| `get_workspace_state()` | Inspects `.rouint-data/` to build workspace state |
| `get_menu_items(state)` | Returns list of `MenuItem` objects with enabled/disabled state |
| `show_interactive_menu(...)` | Renders the Questionary prompt with dynamic state hints |
| `interactive_launcher()` | Full launcher loop — shown when `rouint` is called with no args |

### `rouint/utils/config.py`

Workspace file system operations.

| Function | Description |
|----------|-------------|
| `get_data_path()` | Returns `Path.cwd() / ".rouint-data"` |
| `is_initialized()` | Checks for `config.json` presence |
| `list_environments()` | Returns list of `{name, base_url}` dicts |
| `save_environment(name, url)` | Writes `environments/<name>.json` |
| `init_workspace()` | Creates full `.rouint-data/` structure with `.gitignore` |

---

## Data Flow

### `rouint add-new-api`

```
cli.py (add_new_api)
  └── wizard steps 1-7 (questionary prompts)
       └── core/parser.py → validate_path()
       └── core/manager.py → save_endpoint()
            └── .rouint-data/endpoints/<slug>.json
            └── .rouint-data/registry.json
```

### `rouint start-test`

```
cli.py (start_test)
  └── core/manager.py → list_endpoints()
  └── utils/config.py → list_environments()
  └── core/parser.py  → extract_placeholders(), resolve_placeholders()
  └── core/executor.py → execute_request()
       ├── validate_url(), validate_files()
       └── platforms/linux/executor.py  OR
           platforms/windows/executor.py
                └── subprocess (curl / pwsh)
                     └── HttpResponse
  └── ui/components.py → Rich panels (REQUEST, RESPONSE, METRICS)
  └── token scan → .rouint-data/.temp_token (if saved)
```

---

## Design Principles

| Principle | Implementation |
|-----------|---------------|
| **CLI-first** | Every operation is a typed terminal command |
| **Interactive when useful** | Wizards guide complex input; direct commands for simple ops |
| **Persistent local storage** | All data in `.rouint-data/`, nothing in env vars or cloud |
| **Deferred parameter values** | Placeholders defined at creation, values supplied at test time |
| **Fail loudly on bad input** | Validate immediately, re-prompt rather than warn |
| **Transparent execution** | Show the exact request (with redacted secrets) before the response |
| **Step-back navigation** | Esc at any wizard step goes back — no restart needed |
| **Platform parity** | Same CLI surface and endpoint format on all OSes |
| **No shell=True** | All subprocesses use list arguments — no injection risk |
| **Local-first git safety** | Auto-generated `.gitignore` protects secrets by default |
