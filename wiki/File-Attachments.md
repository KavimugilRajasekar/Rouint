# File Attachments

> **[← Environments](Environments.md)** · File Attachments · [Platform Backends →](Platform-Backends.md)

---

## Overview

Rouint supports `multipart/form-data` file uploads for POST, PUT, PATCH, and DELETE endpoints. Files are configured during endpoint creation (Step 6 of the wizard) and sent using your platform's native HTTP backend at test time.

---

## Configuring File Attachments

File attachments are set in **Step 6** of `rouint add-new-api`. This step appears only for methods that support a body: **POST, PUT, PATCH, DELETE**.

```
? Attach files to this request? (y/N)  y

? File path:        /home/user/documents/photo.jpg
? Form field name:  avatar

? Add another file? (y/N)  n
```

### Fields

| Field | Description |
|-------|-------------|
| **File path** | Absolute path to the file on your machine |
| **Form field name** | The multipart field name the server expects (e.g. `avatar`, `document`, `file`) |

### Validation at creation time

- The file path is checked immediately — it must exist and be a regular file
- If the file does not exist, you are re-prompted before the endpoint is saved

### Multiple files

You can attach more than one file per endpoint:

```
? Attach files to this request? (y/N)  y

? File path:        /home/user/id_front.jpg
? Form field name:  id_front
? Add another file? (y/N)  y

? File path:        /home/user/id_back.jpg
? Form field name:  id_back
? Add another file? (y/N)  n
```

---

## Sending Files at Test Time

When you run `rouint start-test` for an endpoint with file attachments, Rouint:

1. Validates that each saved file path still exists
2. Removes `Content-Type` from headers (the backend sets it automatically with the correct boundary)
3. Sends the request as `multipart/form-data`

If a file is missing at test time, a clear error is shown and the test is cancelled.

---

## Platform Behaviour

### Linux / macOS — cURL

Files are sent using curl's `-F` flag:

```bash
curl -X POST https://api.myapp.com/upload \
  -H "Accept: application/json" \
  -F "avatar=@/home/user/photo.jpg"
```

curl automatically sets the `Content-Type: multipart/form-data; boundary=...` header with the correct boundary.

**Multiple files:**

```bash
curl -X POST https://api.myapp.com/upload \
  -F "id_front=@/home/user/id_front.jpg" \
  -F "id_back=@/home/user/id_back.jpg"
```

**File upload with JSON body:**

If a JSON body is also defined on the endpoint, it is included as an extra form field named `data`:

```bash
curl -F "data={\"name\":\"Alice\"}" \
     -F "avatar=@/home/user/photo.jpg"
```

---

### Windows (PowerShell 7+)

Files are sent using PowerShell's native `-Form` parameter:

```powershell
Invoke-WebRequest -Method POST `
  -Uri "https://api.myapp.com/upload" `
  -Form @{ avatar = Get-Item "/home/user/photo.jpg" }
```

---

### Windows (PowerShell 5.1)

Files are sent using .NET's `MultipartFormDataContent`:

```powershell
$multipart = [System.Net.Http.MultipartFormDataContent]::new()
$fileStream = [System.IO.File]::OpenRead("C:\Users\user\photo.jpg")
$fileContent = [System.Net.Http.StreamContent]::new($fileStream)
$multipart.Add($fileContent, "avatar", "photo.jpg")
```

This approach is functionally equivalent but may behave slightly differently from PowerShell 7+'s native `-Form` with certain server implementations.

---

## Content-Type Header Handling

Rouint automatically removes any manually set `Content-Type` header when files are attached. This is intentional — setting it manually would break the multipart boundary.

| Scenario | Content-Type |
|----------|-------------|
| No files | Set manually in headers (e.g. `application/json`) |
| Files attached | Removed — backend sets `multipart/form-data; boundary=...` |

---

## Stored Configuration

File attachment config in `.rouint-data/endpoints/<slug>.json`:

```json
{
  "files": [
    {
      "path": "/home/user/documents/photo.jpg",
      "field": "avatar"
    },
    {
      "path": "/home/user/documents/resume.pdf",
      "field": "document"
    }
  ]
}
```

An endpoint with no file attachments stores:

```json
{
  "files": []
}
```

---

## Common Field Names

Different APIs use different field names. Use whatever the server expects:

| Common field names |
|--------------------|
| `file` |
| `avatar` |
| `image` |
| `document` |
| `attachment` |
| `upload` |

Check your API's documentation or schema to find the correct field name.
