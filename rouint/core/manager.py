import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from rouint.utils.config import get_data_path, ENDPOINTS_DIR, ENV_DIR, REGISTRY_FILE

class EndpointManager:
    """Handles CRUD operations for API endpoints."""

    def __init__(self):
        self.data_path = get_data_path()
        self.endpoints_path = self.data_path / ENDPOINTS_DIR
        self.registry_path = self.data_path / REGISTRY_FILE

    def save_endpoint(self, name: str, method: str, path: str, base_url_ref: Optional[str], headers: Dict[str, str], auth: Dict[str, Any], body: Optional[str], slug: Optional[str] = None, files: Optional[List[Dict[str, str]]] = None) -> str:
        """Saves an endpoint configuration to a JSON file. Optionally updates an existing one via slug."""
        name = name.strip()
        if not name:
            raise ValueError("Endpoint name cannot be empty.")

        clean_path = path.strip()
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path

        if slug:
            target_slug = slug.strip().lower().replace(" ", "-").replace("/", "-")
        else:
            target_slug = name.lower().replace(" ", "-").replace("/", "-")

        if not target_slug:
            raise ValueError("Invalid endpoint name resulting in empty slug.")

        file_path = self.endpoints_path / f"{target_slug}.json"

        # Load existing ID if updating
        endpoint_id = f"ep_{target_slug}"
        if file_path.exists():
            with open(file_path, "r") as f:
                existing = json.load(f)
                endpoint_id = existing.get("id", endpoint_id)

        config = {
            "id": endpoint_id,
            "name": name,
            "method": method,
            "path": clean_path,
            "base_url_ref": base_url_ref,
            "headers": headers,
            "auth": auth,
            "body": body,
            "files": files or [],
        }

        with open(file_path, "w") as f:
            json.dump(config, f, indent=2)

        self._update_registry(endpoint_id, target_slug)
        return endpoint_id

    def get_endpoint(self, slug: str) -> Optional[Dict[str, Any]]:
        """Loads an endpoint configuration by its slug."""
        if not slug or not slug.strip():
            return None
        file_path = self.endpoints_path / f"{slug.strip()}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                ep = json.load(f)
            if ep and isinstance(ep, dict) and ep.get("name") and ep.get("path"):
                p = ep["path"].strip()
                if not p.startswith("/"):
                    p = "/" + p
                ep["path"] = p
                return ep
        except Exception:
            return None
        return None

    def list_endpoints(self) -> List[Dict[str, Any]]:
        """Lists all saved endpoints from the registry."""
        if not self.registry_path.exists():
            return []

        with open(self.registry_path, "r") as f:
            registry = json.load(f)

        endpoints = []
        for endpoint_id, slug in registry.items():
            if slug:
                ep = self.get_endpoint(slug)
                if ep:
                    endpoints.append(ep)
        return endpoints

    def delete_endpoint(self, slug: str) -> bool:
        """Deletes an endpoint file and removes it from the registry."""
        file_path = self.endpoints_path / f"{slug}.json"
        if not file_path.exists():
            return False

        # Remove from registry
        with open(self.registry_path, "r") as f:
            registry = json.load(f)

        # Find ID by slug
        endpoint_id = next((k for k, v in registry.items() if v == slug), None)
        if endpoint_id:
            del registry[endpoint_id]

        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2)

        file_path.unlink()
        return True

    def _update_registry(self, endpoint_id: str, slug: str):
        """Internal helper to keep the registry JSON up to date."""
        with open(self.registry_path, "r") as f:
            registry = json.load(f)

        registry[endpoint_id] = slug

        with open(self.registry_path, "w") as f:
            json.dump(registry, f, indent=2)
