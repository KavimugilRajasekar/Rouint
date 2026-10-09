# Rouint

A CLI-based API endpoint management and testing tool that wraps `curl`. Define endpoints once, organize them locally, and test them directly from the terminal — no GUI required.

Rouint stores endpoint configurations (method, path, headers, auth, body) in a local `.rouint-data/` directory and executes requests through the system's `curl` installation, giving you the transparency of a raw shell command with the organization of a professional API client.

## Features

- Define reusable API endpoint templates with `{placeholder}` parameters
- Interactive endpoint creation wizard with sensible defaults
- Support for GET, POST, PUT, PATCH, DELETE, HEAD, and OPTIONS methods
- Custom headers, authentication (Bearer Token, Custom), and JSON request bodies
- Automatic URL encoding of placeholder values
- Rich terminal output with formatted tables and color-coded responses
- Local-first storage — all data stays in your project directory

## Requirements

- Python 3.9 or higher
- `curl` installed and available on your `PATH`

## Installation

### From PyPI

```bash
pip install rouint
```

### From source (for development)

```bash
git clone https://github.com/KavimugilRajasekar/Rouint.git
cd Rouint
pip install -e ".[dev]"
```

## Quick Start

### 1. Initialize your workspace

Create the local `.rouint-data/` directory where endpoints and environments are stored.

```bash
rouint init
```

This creates:
```
.rouint-data/
├── config.json          # Workspace configuration
├── registry.json        # Endpoint registry (maps IDs to slugs)
├── endpoints/           # Endpoint configuration files
├── environments/        # Environment base URLs
│   └── local.json       # Default local environment (http://localhost:8000)
└── bodies/              # Request body files
```

### 2. Create an endpoint

```bash
rouint add-new
```

The interactive wizard walks you through:

1. **HTTP method** — choose from GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
2. **Path** — enter the endpoint path with optional placeholders (e.g., `/api/v1/users/{user_id}?active={is_active}`)
3. **Headers** — add custom headers or use defaults (`Accept: application/json`, `Content-Type: application/json`)
4. **Authentication** — choose None, Bearer Token, or Custom
5. **Body** — for POST/PUT/PATCH, optionally provide a JSON body
6. **Name** — give the endpoint a memorable name

The endpoint is saved as a JSON file under `.rouint-data/endpoints/`.

### 3. Test an endpoint

```bash
rouint start
```

Flow: Select endpoint → Enter placeholder values → Get response.

Rouint resolves all `{placeholder}` values you provide, URL-encodes them, constructs the final URL, executes the request via `curl`, and displays:

- HTTP status code
- Response time
- Response body

### 4. Manage your collection

```bash
rouint list
```

Flow: View table → Select endpoint → (Edit / View Configuration / Delete).

Displays all saved endpoints in a formatted table with name, method, and path. Select any endpoint to edit its configuration, view the raw JSON, or delete it.

## Placeholder System

Placeholders let you define a path template once and supply values at test time. Use `{parameter_name}` syntax:

| Path | Placeholders | Example Input |
|------|-------------|---------------|
| `/users/{user_id}` | `user_id` | `123` |
| `/search?q={query}` | `query` | `hello world!` |
| `/users/{user_id}/posts/{post_id}` | `user_id`, `post_id` | `123`, `456` |

Placeholder rules:
- Names must be alphanumeric + underscore (`[a-zA-Z0-9_]`)
- Names must be unique within an endpoint (no duplicates)
- Braces must be balanced
- Values are URL-encoded automatically (spaces → `%20`, etc.)

## Commands Reference

| Command | Description |
|---------|-------------|
| `rouint init` | Initialize the Rouint workspace |
| `rouint add-new` | Create a new endpoint interactively |
| `rouint start` | Select and test a saved endpoint |
| `rouint list` | View, edit, or delete saved endpoints |

## Project Structure

```
Rouint/
├── pyproject.toml          # Package metadata, dependencies, build config
├── LICENSE                 # MIT License
├── README.md               # This file
├── rouint/
│   ├── __init__.py         # Package init, exposes __version__
│   ├── cli.py              # Click CLI commands and interactive flows
│   ├── core/
│   │   ├── __init__.py
│   │   ├── executor.py     # curl wrapper and response parsing
│   │   ├── manager.py      # Endpoint CRUD operations (save, list, delete)
│   │   └── parser.py       # Placeholder extraction, resolution, path validation
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── config.py        # Workspace init, data paths, constants
│   │   └── logger.py       # Logging utilities (reserved for future use)
│   └── ui/
│       ├── __init__.py
│       ├── components.py   # UI components (reserved for future use)
│       └── screens.py       # UI screens (reserved for future use)
└── tests/
    ├── __init__.py
    ├── test_executor.py    # Tests for curl execution and response parsing
    └── test_parser.py      # Tests for placeholder extraction and validation
```

## Development

### Set up the dev environment

```bash
git clone https://github.com/KavimugilRajasekar/Rouint.git
cd Rouint
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run tests

```bash
pytest tests/ -v
```

### Build the package

```bash
python -m build
```

This produces:
- `dist/rouint-1.0.0-py3-none-any.whl` — the wheel
- `dist/rouint-1.0.0.tar.gz` — the source distribution

### Publish to PyPI

```bash
pip install twine
twine upload dist/*
```

You'll need a [PyPI account](https://pypi.org/account/register/) and an API token. After publishing, users can install with `pip install rouint`.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

Kavimugil Rajasekar (kavimugil28@gmail.com)
