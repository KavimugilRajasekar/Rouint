# Rouint — Project Idea & Technical Specification

**Project Name:** Rouint
**Category:** CLI-Based API Endpoint Management and Testing Tool
**Inspiration:** Postman, with cURL as the underlying HTTP request execution engine
**Interface:** Interactive, keyboard-driven terminal UI (TUI)
**Core Philosophy:** Define endpoints once, organize them locally, and test them directly from the terminal.

## 1. Project Overview

Rouint is a CLI-based API endpoint testing tool that wraps the system-installed cURL utility and provides a structured, interactive experience for creating, saving, organizing, editing, and testing API endpoints.

Instead of repeatedly constructing cURL commands manually or switching to a graphical API client, users can define their endpoints once and reuse them whenever needed.

Rouint stores endpoint configurations, request bodies, headers, authentication settings, and related resources inside a dedicated `.rouint-data/` directory within the user's project root.

When an endpoint is tested, Rouint executes the HTTP request through cURL and displays the request details, HTTP status, response headers, response body, and timing information directly in the terminal.

**The primary objective is to make API testing organized, reusable, transparent, nd entirely terminal-oriented.**

## 2. Core Design Principles

1. **CLI-first:** Every major operation should be accessible through a terminal command.
2. **Interactive when useful:** Guide users through endpoint creation and testing without requiring long command arguments.
3. **Persistent storage:** Saved endpoints and request configurations must remain available between sessions.
4. **cURL-powered execution:** Reuse the operating system's cURL installation instead of implementing an HTTP engine from scratch.
5. **Visible request and response:** Show the effective request and actual server response for debugging.
6. **Scalable navigation:** Keep endpoint selection usable even when hundreds of endpoints exist.
7. **Local-first storage:** Store project configurations locally and handle credentials carefully.
8. **Deferred parameter values:** Define path and query parameter placeholders when creating an endpoint; prompt for their actual values when testing it.
9. **Composable workflow:** Support both interactive testing and eventual non-interactive execution through scripts and CI/CD pipelines.

## 3. Workspace Initialization

### Command

```bash
rouint init
```

When executed inside a project root, Rouint initializes its local workspace.

The command should:

* Check whether cURL is installed and available.
* Create the `.rouint-data/` directory.
* Create the required configuration and resource directories.
* Initialize the endpoint registry or index.
* Set up a default environment and base URL configuration.
* Avoid overwriting an existing Rouint workspace.

Example output:

```text
Rouint — API Testing Workspace

✓ cURL detected
✓ Workspace initialized
✓ Configuration created

Workspace: .rouint-data/

Get started:
  rouint add-new
  rouint start
```

If a workspace already exists, Rouint should report that fact and preserve the existing data unless the user explicitly requests a reset.

## 4. Creating a New Endpoint

### Command

```bash
rouint add-new
```

This command starts an interactive endpoint creation wizard.

The wizard should be partially interactive: users provide the essential information, while Rouint uses sensible defaults for optional settings.

### Step 1: Select a base URL or environment

```text
Rouint — Create Endpoint

◆ Select a base URL
│  ● http://localhost:8000
│  ○ Add a new base URL
└
```

The base URL should be stored separately from the endpoint path. This allows users to reuse the same endpoint definition against different environments.

### Step 2: Select the HTTP method

```text
◆ Which method should this endpoint use?
│  ● GET
│  ○ POST
│  ○ PUT
│  ○ PATCH
│  ○ DELETE
│  ○ HEAD
│  ○ OPTIONS
│
│  ↑/↓ Navigate • Enter Confirm • Esc Back
└
```

### Step 3: Enter the endpoint path and parameter placeholders

Users should enter the endpoint path themselves, including any placeholders for dynamic values.

Rouint must not require users to answer a separate yes/no question about whether the endpoint has path parameters or query parameters. The placeholders in the supplied path define which values will be requested during testing.

Example:

```text
◆ Enter endpoint path
│
│  /api/v1/users/{user_id}?is_active={is_active}&page={page}
│
└
```

Here:

* `{user_id}` represents a path parameter.
* `{is_active}` represents a query parameter.
* `{page}` represents another query parameter.

Rouint should save the parameterized path as the endpoint template, not as a URL containing actual values.

The user can also define an endpoint without any parameters:

```text
/api/v1/users
```

Or define an endpoint with only path parameters:

```text
/api/v1/users/{user_id}
```

Or define one with only query parameters:

```text
/api/v1/users?is_active={is_active}&page={page}
```

Rouint should recognize placeholders enclosed in curly braces and preserve them as named variables. It should not automatically invent parameters or require users to confirm their existence through additional prompts.

**Placeholder rules:**

* Use `{parameter_name}` consistently for both path and query parameters.
* Parameter names should be unique within an endpoint.
* Query parameters should use normal URL query syntax, with `&` separating multiple parameters.
* Query parameter values should be URL-encoded when the final request URL is constructed.
* Reserved URL characters and placeholder syntax should be validated before saving.
* If a placeholder is malformed or duplicated, Rouint should explain the problem and ask the user to correct it.

For clarity, a placeholder such as `{user_id}` means that the value is not known yet. It is supplied later when the endpoint is tested.

### Step 4: Configure request headers

```text
◆ Configure request headers

  Content-Type: application/json
  Accept: application/json

Add a header? [y/N]
```

Users should be able to add, edit, and remove headers.

Headers should be stored as part of the endpoint configuration and reused across test executions. Sensitive header values, especially authorization credentials, must be handled securely.

### Step 5: Configure authentication

Rouint should support:

* No authentication.
* Bearer token / JWT.
* Custom authorization headers.

For JWT authentication, users should be able to enter a token through a masked prompt or configure a reference to an environment variable.

Tokens should not be printed in full in the terminal or stored in plaintext by default.

### Step 6: Configure the request body

For methods that commonly send a body, such as POST, PUT, and PATCH, Rouint should ask whether the user wants to attach one.

```text
◆ Configure request body
│  ● Create JSON body
│  ○ Load from file
│  ○ No request body
└
```

Users should be able to create a JSON body interactively, edit an existing body, or provide a file path to load a saved body.

Example:

```json
{
  "name": "Kavi",
  "email": "kavi@example.com"
}
```

The body should be saved separately and referenced by the endpoint configuration.

Rouint should also support file attachments for multipart requests and appropriate raw or binary request bodies.

### Step 7: Name and save the endpoint

```text
◆ Give this endpoint a name
│  Get User By ID
└

Review Endpoint

Name:   Get User By ID
Method: GET
Path:   /api/v1/users/{user_id}?is_active={is_active}&page={page}

Save endpoint? [Y/n]
```

After confirmation, Rouint saves the endpoint template and makes it available for future testing.

**Important:** Creating an endpoint should not require the user to supply actual path or query parameter values. Those values belong to the testing workflow.

## 5. Testing a Saved Endpoint

### Command

```bash
rouint start
```

This command opens the interactive endpoint selector.

Users should be able to select a base URL or environment and then choose an endpoint to test.

Example:

```text
Rouint — Select Endpoint

Search: users

◆ Available Endpoints
│  ● Get All Users        GET
│  ○ Get User By ID       GET
│  ○ Create User          POST
│  ○ Update User          PUT
│  ○ Delete User          DELETE
│  ○ List User Orders     GET
│  ○ Search Users         GET
│
│  Showing 1–7 of 124 endpoints
│
│  ↑/↓ Navigate • Enter Select
│  → Next Page • / Search • Esc Exit
└
```

### Scalable endpoint navigation

* Display a maximum of seven endpoint entries in the interactive viewport.
* Allow smooth keyboard navigation.
* Support paging or scrolling through additional entries.
* Provide search and filtering by name, path, HTTP method, and tags.
* Show the current position and total endpoint count.
* Preserve selection when navigating between pages.

The seven-entry limit applies only to the visible selection viewport, not to the total number of endpoints stored.

### Endpoint action menu

After selecting an endpoint, present an action menu:

