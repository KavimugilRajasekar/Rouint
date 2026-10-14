# Platform Backends

> **[← File Attachments](File-Attachments.md)** · Platform Backends · [Architecture →](Architecture.md)

---

## Overview

Rouint automatically selects the appropriate HTTP backend based on your operating system. All CLI commands, endpoint definitions, and test flows work identically across platforms — the backend difference is transparent to the user.

| Platform | Backend | Module |
|----------|---------|--------|
| Linux | cURL | `rouint/platforms/linux/executor.py` |
| macOS | cURL | `rouint/platforms/linux/executor.py` |
| Windows | PowerShell | `rouint/platforms/windows/executor.py` |

---

## Platform Detection

Platform detection happens at runtime in `rouint/platforms/__init__.py`:

```python
import platform

system = platform.system().lower()

if system in ("linux", "darwin"):
    # use cURL backend
elif system == "windows":
    # use PowerShell backend
```

The correct backend is imported only when needed — no cross-platform imports occur on either OS.

---

## Linux / macOS Backend — cURL

### Tool

`curl` — must be installed and available on your `PATH`.

Most Linux distributions and macOS ship with curl pre-installed. Verify:

```bash
curl --version
```

### How it works

Rouint constructs a `curl` command and runs it as a subprocess:

```bash
curl -i -s -X POST \
  -w "\n%{http_code}\n%{time_total}\n%{size_download}" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice"}' \
  https://api.myapp.com/auth/login
```

**Flags used:**

| Flag | Purpose |
|------|---------|
| `-i` | Include response headers in output |
| `-s` | Silent mode — suppress progress bar |
| `-X METHOD` | Set HTTP method |
| `-H "Key: Value"` | Add a request header |
| `-d "body"` | Set request body |
| `-F "field=@path"` | Add a multipart file field |
| `-w "..."` | Write-out format for status code, time, and size |

### File uploads

```bash
curl -F "avatar=@/home/user/photo.jpg" \
     -F "data={\"name\":\"Alice\"}" \
     https://api.myapp.com/upload
```

curl sets `Content-Type: multipart/form-data; boundary=...` automatically.

### Output parsing

curl outputs the response headers, body, and a trailing three-line footer:

```
HTTP/1.1 200 OK
content-type: application/json

{"access_token": "eyJ..."}

200
0.142
1024
```

Rouint parses:
- Status line and headers from the top
- Body between headers and footer
- Status code, elapsed time, and response size from the footer

### Error handling

| Scenario | Behaviour |
|----------|-----------|
| curl not found | `curl is not installed or not found on PATH` |
| Non-zero exit | Error message from curl's stderr shown in red |
| Unexpected exception | Friendly error message + GitHub issues link |

---

## Windows Backend — PowerShell

### Supported versions

| PowerShell | Executable | Status |
|------------|-----------|--------|
| PowerShell 7+ | `pwsh` | ✅ Preferred |
| Windows PowerShell 5.1 | `powershell.exe` | ✅ Fallback |

Rouint prefers `pwsh` if it is available on `PATH`. If not found, it falls back to `powershell.exe`. If neither is available, a clear error is shown.

### How it works

Rouint generates a PowerShell script and runs it via subprocess:

```powershell
$response = Invoke-WebRequest `
  -Method POST `
  -Uri "https://api.myapp.com/auth/login" `
  -Headers @{ "Accept" = "application/json"; "Content-Type" = "application/json" } `
  -Body '{"username": "alice"}' `
  -SkipHttpErrorCheck `
  -UseBasicParsing
```

**Key flags:**

| Flag | Purpose |
|------|---------|
| `-SkipHttpErrorCheck` | Prevents PowerShell 7 from throwing on 4xx/5xx responses |
| `-UseBasicParsing` | Avoids Internet Explorer engine dependency on PS 5.1 |

### File uploads on PowerShell 7+

```powershell
$response = Invoke-WebRequest `
  -Method POST `
  -Uri "https://api.myapp.com/upload" `
  -Form @{ avatar = Get-Item "C:\Users\user\photo.jpg" }
```

### File uploads on PowerShell 5.1

PowerShell 5.1 does not have native `-Form` support. Rouint uses .NET's `HttpClient`:

```powershell
$httpClient = [System.Net.Http.HttpClient]::new()
$multipart  = [System.Net.Http.MultipartFormDataContent]::new()
$stream     = [System.IO.File]::OpenRead("C:\Users\user\photo.jpg")
$content    = [System.Net.Http.StreamContent]::new($stream)
$multipart.Add($content, "avatar", "photo.jpg")
$response   = $httpClient.PostAsync($uri, $multipart).Result
```

### Timing

Response time on Windows is measured using .NET's `Stopwatch` for millisecond-level accuracy, since curl's `%{time_total}` is not available.

### Terminal encoding

On startup, Rouint reconfigures `sys.stdout` and the Rich console to UTF-8. This prevents garbled characters on Windows terminals that default to a legacy code page (e.g. CP1252).

---

## Limitations

| Platform | Limitation |
|----------|-----------|
| Windows PS 5.1 | File uploads use .NET `HttpClient` — may behave differently from PS 7+ `-Form` with some servers |
| Windows PS 5.1 | Timing uses .NET `Stopwatch` instead of curl's native `%{time_total}` |
| Linux/macOS | curl must be installed separately if not already present |

---

## Adding a New Platform

Rouint's platform dispatch is in `rouint/core/executor.py`. To add support for a new platform:

1. Create `rouint/platforms/<platform>/executor.py`
2. Implement `execute_request(url, method, headers, body, files) → HttpResponse`
3. Update `_get_platform_backend()` in `rouint/core/executor.py` to route to your module

See [Architecture](Architecture.md) for the full module map.
