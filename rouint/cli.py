import json
import re

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rouint.utils.config import (
    init_workspace,
    is_initialized,
    get_data_path,
    get_env_path,
    list_environments,
    get_base_url,
    save_environment,
    TEMP_TOKEN_FILE,
)
from rouint.core.manager import EndpointManager
from rouint.core.parser import extract_placeholders, resolve_placeholders, validate_path
from rouint.core.executor import execute_request
from rouint.ui import display_banner, display_header, box_width
import questionary

console = Console()

# ---------------------------------------------------------------------------
# Questionary custom style & pointer
# ---------------------------------------------------------------------------

_SELECT_STYLE = questionary.Style([
    ("qmark",       "fg:#00bfff bold"),   # the ? prefix
    ("question",    "bold"),
    ("answer",      "fg:#00bfff bold"),
    ("pointer",     "fg:#00bfff bold"),   # the ◆ pointer
    ("highlighted", "fg:#00bfff bold"),   # hovered item
    ("selected",    "fg:#00bfff"),
    ("instruction", "fg:#666666"),
])

_POINTER = "❯"

# ---------------------------------------------------------------------------
# Token management helpers
# ---------------------------------------------------------------------------

def save_temp_token(token: str) -> str:
    """Persists a token to .rouint-data/.temp_token for reuse within the workspace."""
    token_path = get_data_path() / TEMP_TOKEN_FILE
    with open(token_path, "w") as f:
        f.write(token)
    # Ensure file is only readable by owner (sensitive)
    token_path.chmod(0o600)
    return str(token_path)

def load_temp_token() -> str | None:
    """Returns the saved temp token, or None if none exists."""
    token_path = get_data_path() / TEMP_TOKEN_FILE
    if not token_path.exists():
        return None
    return token_path.read_text().strip()

def clear_temp_token() -> bool:
    """Deletes the temp token file if it exists. Returns True if a token was removed."""
    token_path = get_data_path() / TEMP_TOKEN_FILE
    if token_path.exists():
        token_path.unlink()
        return True
    return False

def extract_token_from_response(response) -> str | None:
    """
    Attempts to extract a JWT or bearer token from the response.
    Checks response body (JSON fields) and Authorization / Set-Cookie headers.
    """
    # 1. Check response headers
    for header_key in ("Authorization", "Set-Cookie"):
        val = response.headers.get(header_key)
        if val:
            # Authorization: Bearer <token>
            bearer_match = re.search(r"Bearer\s+(.+)", val, re.IGNORECASE)
            if bearer_match:
                return bearer_match.group(1).strip()
            # Set-Cookie: token=<jwt>; ...
            cookie_match = re.search(r"(?:token|access_token|auth_token)=([^;]+)", val, re.IGNORECASE)
            if cookie_match:
                return cookie_match.group(1).strip()

    # 2. Check response body (JSON)
    if response.body:
        try:
            data = json.loads(response.body)
        except (json.JSONDecodeError, TypeError):
            return None

        # Look for common token field names
        token_fields = ("access_token", "token", "accessToken", "jwt", "auth_token", "id_token")
        if isinstance(data, dict):
            for field in token_fields:
                if field in data and isinstance(data[field], str):
                    return data[field]

            # Nested: { "data": { "token": "..." } }
            if "data" in data and isinstance(data["data"], dict):
                for field in token_fields:
                    if field in data["data"] and isinstance(data["data"][field], str):
                        return data["data"][field]

    return None

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def select_endpoint():
    """Shared helper to list and select an endpoint."""
    manager = EndpointManager()
    endpoints = manager.list_endpoints()

    if not endpoints:
        return None

    max_name_len = max(len(ep['name']) for ep in endpoints)
    choices = [f"{ep['name'].ljust(max_name_len)}  [{ep['method']}]" for ep in endpoints]
    choices.append("— Exit —")
    selected_label = questionary.select("Select an endpoint (or press Esc to exit):", choices=choices, style=_SELECT_STYLE, pointer=_POINTER, instruction="").ask()

    if not selected_label or selected_label == "— Exit —":
        return None

    return next(ep for ep in endpoints if ep['name'] == selected_label.split("  [")[0].strip())

