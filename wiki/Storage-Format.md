# Storage Format

> **[← Architecture](Architecture.md)** · Storage Format · [Contributing →](Contributing.md)

---

## Overview

Rouint stores all data locally in a `.rouint-data/` directory inside your project. Everything is plain JSON — human-readable, easy to inspect, and safe to version-control (with exceptions noted below).

---

## Directory Layout

```
project-root/
└── .rouint-data/
    ├── .gitignore           ← auto-generated; protects secrets
    ├── config.json          ← workspace version and default environment
    ├── registry.json        ← maps endpoint IDs → slugs
    ├── endpoints/           ← one JSON file per endpoint  [safe to commit]
    │   ├── login.json
    │   ├── get-user-by-id.json
    │   └── list-users.json
    ├── environments/        ← one JSON file per base URL  [gitignored]
    │   ├── local.json
    │   ├── staging.json
    │   └── production.json
    ├── bodies/              ← request body files          [gitignored]
    └── .temp_token          ← saved Bearer token          [gitignored]
```

### Git safety at a glance

| Path | Committed? | Reason |
|------|-----------|--------|
| `endpoints/` | ✅ Yes | Shareable endpoint templates |
| `registry.json` | ✅ Yes | Endpoint ID → slug map |
| `config.json` | ✅ Yes | Workspace version config |
| `environments/` | ❌ No | Contains real server URLs |
| `bodies/` | ❌ No | May contain credentials or PII |
| `.temp_token` | ❌ No | Live Bearer token |
| `*.secret.json` | ❌ No | Explicitly sensitive files |

---

## File Schemas

### `config.json`

Created by `rouint init`. Stores the workspace version.

```json
{
  "version": "1.0",
  "default_env": "local"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Workspace format version |
| `default_env` | string | Reserved for future use |

---

### `registry.json`

Maps endpoint IDs to their slug (filename without `.json`). Updated automatically on every save or delete.

```json
{
  "ep_login": "login",
  "ep_get-user-by-id": "get-user-by-id",
  "ep_list-users": "list-users"
}
```

| Field | Type | Description |
|-------|------|-------------|
| key | string | Endpoint ID — `ep_<slug>` |
| value | string | Slug — matches the filename in `endpoints/` |

---

### `endpoints/<slug>.json`

One file per endpoint. The slug is derived from the endpoint name: `Get User By ID` → `get-user-by-id.json`.

**Full schema:**

```json
{
  "id": "ep_get-user-by-id",
  "name": "Get User By ID",
  "method": "GET",
  "path": "/api/v1/users/{id}",
  "base_url_ref": null,
  "headers": {
    "Accept": "application/json"
  },
  "auth": {
    "type": "none"
  },
  "body": null,
  "files": []
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier: `ep_<slug>` |
| `name` | string | Display name shown in menus |
| `method` | string | HTTP method (GET, POST, etc.) |
| `path` | string | Path with optional `{placeholder}` syntax |
| `base_url_ref` | null | Reserved — base URL selected at test time |
| `headers` | object | Key-value header map |
| `auth` | object | Authentication config (see below) |
| `body` | string or null | JSON body string, or null |
| `files` | array | File attachment list (see below) |

---

#### `auth` field

**No auth:**

```json
{ "type": "none" }
```

**Bearer Token:**

```json
{ "type": "bearer token" }
```

**Custom header:**

```json
{
  "type": "custom",
  "header_name": "X-API-Key",
  "header_value": "sk-live-abc123xyz"
}
```

---

#### `files` array

Each element is a file attachment:

```json
[
  {
    "path": "/home/user/photo.jpg",
    "field": "avatar"
  },
  {
    "path": "/home/user/resume.pdf",
    "field": "document"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Absolute file path on disk |
| `field` | string | Multipart form field name |

Empty when no files are attached: `"files": []`

---

### `environments/<name>.json`

One file per environment. The filename is the label you chose when adding the URL.

```json
{
  "base_url": "https://api.myapp.com"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `base_url` | string | Base URL, no trailing slash |

---

### `.temp_token`

A plain text file containing a single Bearer token value. Created with `chmod 0600`.

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ...
```

Deleted by `rouint clear-token`.

---

## Complete Endpoint Examples

### GET with a placeholder

```json
{
  "id": "ep_get-user-by-id",
  "name": "Get User By ID",
  "method": "GET",
  "path": "/api/v1/users/{id}",
  "base_url_ref": null,
  "headers": {
    "Accept": "application/json"
  },
  "auth": { "type": "none" },
  "body": null,
  "files": []
}
```

### POST with Bearer Token and JSON body

```json
{
  "id": "ep_login",
  "name": "Login",
  "method": "POST",
  "path": "/api/v1/auth/login",
  "base_url_ref": null,
  "headers": {
    "Accept": "application/json",
    "Content-Type": "application/json"
  },
  "auth": { "type": "bearer token" },
  "body": "{\"username\": \"alice\", \"password\": \"secret123\"}",
  "files": []
}
```

### POST with file upload

```json
{
  "id": "ep_upload-avatar",
  "name": "Upload Avatar",
  "method": "POST",
  "path": "/api/v1/users/{id}/avatar",
  "base_url_ref": null,
  "headers": {
    "Accept": "application/json"
  },
  "auth": { "type": "bearer token" },
  "body": null,
  "files": [
    { "path": "/home/user/photo.jpg", "field": "avatar" }
  ]
}
```

### GET with Custom API Key auth

```json
{
  "id": "ep_list-products",
  "name": "List Products",
  "method": "GET",
  "path": "/v2/products?category={category}",
  "base_url_ref": null,
  "headers": {
    "Accept": "application/json"
  },
  "auth": {
    "type": "custom",
    "header_name": "X-API-Key",
    "header_value": "sk-live-abc123"
  },
  "body": null,
  "files": []
}
```
