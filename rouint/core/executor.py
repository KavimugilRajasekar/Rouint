"""
Shared HTTP execution interface for Rouint.

This module provides:
- The ``HttpResponse`` dataclass used by all platform backends.
- Shared validation functions (``validate_url``, ``validate_files``).
- The ``execute_request`` dispatcher that selects the appropriate
  platform backend at runtime.

The legacy ``CurlResponse`` name is preserved as an alias for backward
compatibility with existing tests and imports.
"""

import platform
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class HttpResponse:
    """Unified HTTP response container used by all platform backends."""
    status_code: int
    headers: Dict[str, str]
    body: str
    elapsed_time: float
    status_line: str = ""
    response_size: int = 0
    error: Optional[str] = None


# Backward-compatible alias — existing tests import CurlResponse
CurlResponse = HttpResponse


def validate_url(url: str) -> tuple[bool, str]:
    """Validates a URL before sending. Returns (ok, error_message)."""
    if not url or not url.strip():
        return False, "URL is empty."
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, f"Invalid URL '{url}': must start with http:// or https://"
    parts = url.split("/", 3)
    host = parts[2] if len(parts) > 2 else ""
    if not host:
        return False, f"Invalid URL '{url}': missing host."
    return True, ""


def validate_files(files: List[Dict[str, str]]) -> tuple[bool, str]:
    """Validates that all file paths exist and are readable. Returns (ok, error_message)."""
    for entry in files:
        file_path = entry.get("path", "").strip()
        if not file_path:
            return False, f"File entry is missing a path: {entry}"
        p = Path(file_path)
        if not p.exists():
            return False, f"File not found: {file_path}"
        if not p.is_file():
            return False, f"Path is not a file: {file_path}"
    return True, ""


def _get_platform_backend():
    """
    Import and return the appropriate platform-specific executor module.

    Returns the module's ``execute_request`` function.
    """
    system = platform.system().lower()

    if system == "windows":
        from rouint.platforms.windows.executor import execute_request as _execute
        return _execute
    else:
        # Linux, macOS, and other Unix-like systems use the cURL backend
        from rouint.platforms.linux.executor import execute_request as _execute
        return _execute


def execute_request(
    url: str,
    method: str,
    headers: Dict[str, str],
    body: Optional[str] = None,
    files: Optional[List[Dict[str, str]]] = None,
) -> HttpResponse:
    """
    Executes an HTTP request using the appropriate platform backend.

    On Linux/macOS, uses the cURL backend.
    On Windows, uses the PowerShell backend.

    Performs URL and file validation before delegating to the backend.
    """
    # Validate URL
    ok, err = validate_url(url)
    if not ok:
        return HttpResponse(status_code=0, headers={}, body="", elapsed_time=0.0, error=err)

    # Validate files if provided
    if files:
        ok, err = validate_files(files)
        if not ok:
            return HttpResponse(status_code=0, headers={}, body="", elapsed_time=0.0, error=err)

    # Dispatch to platform-specific backend
    backend_execute = _get_platform_backend()
    return backend_execute(url, method, headers, body, files)
