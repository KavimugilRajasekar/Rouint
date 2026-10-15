# Authentication

> **[← Placeholder System](Placeholder-System.md)** · Authentication · [Environments →](Environments.md)

---

## Overview

Rouint supports three authentication modes, configured per endpoint during the wizard (Step 4). The auth type is stored in the endpoint config and used automatically when you run `rouint start-test`.

| Type | Stored in config | Prompted at test time |
|------|-----------------|----------------------|
| None | — | No |
| Bearer Token | Type only | Yes (token value) |
| Custom | Header name + value | No |

---

## None

No authentication header is added to the request.

Use this for:
- Public API endpoints
- Endpoints that use API keys embedded in the URL (query parameters)
- Endpoints where auth is handled by a separate header you add manually

---

## Bearer Token

Rouint stores only the auth type (`"bearer token"`) in the endpoint config — never the token value. Each time you test the endpoint, you are prompted:

```
? Enter Bearer token:  ••••••••••••••••
```

The `Authorization` header is constructed at test time:

```
Authorization: Bearer <your-token>
```

In the REQUEST panel, it is shown as:

```
Authorization: [REDACTED]
```

### Temp Token Workflow

Rouint can automatically capture and reuse tokens from API responses, eliminating the need to manually copy tokens between requests.

#### Step 1 — Run a login endpoint

```bash
rouint start-test
# Select: Login  [POST]  /api/v1/auth/login
# Select: local  →  http://127.0.0.1:8080
```

#### Step 2 — Token detected

After a successful response, Rouint scans for tokens in:

**Response body fields:**
```
access_token    token           accessToken
jwt             auth_token      id_token
data.token      data.access_token
```

**Response headers:**
```
Authorization: Bearer <token>
Set-Cookie: token=<value>
```

If a token is found:

```
✔  Token detected in response.
? Save as temp token for reuse? (Y/n)
```

#### Step 3 — Token saved

Choosing Yes saves the token to `.rouint-data/.temp_token` with `chmod 0600` (owner read/write only).

#### Step 4 — Reuse on next Bearer request

On the next `rouint start-test` for any Bearer Token endpoint:

```
? Use saved temp token? (Y/n)
```

Choosing Yes fills the token automatically — no manual copy-paste needed.

#### Step 5 — Clear when done

```bash
rouint clear-token
```

Deletes `.rouint-data/.temp_token`. The file is also protected by `.gitignore` so it is never accidentally committed.

---

## Custom

Custom authentication lets you define any header name and value. This covers:
- API key headers (`X-API-Key`, `X-Auth-Token`, etc.)
- Proprietary auth schemes
- Service-to-service tokens

During the wizard:

```
? Custom auth header name:   X-API-Key
? Custom auth header value:  sk-live-abc123xyz
```

Both are stored in the endpoint config and automatically added to every request for that endpoint.

**Example header in REQUEST panel:**

```
X-API-Key: [REDACTED]
```

Custom auth headers are stored in plaintext in `.rouint-data/endpoints/<slug>.json`. The endpoint directory is safe to commit, but be careful if your API key is sensitive — consider using Bearer Token mode or environment variables instead.

---

## Security Notes

| Concern | Behaviour |
|---------|-----------|
| Token values in config | Bearer token values are **never stored** — only prompted at test time |
| Temp token file | Saved to `.rouint-data/.temp_token` with `0600` permissions |
| Temp token in git | Protected by `.rouint-data/.gitignore` |
| Auth headers in output | Shown as `[REDACTED]` in the REQUEST panel |
| Custom header values | Stored in endpoint JSON (be aware when committing endpoint files) |
| curl invocation | Built with `subprocess.run(list)` — no shell interpolation |

---

## Endpoint Config Examples

**Bearer Token endpoint:**

```json
{
  "auth": {
    "type": "bearer token"
  }
}
```

**Custom header endpoint:**

```json
{
  "auth": {
    "type": "custom",
    "header_name": "X-API-Key",
    "header_value": "sk-live-abc123xyz"
  }
}
```

**No auth:**

```json
{
  "auth": {
    "type": "none"
  }
}
```