```text
◆ What would you like to do?
│  ● Test Endpoint
│  ○ Edit Endpoint
│  ○ View Configuration
│  ○ Duplicate Endpoint
│  ○ Delete Endpoint
└
```

Selecting **Test Endpoint** starts the request preparation workflow.

### Step 1: Resolve path parameters

If the saved endpoint contains path placeholders, Rouint should prompt for each corresponding value before executing the request.

Saved endpoint:

```text
/api/v1/users/{user_id}
```

Testing prompt:

```text
Rouint — Request Parameters

◆ Enter value for user_id
│  42
└
```

Rouint then constructs:

```text
/api/v1/users/42
```

The entered value is used for that test execution. It should not silently replace the saved `{user_id}` placeholder in the endpoint definition.

### Step 2: Resolve query parameters

For an endpoint saved as:

```text
/api/v1/users?is_active={is_active}&page={page}
```

Rouint should prompt for the query parameter values at test time:

```text
◆ Query Parameters

  is_active: true
  page:      1

Continue with these values? [Y/n]
```

The values supplied during testing are used to construct the final URL:

```text
/api/v1/users?is_active=true&page=1
```

Rouint should URL-encode parameter values correctly. For example, a value containing spaces or reserved URL characters must not accidentally change the query structure.

### Step 3: Handle multiple parameters

If an endpoint contains both path and query placeholders:

```text
/api/v1/users/{user_id}?is_active={is_active}&page={page}
```

Rouint should collect all required values in one organized parameter-entry stage.

Example:

```text
Rouint — Configure Test Request

Path Parameters
  user_id:   42

Query Parameters
  is_active: true
  page:      1

Resolved URL:
  http://localhost:8000/api/v1/users/42?is_active=true&page=1

Proceed with request? [Y/n]
```

The actual values should be requested every time a new test execution needs them, unless the user explicitly chooses an optional temporary default or environment-based value.

For non-interactive execution, Rouint should eventually support supplying these values through command arguments, environment variables, or a test configuration file.

### Step 4: Review and execute

After resolving placeholders, Rouint should display the effective request configuration, including the final URL, method, headers, authentication configuration, and request body.

The user can then confirm the request or return to edit its temporary values.

Once confirmed, Rouint executes the request through cURL and displays the results directly in the terminal.

## 6. Adding an Endpoint From an Existing One

### Command

```bash
rouint add-new-from
```

This command lets users create a new endpoint by reusing an existing endpoint configuration.

The workflow should:

1. Display the existing endpoint selector.
2. Allow the user to search for and select an endpoint.
3. Copy its configuration into a new, independent endpoint.
4. Allow changes to the name, method, path, placeholders, headers, authentication, and request body.
5. Save the new endpoint without modifying the original.

For example, a user could duplicate `Get User By ID` to create `Update User By ID`, reusing its base URL and authentication configuration while changing the HTTP method and request body.

The copied endpoint should not unintentionally share mutable request-body data with the original.

## 7. Editing and Managing Endpoints

Rouint should support the following operations:

* Edit the endpoint name, method, base URL reference, or path template.
* Add, rename, or remove path and query placeholders.
* Edit request headers and authentication configuration.
* Edit, replace, or remove request bodies.
* Attach files using filesystem paths.
* Duplicate endpoints.
* Delete endpoints after confirmation.
* Inspect the saved endpoint configuration.
* Organize endpoints by folders, tags, or logical groups.

Editing a parameterized endpoint should preserve its placeholders unless the user explicitly changes them.

The actual values entered during testing should remain temporary by default and must not silently overwrite the saved endpoint template.

Changes to saved configuration should be validated before being written, so an interrupted edit does not corrupt the previous valid endpoint.

## 8. Request Execution and Terminal Results

Rouint should invoke cURL with the saved configuration and the values resolved for the current test execution.

Example output:

```text
Rouint — Test Result

Endpoint: Get User By ID
Method:   GET
URL:      http://localhost:8000/api/v1/users/42?is_active=true&page=1

REQUEST
────────────────────────────────────────
> GET /api/v1/users/42?is_active=true&page=1 HTTP/1.1
> Accept: application/json
> Authorization: Bearer [REDACTED]

Request Body: None

RESPONSE
────────────────────────────────────────
< HTTP/1.1 200 OK
< Content-Type: application/json

{
  "id": 42,
  "name": "Kavi",
  "email": "kavi@example.com"
}

METRICS
────────────────────────────────────────
HTTP Status:       200 OK
Response Time:     42 ms
Response Size:     78 B
Result:            HTTP request completed

✓ Response received successfully
```

The displayed values are illustrative. Actual results must come from the executed request.

### Required result information

* HTTP method and final URL.
* Resolved path and query parameter values.
* Request headers and body.
* HTTP status code and reason phrase, where available.
* Response headers.
* Response body.
* Response time and response size.
* Connection, DNS, TLS, and timeout errors.
* A clear final result.

Rouint should distinguish between a successfully executed HTTP request and a response that satisfies the user's expectations. An HTTP 404 is a valid HTTP response, but the test may fail if the expected status is 200.

Sensitive information must be redacted by default in both request previews and results.

## 9. Request Body and File Management

Rouint should treat request bodies as reusable resources rather than embedding large payloads directly into endpoint configuration files.

Users should be able to:

* Create and save JSON request bodies.
* Load request bodies from filesystem paths.
* Edit and reuse existing body files.
* Attach files for multipart/form-data requests.
* Send appropriate raw or binary payloads.
* Inspect the effective body used in a test.
* Save response bodies to files when required.

Rouint should distinguish between JSON, multipart attachments, and raw binary bodies because each requires different cURL options and content-type handling.

## 10. Proposed `.rouint-data/` Directory Structure

```text
project-root/
│
├── .rouint-data/
│   │
│   ├── config.json
│   ├── registry.json
│   │
│   ├── environments/
│   │   ├── local.json
│   │   └── development.json
│   │
│   ├── endpoints/
│   │   ├── users/
│   │   │   ├── get-all-users.json
│   │   │   ├── get-user-by-id.json
│   │   │   ├── create-user.json
│   │   │   └── update-user.json
│   │   │
│   │   └── orders/
│   │       ├── get-orders.json
│   │       └── create-order.json
│   │
│   ├── bodies/
│   │   ├── create-user.json
│   │   └── update-user.json
│   │
│   ├── schemas/
│   ├── history/
│   └── .gitignore
│
└── application-source/
```

An endpoint definition should retain its parameter placeholders. For example, `get-user-by-id.json` could contain:

```json
{
  "id": "ep_001",
  "name": "Get User By ID",
  "method": "GET",
  "base_url": "local",
  "path": "/api/v1/users/{user_id}?is_active={is_active}&page={page}",
  "headers": {
    "Accept": "application/json"
  },
  "auth": {
    "type": "none"
  },
  "body": null
}
```

This is an illustrative schema. Rouint should formally define and version its configuration format before implementation.

### Storage rules

* Each endpoint should have its own configuration file.
* Every endpoint should have a stable internal ID.
* Request bodies should be stored separately when practical.
* Environment configurations should be independent of endpoint definitions.
* Actual values entered during interactive testing should not be written back to the endpoint template by default.
* Credentials must not be committed to version control.
* Endpoint discovery should use an index or registry when useful.
* Saved configuration should be validated and migrated safely when the schema changes.

## 11. Configuration and Authentication Security

Rouint should support reusable environments and authentication without exposing secrets.

Environments can define base URLs and references to environment variables. Endpoint definitions can refer to those values rather than duplicating them.

For JWT authentication, Rouint should support masked interactive entry and environment-variable references. A token entered interactively should remain in memory for the current execution unless the user explicitly opts into an appropriate secure persistence mechanism.

Rouint must not assume that a hidden directory is automatically secure. File permissions, debug output, process arguments, and shell history must all be considered.

The `.rouint-data/.gitignore` configuration should help exclude local secrets while allowing users to version-control non-sensitive endpoint definitions and sample bodies.

## 12. Proposed Command Structure