def select_environment(default_ref=None):
    """
    Prompts the user to select an environment/base URL or type a custom one.
    Returns the environment name (e.g. "local").
    Falls back to 'local' if no environments are configured.
    """
    envs = list_environments()

    if not envs:
        # No environments configured — ask for a custom URL
        custom_url = questionary.text("Enter base URL (e.g., http://localhost:8000):").ask()
        if not custom_url or not custom_url.strip():
            return "local"
        custom_url = custom_url.strip()
        env_name = "custom"
        save_environment(env_name, custom_url)
        return env_name

    # Build choice labels showing the URL for clarity
    choices = []
    for env in envs:
        label = f"{env['name']} ({env['base_url']})"
        choices.append(label)
    # Add the "custom URL" option
    choices.append("— Add a new base URL —")

    # Determine default selection
    default_label = None
    if default_ref:
        for env in envs:
            if env["name"] == default_ref:
                default_label = f"{env['name']} ({env['base_url']})"
                break
    if not default_label:
        default_label = choices[0]

    selected = questionary.select(
        "Select a base URL / environment:",
        choices=choices,
        default=default_label,
        style=_SELECT_STYLE,
        pointer=_POINTER,
        instruction="",
    ).ask()

    if not selected:
        return default_ref or "local"

    # Handle custom URL option
    if selected == "— Add a new base URL —":
        custom_url = questionary.text("Enter base URL (e.g., https://api.example.com):").ask()
        if not custom_url or not custom_url.strip():
            console.print("[yellow]No URL entered. Using default 'local'.[/yellow]")
            return default_ref or "local"
        custom_url = custom_url.strip()
        # Derive a name from the URL (e.g., "https://api.example.com" -> "api-example-com")
        env_name = custom_url.replace("https://", "").replace("http://", "")
        env_name = env_name.split("/")[0].replace(".", "-").replace(":", "-")
        save_environment(env_name, custom_url)
        console.print(f"[green]✓ Environment '{env_name}' saved.[/green]")
        return env_name

    # Extract the environment name from the label (before the parenthesis)
    return selected.split(" (")[0]

