import subprocess
import time
import json
from typing import Dict, Any, Optional
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

def execute_request(url: str, method: str, headers: Dict[str, str], body: Optional[str] = None) -> CurlResponse:
    """
    Executes an HTTP request using the system curl utility.
    """
    # Base curl command
    # -i: include protocol headers in output
    # -s: silent mode
    # -w: write out specific variables to stdout
    cmd = [
        "curl",
        "-i",
        "-s",
        "-X", method,
        "-w", "\\n%{http_code}\\n%{time_total}\\n%{size_download}",
        url
    ]

    # Add headers
    for key, value in headers.items():
        cmd.extend(["-H", f"{key}: {value}"])

    # Add body
    if body:
        cmd.extend(["-d", body])

    try:
        start_time = time.time()
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        end_time = time.time()

        output = process.stdout.strip()
        lines = output.splitlines()

        # The last three lines are: size_download, time_total, http_code (from -w)
        # Note: curl -w output is appended to the end of the response
        size_download = int(lines[-1])
        time_total = float(lines[-2])
        status_code = int(lines[-3])

        # Response headers and body are everything before those three lines
        response_content = "\n".join(lines[:-3])

        # Split headers and body
        parts = response_content.split("\r\n\r\n", 1)
        if len(parts) < 2:
            parts = response_content.split("\n\n", 1)

        header_text = parts[0]
        response_body = parts[1] if len(parts) > 1 else ""

        # Parse the status line (first line, e.g. "HTTP/1.1 200 OK")
        header_lines = header_text.splitlines()
        status_line = header_lines[0] if header_lines else ""

        # Parse headers
        response_headers = {}
        for line in header_lines[1:]:  # Skip first line (HTTP/1.1 200 OK)
            if ":" in line:
                k, v = line.split(":", 1)
                response_headers[k.strip()] = v.strip()

        return CurlResponse(
            status_code=status_code,
            headers=response_headers,
            body=response_body,
            elapsed_time=time_total,
            status_line=status_line,
            response_size=size_download
        )

    except subprocess.CalledProcessError as e:
        return CurlResponse(
            status_code=0,
            headers={},
            body="",
            elapsed_time=0.0,
            error=f"Curl error: {e.stderr}"
        )
    except Exception as e:
        return CurlResponse(
            status_code=0,
            headers={},
            body="",
            elapsed_time=0.0,
            error=f"Unexpected error: {str(e)}"
        )