| Command               | Purpose                                      |
| --------------------- | -------------------------------------------- |
| `rouint init`         | Initialize the workspace                     |
| `rouint add-new`      | Create an endpoint interactively             |
| `rouint start`        | Open the interactive endpoint selector       |
| `rouint add-new-from` | Create an endpoint from an existing endpoint |
| `rouint list`         | List saved endpoints                         |
| `rouint edit`         | Edit an endpoint                             |
| `rouint show`         | Display an endpoint configuration            |
| `rouint delete`       | Delete an endpoint after confirmation        |
| `rouint env`          | Manage environments                          |
| `rouint history`      | Inspect previous test executions, if enabled |
| `rouint --help`       | Display command help                         |
| `rouint --version`    | Display the installed version                |

Interactive workflows should be the primary experience. Direct command arguments can be added for automation while preserving the guided terminal interface.

## 13. Implementation Boundaries

Rouint should rely on cURL for HTTP transport, connection handling, TLS verification, and request execution.

Rouint itself should handle:

* Endpoint configuration and persistence.
* Interactive terminal navigation.
* Placeholder parsing and validation.
* Runtime path and query parameter resolution.
* URL construction and encoding.
* Safe invocation of cURL.
* Request and response formatting.
* Timing and response-size reporting.
* Test assertions and result classification.
* Configuration validation and migration.

The implementation must not construct shell commands by concatenating untrusted user input. It should use safe process-execution APIs or carefully controlled argument handling, and it must not disable TLS certificate verification by default.

cURL exit codes must be handled separately from HTTP status codes. A connection failure, DNS error, timeout, or TLS error is not the same as an HTTP 4xx or 5xx response.

## 14. Development Roadmap

### Phase 1 — Core workspace

* Workspace initialization.
* Endpoint configuration schema and persistence.
* Interactive endpoint creation.
* Endpoint listing.
* Basic path and query placeholder parsing.
* cURL-based request execution.
* Basic response and status display.

### Phase 2 — Interactive testing

* Seven-entry endpoint viewport.
* Keyboard navigation, search, and paging.
* Runtime path and query parameter prompts.
* `rouint start`.
* Endpoint editing and duplication.
* `rouint add-new-from`.

### Phase 3 — Request configuration

* Headers and authentication.
* JWT and environment-variable references.
* JSON request bodies and file-based payloads.
* File attachments.
* Multiple environments.

### Phase 4 — Testing and diagnostics

* Expected-status assertions.
* Response-body assertions.
* Response timing and size.
* Improved transport-error reporting.
* Optional request and response history.

### Phase 5 — Automation and advanced features

* Non-interactive execution.
* Shell-script and CI/CD integration.
* Response schema validation.
* Environment-specific test runs.
* Grouped endpoint execution.

## 15. Project Success Criteria

1. Users can initialize a workspace with one command.
2. Users can create and save endpoint templates interactively.
3. Path and query placeholders can be defined directly in the URL template.
4. Actual placeholder values are requested at test time, not during endpoint creation.
5. Endpoints remain reusable across sessions without losing their placeholders.
6. The endpoint selector remains usable with hundreds of saved endpoints.
7. The final request URL is constructed and encoded correctly.
8. Request headers, authentication, and bodies are applied correctly.
9. The terminal displays the actual HTTP status, response headers, body, and timing.
10. HTTP responses are distinguishable from transport failures.
11. Credentials are protected from accidental disclosure.
12. Endpoint duplication and editing do not unintentionally change other saved endpoints.
13. Non-interactive testing can eventually be integrated into scripts and CI/CD pipelines.

## Final Product Definition

**Rouint is a local-first, CLI-based API endpoint management and testing tool that uses cURL as its execution engine and provides an interactive terminal interface for defining, organizing, reusing, and validating HTTP requests.**

Its key workflow is simple: create a reusable endpoint template, enter dynamic path and query values when testing, execute the request through cURL, and inspect the actual result directly in the terminal.

The initial implementation should prioritize workspace initialization, endpoint creation, placeholder resolution, endpoint selection, reliable request execution, and accurate response reporting. Advanced testing and automation capabilities can then build on that foundation.

