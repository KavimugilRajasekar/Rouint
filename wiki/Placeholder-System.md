# Placeholder System

> **[← Endpoint Wizard](Endpoint-Wizard.md)** · Placeholder System · [Authentication →](Authentication.md)

---

## Overview

Placeholders let you define endpoint paths with dynamic segments. Instead of saving a different endpoint for every user ID or query term, you define the path once with `{placeholder}` syntax and supply the values each time you run a test.

```
/api/v1/users/{id}
```

At test time, Rouint prompts:

```
? id:  usr-101
```

And fires the request to:

```
GET https://api.myapp.com/api/v1/users/usr-101
```

---

## Syntax

Wrap a name in curly braces anywhere in the path or query string:

```
{name}
```

**Valid examples:**

```
/users/{id}
/users/{user_id}/posts/{post_id}
/search?q={query}
/files/{filename}/download
/api/{version}/users?role={role}&page={page}
```

---

## Naming Rules

| Rule | Details |
|------|---------|
| Allowed characters | `a–z`, `A–Z`, `0–9`, `_` (underscore) |
| Uniqueness | Each name must be unique within a single endpoint path |
| No spaces | `{user id}` is invalid — use `{user_id}` |
| Case-sensitive | `{ID}` and `{id}` are treated as two different placeholders |

**Valid names:**

```
{id}          {user_id}       {post_id}
{query}       {page}          {API_VERSION}
{filename}    {access_token}  {item123}
```

**Invalid names:**

```
{user id}     ← space not allowed
{user-id}     ← hyphen not allowed
{123start}    ← must start with a letter or underscore... (actually digits are ok per regex)
```

---

## Validation at Creation Time

When you enter a path in the wizard, Rouint validates it immediately:

| Check | Example failure | Error |
|-------|----------------|-------|
| Balanced braces | `/users/{id` | `Malformed placeholders: mismatched curly braces.` |
| Unique names | `/users/{id}/posts/{id}` | `Duplicate placeholders detected.` |

Invalid paths are re-prompted — they are never saved.

---

## URL Encoding

Placeholder values are **URL-encoded automatically** before being inserted into the request URL. You never need to encode values yourself.

| Input value | Encoded in URL |
|-------------|---------------|
| `hello world` | `hello%20world` |
| `user@example.com` | `user%40example.com` |
| `foo/bar` | `foo%2Fbar` |
| `100` | `100` (no change needed) |
| `usr-101` | `usr-101` (no change needed) |

The encoding uses Python's `urllib.parse.quote` with `safe="/"` so forward slashes in intentional path segments are not double-encoded.

---

## Resolution at Test Time

When you run `rouint start-test` and select an endpoint that has placeholders, Rouint prompts for each one in order:

```
? id:        usr-101
? role:      admin
```

Rules:
- Empty values are not accepted — you are re-prompted
- Press `Esc` to go back to the endpoint selection screen
- Each value is URL-encoded before substitution

---

## Examples

### Single placeholder

```
Path:     /api/v1/users/{id}
Input:    id = usr-101
Result:   /api/v1/users/usr-101
```

### Multiple placeholders

```
Path:     /api/v1/users/{id}/posts/{post_id}
Input:    id = 42, post_id = 7
Result:   /api/v1/users/42/posts/7
```

### Query string

```
Path:     /search?q={query}&page={page}
Input:    query = hello world, page = 2
Result:   /search?q=hello%20world&page=2
```

### Mixed path and query

```
Path:     /api/v1/users/{id}?include={fields}
Input:    id = 99, fields = name,email
Result:   /api/v1/users/99?include=name%2Cemail
```

---

## No Placeholders

Paths without placeholders work exactly as expected — no prompts, the path is used as-is:

```
Path:   /api/v1/health
Result: GET https://api.myapp.com/api/v1/health
```

---

## Implementation Reference

The placeholder logic lives in `rouint/core/parser.py`:

| Function | Purpose |
|----------|---------|
| `extract_placeholders(path)` | Returns list of placeholder names from a path string |
| `validate_path(path)` | Checks balanced braces and uniqueness; returns `(ok, error)` |
| `resolve_placeholders(path, values)` | Substitutes values and URL-encodes them |
