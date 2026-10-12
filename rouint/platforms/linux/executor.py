"""
Linux (cURL) HTTP execution backend for Rouint.

This module preserves the original cURL-based execution logic from the
v1.0.0 executor.py, extracted into a platform-specific module.
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from rouint.core.executor import HttpResponse


def execute_request(
    url: str,
    method: str,
    headers: Dict[str, str],
    body: Optional[str] = None,
    files: Optional[List[Dict[str, str]]] = None,
) -> HttpResponse:
    """
    Executes an HTTP request using the system curl utility.

    When files are provided, the request is sent as multipart/form-data
    using curl's -F flag. The body (if any) is included as a form field
    named 'data'. Content-Type should not be set manually for multipart
    requests — curl sets it automatically with the correct boundary.
    """
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

        return HttpResponse(
            status_code=status_code,
            headers=response_headers,
            body=response_body,
            elapsed_time=time_total,
            status_line=status_line,
            response_size=size_download,
        )

    except subprocess.CalledProcessError as e:
        return HttpResponse(
            status_code=0, headers={}, body="", elapsed_time=0.0,
            error=f"curl error: {e.stderr.strip() or 'unknown curl error'}"
        )
    except FileNotFoundError:
        return HttpResponse(
            status_code=0, headers={}, body="", elapsed_time=0.0,
            error="curl is not installed or not found on PATH. Install curl and try again."
        )
    except Exception as e:
        return HttpResponse(
            status_code=0, headers={}, body="", elapsed_time=0.0,
            error=f"Unexpected error: {str(e)}"
        )
