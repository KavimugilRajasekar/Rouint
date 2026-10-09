import subprocess
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class CurlResponse:
    status_code: int
    headers: Dict[str, str]
    body: str
    elapsed_time: float
    status_line: str = ""
    response_size: int = 0
    error: Optional[str] = None


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


def execute_request(
    url: str,
    method: str,
    headers: Dict[str, str],
    body: Optional[str] = None,
    files: Optional[List[Dict[str, str]]] = None,
) -> CurlResponse:
    """
    Executes an HTTP request using the system curl utility.

    When files are provided, the request is sent as multipart/form-data
    using curl's -F flag. The body (if any) is included as a form field
    named 'data'. Content-Type should not be set manually for multipart
    requests — curl sets it automatically with the correct boundary.
    """
    # Validate URL
    ok, err = validate_url(url)
    if not ok:
        return CurlResponse(status_code=0, headers={}, body="", elapsed_time=0.0, error=err)

    # Validate files if provided
    if files:
        ok, err = validate_files(files)
        if not ok:
            return CurlResponse(status_code=0, headers={}, body="", elapsed_time=0.0, error=err)

    # Base curl command
    cmd = [
        "curl",
        "-i",
        "-s",
        "-X", method,
        "-w", "\\n%{http_code}\\n%{time_total}\\n%{size_download}",
        url,
    ]

    # File upload mode: multipart/form-data via -F
    if files:
        # Remove Content-Type if set — curl will set multipart boundary automatically
        filtered_headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
        for key, value in filtered_headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
        # Attach each file as a form field
        for entry in files:
            field_name = entry.get("field", "file")
            file_path = entry.get("path", "").strip()
            cmd.extend(["-F", f"{field_name}=@{file_path}"])
        # Include body as a form field named 'data' if present
        if body:
            cmd.extend(["-F", f"data={body}"])
    else:
        # Standard JSON/text request
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
        if body:
            cmd.extend(["-d", body])

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        output = process.stdout.strip()
        lines = output.splitlines()

        size_download = int(lines[-1])
        time_total = float(lines[-2])
        status_code = int(lines[-3])

        response_content = "\n".join(lines[:-3])

        parts = response_content.split("\r\n\r\n", 1)
        if len(parts) < 2:
            parts = response_content.split("\n\n", 1)

        header_text = parts[0]
        response_body = parts[1] if len(parts) > 1 else ""

        header_lines = header_text.splitlines()
        status_line = header_lines[0] if header_lines else ""

        response_headers = {}
        for line in header_lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                response_headers[k.strip()] = v.strip()

        return CurlResponse(
            status_code=status_code,
            headers=response_headers,
            body=response_body,
            elapsed_time=time_total,
            status_line=status_line,
            response_size=size_download,
        )

    except subprocess.CalledProcessError as e:
        return CurlResponse(
            status_code=0, headers={}, body="", elapsed_time=0.0,
            error=f"curl error: {e.stderr.strip() or 'unknown curl error'}"
        )
    except Exception as e:
        return CurlResponse(
            status_code=0, headers={}, body="", elapsed_time=0.0,
            error=f"Unexpected error: {str(e)}"
        )
