# Installation

> **[← Home](Home.md)** · Installation · [Commands Reference →](Commands-Reference.md)

---

## Requirements

### All Platforms

| Requirement | Version |
|-------------|---------|
| Python | 3.9 or higher |

### Linux / macOS

| Requirement | Notes |
|-------------|-------|
| `curl` | Must be on your `PATH`. Pre-installed on most Linux distros and macOS. |

Verify curl is available:

```bash
curl --version
```

### Windows

| Requirement | Notes |
|-------------|-------|
| PowerShell 7+ (`pwsh`) | Preferred. Supports native `-Form` for file uploads. |
| PowerShell 5.1 (`powershell.exe`) | Fallback. Included with Windows 10/11. |

No additional software required — PowerShell ships with Windows.

---

## Install from PyPI

This is the recommended way to install Rouint.

**Linux / macOS:**

```bash
pip install rouint
```

**Windows:**

```powershell
py -m pip install rouint
```

Verify the installation:

```bash
rouint --version
rouint --help
```

---

## Install from Source

Use this method for development or to run the latest unreleased code.

```bash
# Clone the repository
git clone https://github.com/KavimugilRajasekar/Rouint.git
cd Rouint

# Create and activate a virtual environment
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Install with development extras
pip install -e ".[dev]"
```

The `-e` flag installs Rouint in editable mode — changes to the source code take effect immediately without reinstalling.

**Dev extras installed:**

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `build` | Package builder |
| `twine` | PyPI upload tool |

---

## Upgrading

```bash
pip install --upgrade rouint
```

---

## Uninstalling

```bash
pip uninstall rouint
```

Your `.rouint-data/` workspace directory is **not** removed by uninstalling — your saved endpoints are preserved.

---

## Supported Python Versions

| Python | Supported |
|--------|-----------|
| 3.9 | ✅ |
| 3.10 | ✅ |
| 3.11 | ✅ |
| 3.12 | ✅ |
| 3.13 | ✅ |

---

## Dependencies

Rouint pulls in three runtime dependencies:

| Package | Version Range | Purpose |
|---------|--------------|---------|
| `click` | `>=8.1,<9` | CLI framework |
| `rich` | `>=13.0,<16` | Terminal panels and styled output |
| `questionary` | `>=2.0,<3` | Interactive prompts and menus |

All are installed automatically from PyPI.

---

## Next Step

Once installed, initialize your workspace:

```bash
cd your-project-directory
rouint init
```

See [Commands Reference](Commands-Reference.md) for what to do next.
