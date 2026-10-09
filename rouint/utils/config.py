import os
import json
import logging
from pathlib import Path

# Constants
DATA_DIR = ".rouint-data"
CONFIG_FILE = "config.json"
REGISTRY_FILE = "registry.json"
ENV_DIR = "environments"
ENDPOINTS_DIR = "endpoints"
BODIES_DIR = "bodies"
TEMP_TOKEN_FILE = ".temp_token"

def get_workspace_root() -> Path:
    """Returns the path to the current working directory as workspace root."""
    return Path.cwd()

def get_data_path() -> Path:
    """Returns the absolute path to the .rouint-data directory."""
    return get_workspace_root() / DATA_DIR

def is_initialized() -> bool:
    """Checks if the Rouint workspace is initialized."""
    return (get_data_path() / CONFIG_FILE).exists()

def get_env_path() -> Path:
    """Returns the absolute path to the environments directory."""
    return get_data_path() / ENV_DIR

def list_environments() -> list[dict[str, str]]:
    """
    Lists all configured environments as a list of dicts:
    [{"name": "local", "base_url": "http://localhost:8000"}, ...]
    Returns an empty list if no environments are found.
    """
    env_path = get_env_path()
    if not env_path.exists():
        return []

    envs = []
    for env_file in sorted(env_path.glob("*.json")):
        with open(env_file, "r") as f:
            data = json.load(f)
        env_name = env_file.stem  # e.g. "local" from "local.json"
        envs.append({
            "name": env_name,
            "base_url": data.get("base_url", "")
        })
    return envs

def get_base_url(env_name: str) -> str:
    """Returns the base_url for a given environment name, or empty string if not found."""
    env_path = get_env_path() / f"{env_name}.json"
    if not env_path.exists():
        return ""
    with open(env_path, "r") as f:
        data = json.load(f)
    return data.get("base_url", "")

def save_environment(env_name: str, base_url: str):
    """
    Saves a new environment to .rouint-data/environments/<env_name>.json.
    If the environment already exists, it is overwritten.
    """
    env_dir = get_env_path()
    env_dir.mkdir(parents=True, exist_ok=True)
    env_path = env_dir / f"{env_name}.json"
    clean_url = base_url.strip().rstrip("/")
    with open(env_path, "w") as f:
        json.dump({"base_url": clean_url}, f, indent=2)

def init_workspace():
    """Initializes the Rouint workspace directory structure."""
    data_path = get_data_path()

    if is_initialized():
        return False, "Workspace already initialized."

    try:
        data_path.mkdir(exist_ok=True)
        (data_path / ENV_DIR).mkdir(exist_ok=True)
        (data_path / ENDPOINTS_DIR).mkdir(exist_ok=True)
        (data_path / BODIES_DIR).mkdir(exist_ok=True)

        # Default config
        config = {
            "version": "1.0",
            "default_env": "local"
        }
        with open(data_path / CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

        # Empty registry
        with open(data_path / REGISTRY_FILE, "w") as f:
            json.dump({}, f, indent=2)

        # Create .gitignore for data dir
        gitignore_content = """\
# =============================================================
# Rouint workspace — .gitignore
# =============================================================
# This file controls what gets committed when .rouint-data/
# is tracked by git.
#
# SAFE to commit   : endpoints/   registry.json   config.json
# NOT safe to commit: environments/  .temp_token   bodies/
# =============================================================

# --- Sensitive: never commit ---

# Environment files contain real base URLs (local, staging, prod)
environments/

# Temp Bearer token saved after a successful auth response
.temp_token

# Request bodies may contain credentials or PII
bodies/

# Any explicitly marked secret files
*.secret.json

# --- Editor / OS noise ---
.DS_Store
Thumbs.db
"""
        with open(data_path / ".gitignore", "w") as f:
            f.write(gitignore_content)

        return True, "Workspace initialized successfully."
    except Exception as e:
        return False, f"Error initializing workspace: {str(e)}"
