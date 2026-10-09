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

def get_workspace_root() -> Path:
    """Returns the path to the current working directory as workspace root."""
    return Path.cwd()

def get_data_path() -> Path:
    """Returns the absolute path to the .rouint-data directory."""
    return get_workspace_root() / DATA_DIR

def is_initialized() -> bool:
    """Checks if the Rouint workspace is initialized."""
    return (get_data_path() / CONFIG_FILE).exists()

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

        # Default local environment
        local_env = {
            "base_url": "http://localhost:8000"
        }
        with open(data_path / ENV_DIR / "local.json", "w") as f:
            json.dump(local_env, f, indent=2)

        # Create .gitignore for data dir
        with open(data_path / ".gitignore", "w") as f:
            f.write("# Ignore local secrets\n*.secret.json\n")

        return True, "Workspace initialized successfully."
    except Exception as e:
        return False, f"Error initializing workspace: {str(e)}"
