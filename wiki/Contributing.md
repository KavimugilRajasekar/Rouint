# Contributing

> **[← Storage Format](Storage-Format.md)** · Contributing · [Changelog →](Changelog.md)

---

## Development Setup

### 1. Fork and clone

```bash
git clone https://github.com/KavimugilRajasekar/Rouint.git
cd Rouint
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install in editable mode with dev extras

```bash
pip install -e ".[dev]"
```

This installs:

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | `>=8.0` | Test runner |
| `build` | `>=1.0` | Package builder |
| `twine` | `>=5.0` | PyPI upload validator |

The `-e` flag means any changes to the source take effect immediately — no reinstall needed.

### 4. Verify

```bash
rouint --version
rouint --help
```

---

## Running Tests

```bash
pytest tests/ -v
```

Run a specific test file:

```bash
pytest tests/test_parser.py -v
pytest tests/test_executor.py -v
```

Run a specific test by name:

```bash
pytest tests/test_parser.py::test_extract_placeholders -v
```

### Test files

| File | What it tests |
|------|--------------|
| `test_executor.py` | `HttpResponse`, `validate_url`, `validate_files`, platform dispatch |
| `test_parser.py` | `extract_placeholders`, `validate_path`, `resolve_placeholders` |
| `test_manager.py` | `EndpointManager` CRUD: save, get, list, delete |
| `test_platform.py` | Platform detection (`get_platform`) |
| `test_windows.py` | Windows PowerShell backend (mocked) |
| `test_cli.py` | CLI command smoke tests via Click's `CliRunner` |
| `test_launcher.py` | Interactive launcher, workspace state, menu item logic |

---

## Code Style

- Follow the existing style in each file — no reformatter is enforced yet
- Keep functions focused and small
- Add docstrings to new public functions and classes
- Prefer explicit imports over wildcard imports
- Use `Optional[str]` instead of `str | None` for Python 3.9 compatibility

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, always releasable |
| `feature/<name>` | New features or fixes — opened against `main` |
| `v1.x.x` | Release snapshot branches for backporting patches |

Work on a feature branch, open a pull request to `main`, get it reviewed, then merge.

```bash
git checkout -b feature/my-new-feature
# ... make changes ...
git push -u origin feature/my-new-feature
# open a PR on GitHub
```

---

## CI Pipeline

Rouint uses GitHub Actions. The CI workflow (`.github/workflows/workflow.yml`) runs on every push to `main` or `feature/**` branches and on pull requests to `main`.

### Matrix

| Runner | Python versions |
|--------|----------------|
| `ubuntu-latest` | 3.9, 3.10, 3.11, 3.12, 3.13 |
| `windows-latest` | 3.9, 3.10, 3.11, 3.12, 3.13 |

**10 combinations total** — every commit is tested across all supported platforms and Python versions.

### Steps

1. Check out code
2. Set up Python
3. Install dependencies (`pip install -e ".[dev]"`)
4. Verify CLI installation (`rouint --help`)
5. Check module imports
6. Verify `curl` (Linux) or PowerShell (Windows) availability
7. Run tests (`pytest tests/ -v --tb=short`)
8. Build package (`python -m build`)
9. Validate distributions (`twine check dist/*`)

---

## Building the Package

```bash
python -m build
```

This produces:

```
dist/
├── rouint-1.1.2.tar.gz       ← source distribution
└── rouint-1.1.2-py3-none-any.whl  ← wheel
```

Validate before publishing:

```bash
python -m twine check dist/*
```

---

## PyPI Release Flow

Releases are automated via the `.github/workflows/publish.yml` workflow using **PyPI Trusted Publishing** (OIDC — no API token required).

### Steps

1. Merge all changes to `main` via a reviewed pull request
2. Update the version in two places:
   - `pyproject.toml` → `version = "1.x.x"`
   - `rouint/__init__.py` → `__version__ = "1.x.x"`
3. Commit the version bump:
   ```bash
   git commit -m "chore(release): bump version to 1.x.x"
   ```
4. Create and publish a **GitHub Release** tagged `v1.x.x`
5. The publish workflow triggers automatically:
   - Builds source + wheel distributions
   - Validates with `twine check`
   - Publishes to PyPI via OIDC

The package is live on PyPI within minutes of the release.

---

## Reporting Issues

Open an issue at [github.com/KavimugilRajasekar/Rouint/issues](https://github.com/KavimugilRajasekar/Rouint/issues).

Please include:
- Rouint version (`rouint --version`)
- Python version (`python --version`)
- Operating system and version
- Steps to reproduce
- Expected vs. actual behaviour
- Any error output (remove sensitive values)
