# Changelog

All notable changes to Rouint are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.2] — 2026-10-13

### Changed

- **Endpoint selector — path preview in grey** — the `Select an endpoint` prompt now displays the configured path alongside each entry in dark grey (`\x1b[90m`). Name, method badge, and path are rendered in three perfectly aligned columns: names are padded to the longest name, method badges are padded to the longest badge (`[DELETE]`), and all paths start at the same column. This makes it easy to distinguish endpoints with the same name or method at a glance without opening their configuration.

---

## [1.1.1] — 2026-10-12

### Added

- **State-aware interactive CLI launcher** — typing `rouint` without subcommands opens a clean, keyboard-navigable interactive menu (`ui/screens.py`) using Questionary and prompt_toolkit, allowing instant command selection.
- **Dynamic command availability** — dynamically detects workspace state without modifying files: `init` is only shown in fresh/uninitialized workspaces and hidden thereafter; `add-base-url` displays `(required — no URLs configured yet)` when no base URLs are configured; `add-new-api` displays `(required — no endpoints saved yet)` when no endpoints are saved; `start-test` is disabled until both base URLs and endpoints exist with state-specific hints, and hints that `--no-metrics` is available; `list-api` is disabled when no endpoints exist; `clear-token` is disabled with `(no token saved)` when no Bearer token exists; `help` offers an inline command reference panel.
- **Seamless interactive session workflow** — users are retained inside the Command Launcher loop after subcommands like `init` complete rather than dumping them back to the terminal. Redundant command lists (such as `init`'s `Get started:` guide) are suppressed during interactive sessions, and the menu state dynamically updates immediately.
- **Once-per-session banner rendering** — the Rouint ASCII logo and workspace banner is displayed strictly once per session. Subsequent subcommand screens and menu re-renders emit only their section headers, eliminating duplicate banners in the terminal.
- **Answered selection styling & clean whitespace** — once an option is selected, the command name is highlighted in bright cyan bold (`class:answer`) while the description and hint are styled in dark grey (`class:ansibrightblack`), with excessive menu table padding whitespace stripped cleanly.
- **Strict terminal alignment** — consistent column layout across every menu entry (`name` padded to 16, `desc` padded to 34) ensuring all em dashes (`—`) and opening parentheses (`(`) align vertically across all states. Long descriptions are clamped gracefully.
- **Dark grey hint styling** — parenthesized hints are styled in dark grey (`\033[90m...\033[0m`) without color leakage into command names, descriptions, or subsequent menu items.
- **Direct command execution & clean exit** — selecting an enabled option invokes its existing Click handler directly. Selecting `Exit` or pressing `Esc`/`Ctrl+C` prints a dimmed, timestamped `Cancelled by user` notification and exits cleanly.

### Fixed

- **Windows hidden folder** — `.rouint-data/` is now marked as a hidden directory on Windows immediately after creation using `SetFileAttributesW` (`FILE_ATTRIBUTE_HIDDEN`, `ctypes`), so it behaves identically to `.git` — invisible in File Explorer without requiring "Show hidden files". Linux and macOS are unaffected; the dot-prefix convention already handles visibility there.

### Notes

- Failure to set the attribute (e.g. restricted environment) is caught silently — workspace initialization always completes regardless.
- No new dependencies introduced; `ctypes` is part of the Python standard library.

---

## [1.1.0] — 2026-10-12

### Added

- **Windows backend** — native PowerShell executor (`platforms/windows/executor.py`) using `Invoke-WebRequest`. All CLI commands and endpoint configurations work identically across Linux, macOS, and Windows.
- **PowerShell version support** — prefers `pwsh` (PowerShell 7+) with native `-Form` for file uploads; falls back to `powershell.exe` (Windows PowerShell 5.1) using .NET `MultipartFormDataContent`.
- **Cross-platform CI matrix** — GitHub Actions workflow running Ubuntu and Windows runners across Python 3.9, 3.10, 3.11, 3.12, and 3.13.
- **PyPI Trusted Publishing** — automated PyPI releases via OIDC; no API token required.
- **Test suite expansion** — `test_platform.py` (platform detection), `test_windows.py` (Windows backend), `test_cli.py` (CLI command smoke tests).

### Fixed

- **Python 3.9 import crash** — `str | None` union syntax (PEP 604, Python 3.10+ only) replaced with `Optional[str]` throughout `cli.py` and `ui/components.py`. Running `rouint --help` on Python 3.9 no longer raises `TypeError`.
- **PowerShell 7 HTTP error handling** — `Invoke-WebRequest` in PowerShell 7 raises `HttpResponseException` on 4xx/5xx responses. Added `-SkipHttpErrorCheck` so error responses are captured and displayed in the RESPONSE panel instead of crashing.
- **Windows terminal encoding** — `sys.stdout` and the Rich console are now reconfigured to UTF-8 at startup, preventing garbled characters on Windows terminals that default to a legacy code page.

---

## [1.0.0] — 2026-10-11

### Added

- **`rouint init`** — creates `.rouint-data/` workspace with `endpoints/`, `environments/`, `bodies/` subdirectories, `config.json`, `registry.json`, and an auto-generated `.gitignore` that protects `environments/`, `.temp_token`, `bodies/`, and `*.secret.json` from being committed.
- **`rouint add-new-api`** — 7-step interactive wizard (method → path → headers → auth → body → files → name) with Esc step-back navigation at every step.
- **`rouint add-base-url`** — add or delete named environment URLs (local, staging, production).
- **`rouint start-test`** — endpoint and environment selection, `{placeholder}` resolution with URL encoding, cURL-based HTTP execution, and results display across REQUEST / RESPONSE / METRICS panels. `--no-metrics` flag hides the metrics panel.
- **`rouint list-api`** — list, view configuration, edit (pre-filled wizard), and delete saved endpoints.
- **`rouint clear-token`** — remove the saved temp Bearer token.
- **Placeholder system** — `{name}` syntax in paths and query strings; values are URL-encoded automatically at test time. Names validated as `[a-zA-Z0-9_]`, must be unique, braces must be balanced.
- **Bearer Token auth** — token prompted at test time; scans response body and headers for common token fields (`access_token`, `token`, `jwt`, `id_token`, etc.) and offers to save as temp token for reuse on subsequent requests.
- **Custom header auth** — header name and value stored in endpoint config.
- **File attachment support** — multipart/form-data uploads via `curl -F`; multiple files per endpoint; `Content-Type` auto-removed from headers when files are present.
- **Pretty-printed output** — JSON bodies pretty-printed in both REQUEST and RESPONSE panels; panels expand to full terminal width dynamically.
- **Method-aware header defaults** — `Content-Type: application/json` pre-filled for POST/PUT/PATCH; `Accept: application/json` for all methods.

### Fixed

- **Placeholder `None` values** — parser now skips `None` values during path resolution instead of raising a `TypeError`.
- **`pyproject.toml` classifier** — corrected `Topic :: Utilities` classifier.

### Changed

- `box_width()` simplified to return raw terminal width directly.
- Environment display table removed from `add-base-url` flow for a cleaner single-action experience.
- Questionary prompt styles tuned; method badges aligned in the endpoint selection list.

---

[1.1.1]: https://github.com/KavimugilRajasekar/Rouint/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/KavimugilRajasekar/Rouint/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/KavimugilRajasekar/Rouint/releases/tag/v1.0.0
