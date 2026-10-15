# Endpoint Wizard

> **[← Commands Reference](Commands-Reference.md)** · Endpoint Wizard · [Placeholder System →](Placeholder-System.md)

---

## Overview

The endpoint wizard is launched by `rouint add-new-api`. It walks you through 7 steps to define a reusable API endpoint template. At every step you can press **Esc** to go back to the previous step — no need to start over if you make a mistake.

```bash
rouint add-new-api
```

The wizard saves the endpoint configuration to `.rouint-data/endpoints/` when you complete all 7 steps. No base URL is stored — you choose the environment at test time.

---

## Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate options |
| `Enter` | Confirm selection / submit input |
| `Esc` | Go back to the previous step |
| `Ctrl+C` | Cancel and exit the wizard |

---

## Step 1 — HTTP Method

Choose the HTTP method for this endpoint.

```
? Select HTTP method:
❯ GET
  POST
  PUT
  PATCH
  DELETE
  HEAD
  OPTIONS
```

**Supported methods:** GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS

The method you choose affects later steps:
- Steps 5 (Body) and 6 (Files) are only shown for **POST, PUT, PATCH, DELETE**
- Default headers differ by method (see Step 3)

---

## Step 2 — Path

Enter the endpoint path. You can include `{placeholder}` syntax for dynamic values.

```
? Enter the path:  /api/v1/users/{id}
```

**Examples:**

```
/api/v1/users
/api/v1/users/{id}
/api/v1/users/{id}/posts/{post_id}
/search?q={query}&page={page}
/api/v1/auth/login
```

**Validation rules:**
- Cannot be empty
- Automatically prefixed with `/` if missing
- Curly braces must be balanced — `{id}` ✅, `{id` ❌
- Placeholder names must be unique within the path
- Placeholder names: `[a-zA-Z0-9_]` characters only

If validation fails, you are re-prompted with an error message.

See [Placeholder System](Placeholder-System.md) for full details.

---

## Step 3 — Headers

Review and customise the request headers.

Rouint pre-fills method-aware defaults:

| Method | Default Headers |
|--------|----------------|
| GET, HEAD, OPTIONS, DELETE | `Accept: application/json` |
| POST, PUT, PATCH | `Accept: application/json`, `Content-Type: application/json` |

```
Current headers:
  Accept           application/json
  Content-Type     application/json

? Header name (or press Enter to continue):
```

To add a header, enter the name and then the value when prompted. Press `Enter` on an empty name to move to the next step.

**Notes:**
- Custom auth headers added in Step 4 are also reflected here
- If you attach files in Step 6, `Content-Type` is automatically removed — the HTTP backend sets it to `multipart/form-data` with the correct boundary

---

## Step 4 — Authentication

Choose the authentication strategy for this endpoint.

```
? Select authentication type:
❯ None
  Bearer Token
  Custom
```

### None
No authentication header is added.

### Bearer Token
No value is stored at creation time. When you run `rouint start-test`, you are prompted for the token. If a temp token has been saved from a previous response, Rouint offers to reuse it automatically.

```
? Enter Bearer token:  ••••••••••••••••
```

The `Authorization: Bearer <token>` header is added at test time and shown as `[REDACTED]` in the REQUEST panel.

### Custom
Prompts for a custom header name and value. Both are stored in the endpoint configuration.

```
? Custom auth header name:   X-API-Key
? Custom auth header value:  my-secret-key
```

The header is added to every request for this endpoint.

See [Authentication](Authentication.md) for the full temp token workflow.

---

## Step 5 — Request Body

*Shown for: POST, PUT, PATCH, DELETE only.*

```
? Does this request have a body? (Y/n)
```

If yes, enter a valid JSON body:

```
? Enter JSON body:
{
  "username": "alice",
  "password": "secret123"
}
```

**Validation:**
- Must be valid, parseable JSON
- Cannot be empty if you answered Yes
- Re-prompted immediately on invalid JSON — bad data is never accepted

**Example bodies:**

```json
{ "name": "Alice", "role": "admin" }
```

```json
{
  "filters": { "active": true },
  "pagination": { "page": 1, "limit": 20 }
}
```

---

## Step 6 — File Attachments

*Shown for: POST, PUT, PATCH, DELETE only.*

```
? Attach files to this request? (y/N)
```

If yes, add one or more files:

```
? File path:        /home/user/documents/photo.jpg
? Form field name:  avatar
? Add another file? (y/N)
```

**Validation:**
- File path must exist and be a regular file (checked immediately)
- Form field name is the multipart field the server expects
- Multiple files are supported

When files are attached:
- The request is sent as `multipart/form-data`
- `Content-Type` is removed from headers — the HTTP backend sets the correct boundary automatically
- On Linux/macOS: `curl -F field=@/path/to/file`
- On Windows (PS 7+): PowerShell `-Form` parameter
- On Windows (PS 5.1): .NET `MultipartFormDataContent`

See [File Attachments](File-Attachments.md) for more detail.

---

## Step 7 — Name

Give the endpoint a memorable label.

```
? Endpoint name:  Login
```

**Rules:**
- Cannot be empty
- Used as the display name in `rouint list-api` and `rouint start-test`
- The slug (filename) is derived from the name: `Login` → `login.json`

---

## Saving

After Step 7, the endpoint is saved to `.rouint-data/endpoints/<slug>.json` and registered in `registry.json`. You will see a confirmation:

```
✔  Endpoint "Login" saved.
```

---

## Editing an Existing Endpoint

From `rouint list-api`, select an endpoint and choose **Edit Endpoint**. The wizard re-runs with all existing values pre-filled. Each step shows the current value — press `Enter` to keep it or type a new value.

Esc navigation works the same as during creation.

---

## Example: Creating a POST Login Endpoint

```
Step 1  method    →  POST
Step 2  path      →  /api/v1/auth/login
Step 3  headers   →  Accept: application/json
                     Content-Type: application/json
Step 4  auth      →  Bearer Token
Step 5  body      →  { "username": "alice", "password": "secret" }
Step 6  files     →  (none)
Step 7  name      →  Login

✔  Endpoint "Login" saved.
```
