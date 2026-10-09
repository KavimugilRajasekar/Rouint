# Architecture Documentation

## Overview
Rouint is a modular Python application that manages API endpoint templates and executes them using the system's `curl` utility.

## System Design

### 1. Data Layer (`.rouint-data/`)
Rouint follows a local-first storage approach. All configurations are stored in JSON files within the project root.
- `config.json`: Global application settings.
- `registry.json`: Index of all saved endpoints for fast lookup.
- `endpoints/`: Individual JSON files for each endpoint template.
- `environments/`: Base URL configurations (e.g., local, staging, production).

### 2. Core Logic (`rouint.core`)
- **`manager.py`**: Handles the CRUD operations for endpoints. It ensures that filenames (slugs) are consistent and the registry is always in sync with the filesystem.
- **`parser.py`**: Responsible for the "Template" logic. It extracts `{placeholders}` and performs URL-encoded replacements at runtime.
- **`executor.py`**: The bridge to the OS. It constructs a safe `curl` command, executes it via `subprocess`, and parses the combined output (headers + body + metrics).

### 3. User Interface (`rouint.cli`)
The UI is split into two primary workflows to avoid redundancy:
- **Testing Workflow (`start`)**: Optimized for speed. Minimal prompts, direct execution.
- **Management Workflow (`list`)**: Optimized for organization. Provides a tabular view and a management sub-menu.

## Data Flow: Testing an Endpoint
1. `rouint start` $\rightarrow$ User selects an endpoint from the registry.
2. `parser.py` $\rightarrow$ Extracts placeholders from the path.
3. `cli.py` $\rightarrow$ Prompts user for values.
4. `parser.py` $\rightarrow$ Resolves the final URL.
5. `executor.py` $\rightarrow$ Calls `curl` $\rightarrow$ Returns `CurlResponse` object.
6. `cli.py` $\rightarrow$ Renders the response using `rich`.
