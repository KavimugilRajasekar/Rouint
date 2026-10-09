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
        "-w", "\\n%{http_code}\\n%{time_total}",
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

        # The last line is time_total, second to last is http_code (from -w)
        # Note: curl -w output is appended to the end of the response
        time_total = float(lines[-1])
        status_code = int(lines[-2])

        # Response headers and body are everything before those two lines
        response_content = "\n".join(lines[:-2])

        # Split headers and body
        parts = response_content.split("\r\n\r\n", 1)
        if len(parts) < 2:
            parts = response_content.split("\n\n", 1)

        header_text = parts[0]
        body = parts[1] if len(parts) > 1 else ""

        # Parse headers
        headers = {}
        for line in header_text.splitlines()[1:]: # Skip first line (HTTP/1.1 200 OK)
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()

        return CurlResponse(
            status_code=status_code,
            headers=headers,
            body=body,
            elapsed_time=time_total
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