def handle_endpoint_creation(existing_ep=None):
    """Shared logic for creating and editing endpoints."""
    # Default values if editing
    defaults = existing_ep or {}

    console.print("[dim]Base URL is selected at test time — you can test this endpoint against any saved URL.[/dim]\n")

    # 1. HTTP Method
    method = questionary.select(
        "Which method should this endpoint use?",
        choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        default=defaults.get("method"),
        style=_SELECT_STYLE,
        pointer=_POINTER,
    ).ask()
    if not method:
        console.print("[red]Endpoint creation cancelled.[/red]")
        return None

    # 2. Path
    path = questionary.text(
        "Enter endpoint path (e.g., /api/v1/users/{user_id})",
        default=defaults.get("path", "")
    ).ask()
    if not path or not path.strip():
        console.print("[red]Path is required. Please enter a valid path.[/red]")
        path = questionary.text("Enter endpoint path").ask()
        while not path or not path.strip():
            console.print("[red]Path is required. Please enter a valid path.[/red]")
            path = questionary.text("Enter endpoint path").ask()

    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path

    valid, msg = validate_path(path)
    while not valid:
        console.print(f"[red]{msg}[/red]")
        path = questionary.text("Enter endpoint path").ask()
        if not path or not path.strip():
            continue
        path = path.strip()
        if not path.startswith("/"):
            path = "/" + path
        valid, msg = validate_path(path)

    # 3. Headers
    # When editing, use saved headers. When creating, derive sensible defaults from method.
    if defaults.get("headers"):
        headers = dict(defaults["headers"])
        header_source = "saved"
    else:
        headers = {"Accept": "application/json"}
        if method in ["POST", "PUT", "PATCH"]:
            headers["Content-Type"] = "application/json"
        header_source = "default"

    # Show current headers
    if headers:
        label = "Saved headers:" if header_source == "saved" else f"Default headers for {method}:"
        console.print(f"\n[bold]{label}[/bold]")
        for hk, hv in headers.items():
            console.print(f"  [cyan]{hk}[/cyan]: {hv}")
        console.print()

    add_header = questionary.confirm(
        "Add or edit headers?",
        default=False
    ).ask()
    if add_header:
        console.print("[dim]Enter header name only (e.g. Authorization), then its value separately.[/dim]")
        console.print("[dim]Press Enter with an empty name to finish.[/dim]\n")
        while True:
            h_key = questionary.text("Header name (e.g. Authorization):").ask()
            if not h_key or not h_key.strip():
                break
            # Guard: user typed "Key: Value" in one shot
            if ":" in h_key:
                console.print("[yellow]⚠  Enter ONLY the header name here, not 'Name: Value'.[/yellow]")
                console.print("[yellow]   Example: Authorization  (then press Enter, then give the value)[/yellow]\n")
                continue
            h_key = h_key.strip()
            h_val = questionary.text(f"Value for '{h_key}':").ask()
            if h_val is not None:
                headers[h_key] = h_val.strip()

    # Show final headers
    # 4. Auth
    auth_type = questionary.select(
        "Authentication type?",
        choices=["None", "Bearer Token", "Custom"],
        default=defaults.get("auth", {}).get("type", "None").capitalize(),
        style=_SELECT_STYLE,
        pointer=_POINTER,
    ).ask()
    auth = {"type": auth_type.lower() if auth_type else "none"}

    # 5. Body
    body = defaults.get("body")
    if method in ["POST", "PUT", "PATCH"]:
        has_body = questionary.confirm(
            "Does this request have a body?",
            default=True if body else False
        ).ask()
        if has_body:
            console.print('[dim]Enter raw JSON body.[/dim]')
            body = questionary.text(
                "JSON body:",
                default=body or ""
            ).ask()
            # Validate it's non-empty
            while not body or not body.strip():
                console.print("[red]Body cannot be empty. Enter a JSON string or press N above to skip.[/red]")
                body = questionary.text("JSON body:").ask()
            body = body.strip()
            # Warn if invalid JSON (don't block, just notify)
            try:
                import json as _json
                _json.loads(body)
            except ValueError:
                console.print("[yellow]⚠  Warning: body does not appear to be valid JSON. It will be sent as-is.[/yellow]")
        else:
            body = None

    # 6. Name — required, re-prompt if empty
    name = questionary.text("Give this endpoint a name:", default=defaults.get("name", "")).ask()
    if not name or not name.strip():
        console.print("[red]Name is required. Please enter a name.[/red]")
        name = questionary.text("Give this endpoint a name:").ask()
        while not name or not name.strip():
            console.print("[red]Name is required. Please enter a name.[/red]")
            name = questionary.text("Give this endpoint a name:").ask()

    # Save — base_url_ref is None; base URL is chosen at test time
    manager = EndpointManager()
    slug = None
    if existing_ep:
        slug = name.lower().replace(" ", "-").replace("/", "-")

    endpoint_id = manager.save_endpoint(name, method, path, None, headers, auth, body, slug=slug)
    return endpoint_id

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Rouint — cURL-powered API endpoint management & testing tool.

    Define endpoints once, organize them locally, and test them against
    any environment directly from your terminal.

    Run without a command to see the full command menu.
    """
    if ctx.invoked_subcommand is None:
        display_banner()

@cli.command()
def init():
    """Initialize the Rouint workspace in the current directory.

    Creates a .rouint-data/ folder with subdirectories for endpoints,
    environments, and bodies. Also sets up a default 'local' environment
    pointing to http://localhost:8000.

    Run this once per project before using any other commands.
    """
    display_header("Workspace Initialization")
    success, message = init_workspace()
    if success:
        console.print(f"[green]✓ {message}[/green]")
        console.print("\nWorkspace: .rouint-data/\nGet started:\n  rouint add-base-url   # add your local/server URLs\n  rouint add-new-api    # define your API endpoints\n  rouint start-test     # pick endpoint + URL and test!\n  rouint list-api       # list/manage saved endpoints")
    else:
        console.print(f"[red]✗ {message}[/red]")

@cli.command(name="add-new-api")
def add_new_api():
    """Define a new API endpoint interactively.

    Walks you through setting up an endpoint step by step:

    \b
      1. HTTP method  — GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
      2. Path         — supports {placeholder} syntax (e.g. /users/{id})
      3. Headers      — pre-filled defaults based on method
      4. Auth         — None, Bearer Token, or Custom
      5. Body         — JSON body for POST / PUT / PATCH
      6. Name         — a memorable label for the endpoint

    The endpoint is saved locally and can be tested against any
    registered base URL using 'rouint start-test'.
    """
    display_header("Add New API Endpoint Definition")
    if not is_initialized():
        console.print("[red]Error: Workspace not initialized. Run 'rouint init' first.[/red]")
        return

    id = handle_endpoint_creation()
    if id is None:
        console.print("[yellow]Endpoint creation cancelled.[/yellow]")
        return
    console.print(f"\n[green]✓ Endpoint saved successfully! (ID: {id})[/green]")
    console.print("[dim]Use 'rouint start-test' to run it against any base URL.[/dim]")

@cli.command(name="add-base-url")
def add_base_url():
    """Add or delete a base URL environment.

    Environments are named base URLs you test against — e.g.
    local → http://127.0.0.1:8080, production → https://api.myapp.com.

    Actions available:

    \b
      Add     — register a new base URL with a label
      Delete  — remove an existing environment
    """
    display_header("Manage Global Base URLs")
    if not is_initialized():
        console.print("[red]Error: Workspace not initialized. Run 'rouint init' first.[/red]")
        return

    action = questionary.select(
        "What would you like to do?",
        choices=["Add a new base URL", "Delete an environment"],
        style=_SELECT_STYLE,
        pointer=_POINTER,
        instruction="",
    ).ask()

    if not action:
        return

    if action == "Add a new base URL":
        console.print("\n[dim]Examples: http://127.0.0.1:8080  |  https://api.myapp.com  |  https://staging.myapp.com[/dim]\n")

        url = questionary.text("Base URL:").ask()
        if not url or not url.strip():
            console.print("[yellow]No URL entered. Cancelled.[/yellow]")
            return
        url = url.strip().rstrip("/")

        suggested = url.replace("https://", "").replace("http://", "").split("/")[0]
        suggested = suggested.replace(".", "-").replace(":", "-")
        env_name = questionary.text(
            "Label (e.g. local, staging, production):",
            default=suggested
        ).ask()
        if not env_name or not env_name.strip():
            console.print("[yellow]Name is required. Cancelled.[/yellow]")
            return
        env_name = env_name.strip().lower().replace(" ", "-")

        save_environment(env_name, url)
        console.print(f"\n[green]✓ '[bold]{env_name}[/bold]' → {url} saved.[/green]")

    elif action == "Delete an environment":
        envs = list_environments()
        if not envs:
            console.print("[yellow]No environments configured.[/yellow]")
            return

        choices = [f"{e['name']}  ({e['base_url']})" for e in envs]
        selected = questionary.select(
            "Select environment to delete:",
            choices=choices,
            style=_SELECT_STYLE,
            pointer=_POINTER,
            instruction="",
        ).ask()
        if not selected:
            return

        env_name_to_delete = selected.split("  (")[0].strip()
        confirm = questionary.confirm(f"Delete '{env_name_to_delete}'?", default=True).ask()
        if confirm:
            env_file = get_env_path() / f"{env_name_to_delete}.json"
            if env_file.exists():
                env_file.unlink()
                console.print(f"[green]✓ '{env_name_to_delete}' deleted.[/green]")
            else:
                console.print("[yellow]Environment file not found.[/yellow]")
        else:
            console.print("[dim]Cancelled.[/dim]")



@cli.command(name="start-test")
@click.option("--no-metrics", is_flag=True, default=False, help="Hide the metrics box from the output.")
def start_test(no_metrics):
    """Run a test against a saved API endpoint.

    Flow: select endpoint → select base URL → fill placeholders → execute.

    Displays a REQUEST box, RESPONSE box (pretty-printed JSON), and a
    METRICS box (status, response time, size). If a token is detected
    in the response it is offered for reuse on Bearer-auth endpoints.

    \b
    Options:
      --no-metrics   Skip the metrics box for a cleaner output
    """
    display_header("API Endpoint Test Runner")
    if not is_initialized():
        console.print("[red]Error: Workspace not initialized. Run 'rouint init' first.[/red]")
        return

    # ── Main loop: select endpoint → select base URL → test ──────────────
    while True:
        try:
            if not EndpointManager().list_endpoints():
                console.print("[yellow]No endpoints found. Use 'rouint add-new-api' to create one.[/yellow]")
                return

            selected_ep = select_endpoint()
            if not selected_ep:
                return  # user cancelled / pressed Esc

            # ── Select Base URL ───────────────────────────────────────────────
            envs = list_environments()
            if not envs:
                console.print("[yellow]No base URLs configured. Run 'rouint add-base-url' first.[/yellow]")
                base_url = questionary.text(
                    "Enter a base URL to use now (e.g. http://127.0.0.1:8080):"
                ).ask()
                if not base_url or not base_url.strip():
                    console.print("[red]No base URL provided. Aborting.[/red]")
                    return
                base_url = base_url.strip().rstrip("/")
            else:
                env_choices = [f"{e['name']}  →  {e['base_url']}" for e in envs]
                selected_env_label = questionary.select("Select a base URL to test against:", choices=env_choices, style=_SELECT_STYLE, pointer=_POINTER, instruction="").ask()
                if not selected_env_label:
                    return
                chosen_env_name = selected_env_label.split("  →  ")[0].strip()
                base_url = get_base_url(chosen_env_name)
                console.print(f"[dim]Testing against: [bold]{base_url}[/bold][/dim]\n")

            # ── Resolve Placeholders ─────────────────────────────────────────
            path = selected_ep['path']
            placeholders = extract_placeholders(path)
            values = {}
            cancelled = False
            for p in placeholders:
                val = questionary.text(f"Enter value for {p}:", style=_SELECT_STYLE).ask()
                if val is None:
                    console.print("[yellow]Cancelled.[/yellow]")
                    cancelled = True
                    break
                while not val.strip():
                    console.print(f"[red]Value for '{p}' cannot be empty.[/red]")
                    val = questionary.text(f"Enter value for {p}:", style=_SELECT_STYLE).ask()
                    if val is None:
                        cancelled = True
                        break
                if cancelled:
                    break
                values[p] = val.strip()
            if cancelled:
                continue

            resolved_path = resolve_placeholders(path, values)
            clean_base_url = base_url.strip().rstrip("/")
            if not resolved_path.startswith("/"):
                resolved_path = "/" + resolved_path
            final_url = f"{clean_base_url}{resolved_path}"

            # Build the effective headers, applying temp token if applicable
            effective_headers = dict(selected_ep.get("headers") or {})
            auth = selected_ep.get("auth") or {}
            auth_type = auth.get("type", "none")

            # If endpoint uses Bearer auth, offer temp token reuse
            if auth_type in ("bearer token", "bearer"):
                temp_token = load_temp_token()
                if temp_token:
                    use_temp = questionary.confirm(
                        "Use saved temp token for authentication?", default=True
                    ).ask()
                    if use_temp:
                        effective_headers["Authorization"] = f"Bearer {temp_token}"
                        console.print("[green]✓ Using saved temp token.[/green]")
                    else:
                        token = questionary.password("Enter Bearer token:").ask()
                        if token:
                            effective_headers["Authorization"] = f"Bearer {token}"
                else:
                    token = questionary.password("Enter Bearer token:").ask()
                    if token:
                        effective_headers["Authorization"] = f"Bearer {token}"

            # ── REQUEST box ──────────────────────────────────────────────────
            request_lines = []
            request_lines.append(f"[bold]> {selected_ep['method']} {resolved_path} HTTP/1.1[/bold]")
            for h_key, h_val in effective_headers.items():
                if h_key.lower() in ("authorization", "auth"):
                    display_val = "[REDACTED]"
                else:
                    display_val = h_val
                request_lines.append(f"  {h_key}: {display_val}")
            request_body = selected_ep.get("body")
            request_lines.append("")
            if request_body:
                try:
                    parsed_body = json.loads(request_body)
                    pretty_body = json.dumps(parsed_body, indent=2)
                    request_lines.append("Request Body:")
                    for line in pretty_body.splitlines():
                        request_lines.append(f"  {line}")
                except (json.JSONDecodeError, TypeError):
                    request_lines.append(f"Request Body: {request_body}")
            else:
                request_lines.append("Request Body: None")

            console.print(Panel(
                "\n".join(request_lines),
                title="[bold blue]REQUEST[/bold blue]",
                title_align="left",
                border_style="blue",
                expand=True,
            ))

            # Execute
            console.print(f"\n[dim]Executing: {selected_ep['method']} {final_url}[/dim]\n")
            response = execute_request(
                url=final_url,
                method=selected_ep['method'],
                headers=effective_headers,
                body=selected_ep['body']
            )

            # ── RESPONSE box ─────────────────────────────────────────────────
            if response.error:
                console.print(Panel(
                    f"[red]{response.error}[/red]",
                    title="[bold red]RESPONSE[/bold red]",
                    title_align="left",
                    border_style="red",
                    expand=True,
                ))
                console.print()
                continue

            response_lines = []
            response_lines.append(f"[bold]< {response.status_line}[/bold]")
            for h_key, h_val in response.headers.items():
                response_lines.append(f"  {h_key}: {h_val}")
            response_lines.append("")
            if response.body:
                try:
                    parsed_resp = json.loads(response.body)
                    pretty_resp = json.dumps(parsed_resp, indent=2)
                    for line in pretty_resp.splitlines():
                        response_lines.append(f"  {line}")
                except (json.JSONDecodeError, TypeError):
                    response_lines.append(response.body)
            else:
                response_lines.append("  (empty body)")

            console.print(Panel(
                "\n".join(response_lines),
                title="[bold cyan]RESPONSE[/bold cyan]",
                title_align="left",
                border_style="cyan",
                expand=True,
            ))

            # ── METRICS box ──────────────────────────────────────────────────
            if not no_metrics:
                time_ms = response.elapsed_time * 1000
                size_b = response.response_size
                if size_b < 1024:
                    size_display = f"{size_b} B"
                else:
                    size_display = f"{size_b / 1024:.1f} KB"

                metrics_lines = [
                    f"HTTP Status:      {response.status_code}",
                    f"Response Time:    {time_ms:.0f} ms",
                    f"Response Size:    {size_display}",
                    f"Result:           HTTP request completed",
                ]

                result_color = "green" if 200 <= response.status_code < 400 else "yellow"
                console.print(Panel(
                    "\n".join(metrics_lines),
                    title=f"[bold {result_color}]METRICS[/bold {result_color}]",
                    title_align="left",
                    border_style=result_color,
                    expand=True,
                ))

            result_color = "green" if 200 <= response.status_code < 400 else "yellow"
            console.print(f"[{result_color}]✓ Response received successfully[/{result_color}]")

            # ── Token capture ────────────────────────────────────────────────
            extracted_token = extract_token_from_response(response)
            if extracted_token:
                save_choice = questionary.confirm(
                    "Token detected in response. Save as temp token for future requests?",
                    default=True
                ).ask()
                if save_choice:
                    token_path = save_temp_token(extracted_token)
                    console.print(f"[green]✓ Temp token saved to {token_path}[/green]")
                    console.print("[dim]It will be offered automatically when testing endpoints with Bearer auth.[/dim]")
                    console.print("[dim]Use 'rouint clear-token' to remove it.[/dim]")

            # ── Loop back ────────────────────────────────────────────────────
            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            return
        except Exception as e:
            console.print(f"\n[red]✗ Unexpected error: {e}[/red]")
            console.print("[dim]If this persists, report it at https://github.com/KavimugilRajasekar/Rouint/issues[/dim]")
            return

@cli.command(name="list-api")
def list_api():
    """List, inspect, edit, or delete saved endpoints.

    Select any saved endpoint to:

    \b
      Edit              — modify method, path, headers, auth, or body
      View Configuration — print the raw JSON config
      Delete            — permanently remove the endpoint
    """
    display_header("Manage Saved API Endpoints")
    if not is_initialized():
        console.print("[red]Error: Workspace not initialized. Run 'rouint init' first.[/red]")
        return

    while True:
        manager = EndpointManager()
        endpoints = manager.list_endpoints()

        if not endpoints:
            console.print("[yellow]No endpoints found. Use 'rouint add-new-api' to create one.[/yellow]")
            break

        selected_ep = select_endpoint()
        if not selected_ep:
            break

        # Action Menu
        action = questionary.select("What would you like to do with this endpoint?", choices=[
            "Edit Endpoint",
            "View Configuration",
            "Delete Endpoint",
            "Back"
        ], style=_SELECT_STYLE, pointer=_POINTER, instruction="").ask()

        if action == "Edit Endpoint":
            handle_endpoint_creation(existing_ep=selected_ep)
            console.print("[green]✓ Endpoint updated successfully![/green]")
        elif action == "View Configuration":
            console.print("\n[bold]Configuration:[/bold]")
            console.print(json.dumps(selected_ep, indent=2))
        elif action == "Delete Endpoint":
            confirm = questionary.confirm("Are you sure you want to delete this endpoint?").ask()
            if confirm:
                # Derive slug for deletion
                slug = selected_ep['name'].lower().replace(" ", "-").replace("/", "-")
                manager.delete_endpoint(slug)
                console.print("[red]✓ Endpoint deleted.[/red]")
        elif action == "Back":
            continue

@cli.command(name="clear-token")
def clear_token():
    """Clear the saved temporary Bearer token.

    When a token is detected in a response during 'rouint start-test',
    it is saved to .rouint-data/.temp_token for reuse on subsequent
    Bearer-auth requests. Use this command to remove it.
    """
    display_header("Clear Saved Temp Token")
    if not is_initialized():
        console.print("[red]Error: Workspace not initialized. Run 'rouint init' first.[/red]")
        return

    if clear_temp_token():
        console.print("[green]✓ Temp token cleared successfully.[/green]")
    else:
        console.print("[yellow]No temp token found to clear.[/yellow]")
