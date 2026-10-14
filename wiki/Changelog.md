# Changelog

> **[← Contributing](Contributing.md)** · Changelog · [Home →](Home.md)

---

All notable changes to Rouint are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.2] — 2026-10-13

### Changed

- **Endpoint selector — aligned path previews** — the `Select an endpoint` prompt now displays the configured path alongside each entry in dark grey. Name, method badge, and path are rendered in three perfectly aligned columns: names padded to the longest name, method badges padded to the longest badge (`[DELETE]`), and all paths starting at the same column. Makes it easy to distinguish endpoints with identical names or methods without opening their config.

---

## [1.1.1] — 2026-10-12

### Added

- **Interactive CLI launcher** — running `rouint` with no arguments opens a clean, keyboard-navigable menu using Questionary and prompt_toolkit. No more typing command names from memory.
- **Dynamic workspace-aware menu** — menu items reflect current workspace state:
  - `init` is hidden after the workspace is initialized
  - `add-base-url` shows `(required — no URLs configured yet)` when no environments exist
  - `add-new-api` shows `(required — no endpoints saved yet)` when empty
  - `start-test` is disabled until both URLs and endpoints exist
  - `clear-token` shows `(no token saved)` when no token file exists
- **Session-aware launcher loop** — after a subcommand completes, users are returned to the launcher menu instead of the terminal. State updates immediately.
- **Once-per-session banner** — the ASCII logo is displayed exactly once per session; subsequent command screens emit only their section headers.
- **Answered selection styling** — selected option name is highlighted in bright cyan bold; description and hints are styled in dark grey.
- **Windows hidden folder** — `.rouint-data/` is marked as a hidden directory on Windows using `SetFileAttributesW` (`FILE_ATTRIBUTE_HIDDEN`), matching `.git` behaviour in File Explorer.

### Fixed

- Failure to set the Windows hidden attribute is caught silently — workspace initialization always completes.

---

## [1.1.0] — 2026-10-12

### Added

- **Windows backend** — native PowerShell executor (`platforms/windows/executor.py`) using `Invoke-WebRequest`. All CLI commands and endpoint configurations work identically across Linux, macOS, and Windows.
- **PowerShell version support** — prefers `pwsh` (PowerShell 7+) with native `-Form` for file uploads; falls back to `powershell.exe` (Windows PowerShell 5.1) using .NET `MultipartFormDataContent`.
- **Cross-platform CI matrix** — GitHub Actions workflow running Ubuntu and Windows runners across Python 3.9, 3.10, 3.11, 3.12, and 3.13.
- **PyPI Trusted Publishing** — automated PyPI releases via OIDC; no API token required.
- **Test suite expansion** — `test_platform.py` (platform detection), `test_windows.py` (Windows backend), `test_cli.py` (CLI smoke tests).

### Fixed

- **Python 3.9 import crash** — `str | None` union syntax (PEP 604, Python 3.10+) replaced with `Optional[str]` throughout `cli.py` and `ui/components.py`. Running `rouint --help` on Python 3.9 no longer raises `TypeError`.
- **PowerShell 7 HTTP error handling** — `Invoke-WebRequest` raises `HttpResponseException` on 4xx/5xx. Added `-SkipHttpErrorCheck` so error responses are captured in the RESPONSE panel instead of crashing.
- **Windows terminal encoding** — `sys.stdout` and the Rich console are reconfigured to UTF-8 at startup, preventing garbled characters on terminals that default to a legacy code page.

---

## [1.0.0] — 2026-10-11

### Added

- **`rouint init`** — creates `.rouint-data/` workspace with `endpoints/`, `environments/`, `bodies/` subdirectories, `config.json`, `registry.json`, and an auto-generated `.gitignore`.
- **`rouint add-new-api`** — 7-step interactive wizard (method → path → headers → auth → body → files → name) with Esc step-back navigation at every step.
- **`rouint add-base-url`** — add or delete named environment URLs (local, staging, production).
- **`rouint start-test`** — endpoint and environment selection, `{placeholder}` resolution with URL encoding, cURL-based HTTP execution, and results across REQUEST / RESPONSE / METRICS panels. `--no-metrics` flag hides the metrics panel.
- **`rouint list-api`** — list, view, edit (pre-filled wizard), and delete saved endpoints.
- **`rouint clear-token`** — remove the saved temp Bearer token.
- **Placeholder system** — `{name}` syntax in paths and query strings; values URL-encoded automatically at test time.
- **Bearer Token auth** — token prompted at test time; scans response body and headers for common token fields; offers to save as temp token for reuse.
- **Custom header auth** — header name and value stored in endpoint config.
- **File attachment support** — `multipart/form-data` uploads via `curl -F`; multiple files per endpoint; `Content-Type` auto-removed when files are present.
- **Pretty-printed output** — JSON bodies pretty-printed in REQUEST and RESPONSE panels; panels expand to full terminal width.
- **Method-aware header defaults** — `Content-Type: application/json` pre-filled for POST/PUT/PATCH; `Accept: application/json` for all methods.

### Fixed

- **Placeholder `None` values** — parser now skips `None` values during path resolution instead of raising `TypeError`.
- **`pyproject.toml` classifier** — corrected `Topic :: Utilities` classifier.

### Changed

- `box_width()` simplified to return raw terminal width directly.
- Environment display table removed from `add-base-url` flow for a cleaner single-action experience.

---

## Version History Summary

| Version | Date | Headline |
|---------|------|---------|
| 1.1.2 | 2026-10-13 | Aligned path previews in endpoint selector |
| 1.1.1 | 2026-10-12 | Interactive TUI launcher, Windows hidden folder |
| 1.1.0 | 2026-10-12 | Windows backend, CI matrix, PyPI Trusted Publishing |
| 1.0.0 | 2026-10-11 | Initial release — full feature set on Linux/macOS |

---

Full diff links:

- [1.1.2 vs 1.1.1](https://github.com/KavimugilRajasekar/Rouint/compare/v1.1.1...v1.1.2)
- [1.1.1 vs 1.1.0](https://github.com/KavimugilRajasekar/Rouint/compare/v1.1.0...v1.1.1)
- [1.1.0 vs 1.0.0](https://github.com/KavimugilRajasekar/Rouint/compare/v1.0.0...v1.1.0)
- [1.0.0 release](https://github.com/KavimugilRajasekar/Rouint/releases/tag/v1.0.0)
