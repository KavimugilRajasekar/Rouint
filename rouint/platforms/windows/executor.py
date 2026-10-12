"""
Windows (PowerShell) HTTP execution backend for Rouint.

Uses PowerShell's Invoke-RestMethod / Invoke-WebRequest to execute HTTP
requests. Supports both PowerShell 7+ (pwsh) and Windows PowerShell 5.1
(powershell.exe).

Design decisions:
- Request data is passed via a temporary JSON script file to avoid
  command-line quoting issues and to prevent credentials from appearing
  in the process command line.
- The script file is cleaned up after execution.
- HTTP error responses (4xx/5xx) are still returned as valid responses
  so the user can inspect them.
"""

import json
import os
import subprocess
import tempfile
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from rouint.core.executor import HttpResponse


def _find_powershell() -> Optional[str]:
    """
    Locate a usable PowerShell executable.

    Prefers PowerShell 7+ (pwsh) over Windows PowerShell 5.1 (powershell).
    Returns the executable name or None if neither is found.
    """
    # Try pwsh first (PowerShell 7+)
    if shutil.which("pwsh"):
        return "pwsh"
    # Fall back to Windows PowerShell 5.1
    if shutil.which("powershell"):
        return "powershell"
    return None


def _build_powershell_script(
    url: str,
    method: str,
    headers: Dict[str, str],
    body: Optional[str] = None,
    files: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Build a PowerShell script string that executes the HTTP request and
    outputs a structured JSON result.

    The script uses Invoke-WebRequest (not Invoke-RestMethod) so we can
    access raw status codes, headers, and body regardless of content type.
    """
    lines = []

    # Set UTF-8 encoding for standard output and WebClient/ServicePoint
    lines.append("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8")
    lines.append("$OutputEncoding = [System.Text.Encoding]::UTF8")
    lines.append("[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12")
    lines.append("$ErrorActionPreference = 'Stop'")
    lines.append("")

    # Build headers hashtable
    lines.append("$headers = @{}")
    if files:
        # For multipart, skip Content-Type — PowerShell sets it with boundary
        for key, value in headers.items():
            if key.lower() != "content-type":
                escaped_key = key.replace("'", "''")
                escaped_value = value.replace("'", "''")
                lines.append(f"$headers['{escaped_key}'] = '{escaped_value}'")
    else:
        for key, value in headers.items():
            escaped_key = key.replace("'", "''")
            escaped_value = value.replace("'", "''")
            lines.append(f"$headers['{escaped_key}'] = '{escaped_value}'")

    lines.append("")

    # Build the request parameters
    lines.append("$params = @{")
    lines.append(f"    Uri = '{url.replace(chr(39), chr(39)+chr(39))}'")
    lines.append(f"    Method = '{method}'")
    lines.append("    Headers = $headers")
    lines.append("    UseBasicParsing = $true")
    lines.append("}")
    lines.append("")
    lines.append("if ($PSVersionTable.PSVersion.Major -ge 7) {")
    lines.append("    $params['SkipHttpErrorCheck'] = $true")
    lines.append("}")
    lines.append("")

    # Handle file uploads (multipart/form-data)
    if files:
        # PowerShell 7+ has native -Form support; for 5.1 we use a different approach
        lines.append("# Multipart file upload")
        lines.append("if ($PSVersionTable.PSVersion.Major -ge 7) {")
        lines.append("    $form = @{}")

        for entry in files:
            field_name = entry.get("field", "file")
            file_path = entry.get("path", "").strip()
            escaped_field = field_name.replace("'", "''")
            escaped_path = file_path.replace("'", "''")
            lines.append(f"    $form['{escaped_field}'] = Get-Item -LiteralPath '{escaped_path}'")

        if body:
            escaped_body = body.replace("'", "''")
            lines.append(f"    $form['data'] = '{escaped_body}'")

        lines.append("    $params['Form'] = $form")
        lines.append("} else {")
        # Windows PowerShell 5.1 multipart workaround
        lines.append("    Add-Type -AssemblyName 'System.Net.Http'")
        lines.append("    $multipartContent = [System.Net.Http.MultipartFormDataContent]::new()")

        for entry in files:
            field_name = entry.get("field", "file")
            file_path = entry.get("path", "").strip()
            escaped_field = field_name.replace("'", "''")
            escaped_path = file_path.replace("'", "''")
            lines.append(f"    $fileBytes = [System.IO.File]::ReadAllBytes('{escaped_path}')")
            lines.append(f"    $fileContent = [System.Net.Http.ByteArrayContent]::new($fileBytes)")
            file_name = Path(file_path).name.replace("'", "''")
            lines.append(f"    $fileContent.Headers.ContentDisposition = [System.Net.Http.Headers.ContentDispositionHeaderValue]::new('form-data')")
            lines.append(f"    $fileContent.Headers.ContentDisposition.Name = '\"{escaped_field}\"'")
            lines.append(f"    $fileContent.Headers.ContentDisposition.FileName = '\"{file_name}\"'")
            lines.append("    $multipartContent.Add($fileContent)")

        if body:
            escaped_body = body.replace("'", "''")
            lines.append(f"    $dataContent = [System.Net.Http.StringContent]::new('{escaped_body}')")
            lines.append("    $dataContent.Headers.ContentDisposition = [System.Net.Http.Headers.ContentDispositionHeaderValue]::new('form-data')")
            lines.append("    $dataContent.Headers.ContentDisposition.Name = '\"data\"'")
            lines.append("    $multipartContent.Add($dataContent)")

        lines.append("    $params['Body'] = $multipartContent")
        lines.append("    $params['ContentType'] = $multipartContent.Headers.ContentType.ToString()")
        lines.append("}")
    elif body:
        # JSON body — use -Body parameter
        # Encode body as UTF-8 bytes to avoid encoding issues
        escaped_body = body.replace("'", "''")
        lines.append(f"$bodyText = '{escaped_body}'")
        lines.append("$params['Body'] = [System.Text.Encoding]::UTF8.GetBytes($bodyText)")
        lines.append("")

    lines.append("")

    # Execute the request with timing
    lines.append("$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()")
    lines.append("try {")
    lines.append("    $response = Invoke-WebRequest @params -ErrorAction Stop")
    lines.append("    $stopwatch.Stop()")
    lines.append("} catch {")
    lines.append("    $stopwatch.Stop()")
    lines.append("    $ex = $_.Exception")
    lines.append("    if ($ex.Response) {")
    lines.append("        # HTTP error response (4xx, 5xx) — still read the response")
    lines.append("        $errResponse = $ex.Response")
    lines.append("        $errBody = ''")
    lines.append("        $errHeaders = @{}")
    lines.append("        $statusCode = 0")
    lines.append("        $statusDesc = ''")
    lines.append("        $protocolVersion = '1.1'")
    lines.append("")
    lines.append("        # PowerShell 7+ (.NET Core) HttpResponseMessage")
    lines.append("        if ($errResponse.GetType().FullName -like '*HttpResponseMessage*') {")
    lines.append("            $statusCode = [int]$errResponse.StatusCode")
    lines.append("            $statusDesc = $errResponse.ReasonPhrase")
    lines.append("            if ($errResponse.Version) { $protocolVersion = $errResponse.Version }")
    lines.append("            if ($errResponse.Content) {")
    lines.append("                try {")
    lines.append("                    $errBody = $errResponse.Content.ReadAsStringAsync().GetAwaiter().GetResult()")
    lines.append("                } catch {}")
    lines.append("            }")
    lines.append("            if ($errResponse.Headers) {")
    lines.append("                foreach ($h in $errResponse.Headers) {")
    lines.append("                    $errHeaders[$h.Key] = ($h.Value -join ', ')")
    lines.append("                }")
    lines.append("            }")
    lines.append("            if ($errResponse.Content -and $errResponse.Content.Headers) {")
    lines.append("                foreach ($h in $errResponse.Content.Headers) {")
    lines.append("                    $errHeaders[$h.Key] = ($h.Value -join ', ')")
    lines.append("                }")
    lines.append("            }")
    lines.append("        }")
    lines.append("        # Windows PowerShell 5.1 HttpWebResponse")
    lines.append("        elseif ($errResponse.GetResponseStream) {")
    lines.append("            $errStream = $errResponse.GetResponseStream()")
    lines.append("            $reader = [System.IO.StreamReader]::new($errStream)")
    lines.append("            $errBody = $reader.ReadToEnd()")
    lines.append("            $reader.Close()")
    lines.append("            $errStream.Close()")
    lines.append("")
    lines.append("            if ($errResponse.Headers) {")
    lines.append("                foreach ($key in $errResponse.Headers.AllKeys) {")
    lines.append("                    $errHeaders[$key] = $errResponse.Headers[$key]")
    lines.append("                }")
    lines.append("            }")
    lines.append("")
    lines.append("            $statusCode = [int]$errResponse.StatusCode")
    lines.append("            $statusDesc = $errResponse.StatusDescription")
    lines.append("            $protocolVersion = $errResponse.ProtocolVersion")
    lines.append("        }")
    lines.append("")
    lines.append("        if ($statusCode -gt 0) {")
    lines.append("            $result = @{")
    lines.append("                status_code = $statusCode")
    lines.append("                status_line = \"HTTP/$protocolVersion $statusCode $statusDesc\"")
    lines.append("                headers = $errHeaders")
    lines.append("                body = $errBody")
    lines.append("                elapsed_ms = $stopwatch.ElapsedMilliseconds")
    lines.append("                response_size = [System.Text.Encoding]::UTF8.GetByteCount($errBody)")
    lines.append("                error = $null")
    lines.append("            }")
    lines.append("            $result | ConvertTo-Json -Depth 10 -Compress")
    lines.append("            exit 0")
    lines.append("        }")
    lines.append("    }")
    lines.append("")
    lines.append("    # Network error or request failure — no HTTP response at all")
    lines.append("    $errMsg = $ex.Message")
    lines.append("    if ($ex.InnerException) { $errMsg = $ex.InnerException.Message }")
    lines.append("    $prefix = if ($ex -is [System.Net.WebException] -or $ex.GetType().FullName -like '*Http*') { 'Network error: ' } else { 'Request failed: ' }")
    lines.append("    $result = @{")
    lines.append("        status_code = 0")
    lines.append("        status_line = ''")
    lines.append("        headers = @{}")
    lines.append("        body = ''")
    lines.append("        elapsed_ms = $stopwatch.ElapsedMilliseconds")
    lines.append("        response_size = 0")
    lines.append("        error = \"$prefix$errMsg\"")
    lines.append("    }")
    lines.append("    $result | ConvertTo-Json -Depth 10 -Compress")
    lines.append("    exit 0")
    lines.append("}")
    lines.append("")

    # Build the result from a successful response
    lines.append("$respHeaders = @{}")
    lines.append("foreach ($key in $response.Headers.Keys) {")
    lines.append("    $val = $response.Headers[$key]")
    lines.append("    if ($val -is [System.Array]) { $val = $val -join ', ' }")
    lines.append("    $respHeaders[$key] = $val")
    lines.append("}")
    lines.append("")
    lines.append("$respBody = $response.Content")
    lines.append("if (-not $respBody) { $respBody = '' }")
    lines.append("")
    lines.append("$statusCode = [int]$response.StatusCode")
    lines.append("$statusDesc = $response.StatusDescription")
    lines.append("")
    # Build a status line similar to curl's output
    lines.append("$statusLine = \"HTTP/$($response.ProtocolVersion) $statusCode $statusDesc\"")
    lines.append("if (-not $response.ProtocolVersion) { $statusLine = \"HTTP $statusCode $statusDesc\" }")
    lines.append("")
    lines.append("$result = @{")
    lines.append("    status_code = $statusCode")
    lines.append("    status_line = $statusLine")
    lines.append("    headers = $respHeaders")
    lines.append("    body = $respBody")
    lines.append("    elapsed_ms = $stopwatch.ElapsedMilliseconds")
    lines.append("    response_size = if ($respBody) { [System.Text.Encoding]::UTF8.GetByteCount($respBody) } else { 0 }")
    lines.append("    error = $null")
    lines.append("}")
    lines.append("$result | ConvertTo-Json -Depth 10 -Compress")

    return "\n".join(lines)


def execute_request(
    url: str,
    method: str,
    headers: Dict[str, str],
    body: Optional[str] = None,
    files: Optional[List[Dict[str, str]]] = None,
) -> HttpResponse:
    """
    Executes an HTTP request using PowerShell's Invoke-WebRequest.

    The request parameters are passed via a temporary script file to
    avoid command-line quoting issues and prevent credential exposure
    in the process command line.
    """
    # Find PowerShell executable
    ps_exe = _find_powershell()
    if not ps_exe:
        return HttpResponse(
            status_code=0, headers={}, body="", elapsed_time=0.0,
            error=(
                "PowerShell is not installed or not found on PATH. "
                "Install PowerShell 7+ (pwsh) or ensure Windows PowerShell "
                "(powershell.exe) is available. "
                "See: https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows"
            )
        )

    # Build the PowerShell script
    script_content = _build_powershell_script(url, method, headers, body, files)

    # Write the script to a temporary file (avoids cmd-line quoting issues)
    script_file = None
    try:
        # Create temp file in a secure location
        fd, script_path = tempfile.mkstemp(suffix=".ps1", prefix="rouint_")
        script_file = Path(script_path)
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
            f.write(script_content)

        # Execute the PowerShell script
        cmd = [
            ps_exe,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-File", str(script_file),
        ]

        start_time = time.time()
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,  # 5-minute timeout
        )
        fallback_elapsed = time.time() - start_time

        if process.returncode != 0 and not process.stdout.strip():
            stderr = process.stderr.strip()
            return HttpResponse(
                status_code=0, headers={}, body="", elapsed_time=fallback_elapsed,
                error=f"PowerShell execution failed: {stderr or 'unknown error'}"
            )

        # Parse the JSON result from PowerShell
        output = process.stdout.strip()
        if not output:
            return HttpResponse(
                status_code=0, headers={}, body="", elapsed_time=fallback_elapsed,
                error="PowerShell returned empty output"
            )

        try:
            result = json.loads(output)
        except json.JSONDecodeError:
            return HttpResponse(
                status_code=0, headers={}, body="", elapsed_time=fallback_elapsed,
                error=f"Failed to parse PowerShell response: {output[:500]}"
            )

        # Extract fields from the structured result
        error = result.get("error")
        elapsed_ms = result.get("elapsed_ms", 0)
        elapsed_time = elapsed_ms / 1000.0 if elapsed_ms else fallback_elapsed

        resp_headers = result.get("headers", {})
        # Ensure headers is a dict of str->str
        if isinstance(resp_headers, dict):
            resp_headers = {str(k): str(v) for k, v in resp_headers.items()}
        else:
            resp_headers = {}

        return HttpResponse(
            status_code=int(result.get("status_code", 0)),
            headers=resp_headers,
            body=str(result.get("body", "")),
            elapsed_time=elapsed_time,
            status_line=str(result.get("status_line", "")),
            response_size=int(result.get("response_size", 0)),
            error=error if error else None,
        )

    except subprocess.TimeoutExpired:
        return HttpResponse(
            status_code=0, headers={}, body="", elapsed_time=300.0,
            error="Request timed out after 300 seconds"
        )
    except FileNotFoundError:
        return HttpResponse(
            status_code=0, headers={}, body="", elapsed_time=0.0,
            error=f"PowerShell executable '{ps_exe}' not found on PATH."
        )
    except Exception as e:
        return HttpResponse(
            status_code=0, headers={}, body="", elapsed_time=0.0,
            error=f"Unexpected error: {str(e)}"
        )
    finally:
        # Clean up the temporary script file
        if script_file and script_file.exists():
            try:
                script_file.unlink()
            except OSError:
                pass
