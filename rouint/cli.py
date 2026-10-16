from __future__ import annotations

import json
import os
import platform
import re
from rouint import __version__
import sys
from pathlib import Path as _Path
from typing import Optional

# On Windows consoles running legacy encodings (like cp1252), reconfigure stdout/stderr to utf-8
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
from rouint.core.executor import execute_request, validate_url
from rouint.ui import (
    display_banner,
    display_header,
    box_width,
    interactive_launcher,
    is_in_launcher,
    reset_banner_state,
)
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from rouint.ui.controls import AlignedInquirerControl
import questionary
from questionary import Choice, Question
from prompt_toolkit.formatted_text import FormattedText
from questionary.prompts import common
from questionary.styles import merge_styles_default

console = Console(legacy_windows=False)

# ---------------------------------------------------------------------------
# Questionary custom style & pointer
# ---------------------------------------------------------------------------

def _get_select_style() -> questionary.Style:
    """Return a questionary Style built from the active theme. Called at use-time
    so theme changes mid-session are always reflected."""
    try:
        from rouint.ui.theme import build_qs_style
        return build_qs_style()
    except Exception:
        return questionary.Style([
            ("qmark",       "fg:#00bfff bold"),
            ("question",    "bold"),
            ("answer",      "fg:#00bfff bold"),
            ("pointer",     "fg:#00bfff bold"),
            ("highlighted", "fg:#00bfff bold"),
            ("selected",    "fg:#00bfff"),
            ("instruction", "fg:#666666"),
        ])


def _theme_accent() -> str:
    """Return the active theme's hex accent colour string (e.g. '#00bfff').
    Used to colour panels, syntax highlighting, and inline text."""
    try:
        from rouint.ui.theme import get_active_theme
        return get_active_theme()["accent"]
    except Exception:
        return "#00bfff"


def _theme_accent_rich() -> str:
    """Return the active theme's Rich accent name (e.g. 'cyan').
    Used in Rich markup like [bold cyan]...[/bold cyan]."""
    try:
        from rouint.ui.theme import get_active_theme
        return get_active_theme()["accent_rich"]
    except Exception:
        return "cyan"


_POINTER = "❯"

def prompt_endpoint_select(
    question_text: str,
    choices: list[Union[Choice, Separator]],
    style: Optional[questionary.Style] = None,
    pointer: str = "❯",
) -> Question:
    """
    Construct a Question prompt using AlignedInquirerControl to enable per-token
    highlighting (name-only glow) on hover.
    """
    merged_style = merge_styles_default([style or _get_select_style()])

    ic = AlignedInquirerControl(
        choices,
        pointer=pointer,
        use_indicator=False,
        use_shortcuts=False,
        show_selected=False,
        show_description=False,
        use_arrow_keys=True,
    )

    def get_prompt_tokens():
        # Simple prompt for the CLI endpoint selector
        return [
            ("class:qmark", "?"),
            ("class:question", f" {question_text} "),
            ("class:instruction", "(Use arrow keys)"),
        ]

    layout = common.create_inquirer_layout(ic, get_prompt_tokens)

    bindings = KeyBindings()

    @bindings.add(Keys.ControlC, eager=True)
    @bindings.add(Keys.Escape, eager=True)
    def _(event):
        event.app.exit(result=None)

    @bindings.add(Keys.ControlM, eager=True)
    def set_answer(event):
        ic.is_answered = True
        event.app.exit(result=ic.get_pointed_at().value)

    @bindings.add(Keys.Down, eager=True)
    def move_down(event):
        ic.select_next()
        while not ic.is_selection_valid():
            ic.select_next()

    @bindings.add(Keys.Up, eager=True)
    def move_up(event):
        ic.select_previous()
        while not ic.is_selection_valid():
            ic.select_previous()

    bindings.add(Keys.Down, eager=True)(move_down)
    bindings.add(Keys.Up, eager=True)(move_up)
    bindings.add("j", eager=True)(move_down)
    bindings.add("k", eager=True)(move_up)

    return Question(
        Application(
            layout=layout,
            key_bindings=bindings,
            style=merged_style,
        )
    )

def save_temp_token(token: str) -> str:
    """Persists a token to .rouint-data/.temp_token for reuse within the workspace."""
    token_path = get_data_path() / TEMP_TOKEN_FILE
    with open(token_path, "w") as f:
        f.write(token)
    # Ensure file is only readable by owner (sensitive)
    if platform.system().lower() != "windows":
        token_path.chmod(0o600)
    else:
        # On Windows, restrict file access to the current user only
        try:
            import subprocess as _sp
            username = os.environ.get("USERNAME", "")
            if username:
                _sp.run(
                    ["icacls", str(token_path), "/inheritance:r",
                     "/grant:r", f"{username}:(R,W)"],
                    capture_output=True, check=False,
                )
        except Exception:
            pass  # Best-effort; Windows home dirs are usually private
    return str(token_path)

def load_temp_token() -> Optional[str]:
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

def extract_token_from_response(response) -> Optional[str]:
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
    # [DELETE] is the longest method badge (8 chars); pad all badges to that width
    max_badge_len = max(len(f"[{ep['method']}]") for ep in endpoints)

    def _make_title(ep: dict) -> FormattedText:
        name_col  = ep['name'].ljust(max_name_len) + "  "
        badge_col = ("[" + ep["method"] + "]").ljust(max_badge_len) + "  "
        path_col  = ep.get("path", "")
        return FormattedText([
            ("", name_col),
            ("", badge_col),
            ("fg:#666666", path_col),
        ])

    choices = [
        questionary.Choice(title=_make_title(ep), value=ep['name'])
        for ep in endpoints
    ]
    choices.append(questionary.Choice(title="— Exit —", value="— Exit —"))

    q = prompt_endpoint_select(
        "Select an endpoint (or press Esc to exit):",
        choices=choices,
        style=_get_select_style(),
        pointer=_POINTER,
    )
    selected_name = q.ask()

    if not selected_name or selected_name == "— Exit —":
        return None

    return next(ep for ep in endpoints if ep['name'] == selected_name)


def handle_endpoint_creation(existing_ep=None):
    """Shared logic for creating and editing endpoints.
    Each step supports Esc to go back to the previous step.
    """
    defaults = existing_ep or {}
    console.print("[dim]Base URL is selected at test time — you can test this endpoint against any saved URL.[/dim]\n")

    # Step state
    method = defaults.get("method")
    path = defaults.get("path", "")
    headers = dict(defaults.get("headers") or {})
    auth = dict(defaults.get("auth") or {"type": "none"})
    body = defaults.get("body")
    files = list(defaults.get("files") or [])
    name = defaults.get("name", "")

    STEPS = ["method", "path", "headers", "auth", "body", "files", "name"]
    step = 0

    while step < len(STEPS):
        current = STEPS[step]

        # ── Step 1: Method ───────────────────────────────────────────────
        if current == "method":
            result = questionary.select(
                "HTTP method:",
                choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
                default=method,
                style=_get_select_style(),
                pointer=_POINTER,
                instruction="",
            ).ask()
            if result is None:
                console.print("[yellow]Cancelled.[/yellow]")
                return None
            method = result
            # Reset body/files/headers defaults if method changes
            if not defaults.get("headers"):
                headers = {"Accept": "application/json"}
                if method in ["POST", "PUT", "PATCH"]:
                    headers["Content-Type"] = "application/json"
            step += 1

        # ── Step 2: Path ─────────────────────────────────────────────────
        elif current == "path":
            result = questionary.text(
                "Endpoint path (e.g., /api/v1/users/{id}):",
                default=path,
            ).ask()
            if result is None:
                step -= 1
                continue
            if not result.strip():
                console.print("[red]✗ Path is required.[/red]")
                continue
            result = result.strip()
            if not result.startswith("/"):
                result = "/" + result
            valid, msg = validate_path(result)
            if not valid:
                console.print(f"[red]✗ {msg}[/red]")
                continue
            path = result
            step += 1

        # ── Step 3: Headers ──────────────────────────────────────────────
        elif current == "headers":
            label = "Saved headers:" if defaults.get("headers") else f"Default headers for {method}:"
            console.print(f"\n[bold]{label}[/bold]")
            for hk, hv in headers.items():
                console.print(f"  [cyan]{hk}[/cyan]: {hv}")
            console.print()

            add_header = questionary.confirm("Add or edit headers?", default=False).ask()
            if add_header is None:
                step -= 1
                continue
            if add_header:
                console.print("[dim]Enter header name, then value. Empty name to finish. Esc to go back.[/dim]\n")
                while True:
                    h_key = questionary.text("Header name:").ask()
                    if h_key is None:
                        break  # Esc — stop adding headers, stay on this step
                    if not h_key.strip():
                        break  # empty — done
                    if ":" in h_key:
                        console.print("[yellow]⚠  Enter ONLY the header name, not 'Name: Value'.[/yellow]\n")
                        continue
                    h_val = questionary.text(f"Value for '{h_key.strip()}':").ask()
                    if h_val is None:
                        break  # Esc — stop adding
                    headers[h_key.strip()] = h_val.strip()
            step += 1

        # ── Step 4: Auth ─────────────────────────────────────────────────
        elif current == "auth":
            current_auth_type = auth.get("type", "none")
            display_default = current_auth_type.title() if current_auth_type != "bearer token" else "Bearer Token"
            result = questionary.select(
                "Authentication type?",
                choices=["None", "Bearer Token", "Custom"],
                default=display_default,
                style=_get_select_style(),
                pointer=_POINTER,
                instruction="",
            ).ask()
            if result is None:
                step -= 1
                continue
            auth = {"type": result.lower()}
            if result == "Custom":
                saved_header = auth.get("header", "Authorization")
                saved_value = auth.get("value", "")
                custom_header = questionary.text("Custom auth header name:", default=saved_header).ask()
                if custom_header is None:
                    continue  # Esc — re-show auth select
                if custom_header.strip():
                    custom_value = questionary.text(f"Value for '{custom_header.strip()}':", default=saved_value).ask()
                    if custom_value is None:
                        continue  # Esc — re-show auth select
                    auth["header"] = custom_header.strip()
                    auth["value"] = custom_value.strip()
                    headers[custom_header.strip()] = custom_value.strip()
            step += 1

        # ── Step 5: Body ─────────────────────────────────────────────────
        elif current == "body":
            if method not in ["POST", "PUT", "PATCH", "DELETE"]:
                body = None
                step += 1
                continue

            has_body = questionary.confirm(
                "Does this request have a body?",
                default=bool(body),
            ).ask()
            if has_body is None:
                step -= 1
                continue
            if has_body:
                console.print("[dim]Enter raw JSON body.[/dim]")
                while True:
                    result = questionary.text("JSON body:", default=body or "").ask()
                    if result is None:
                        break  # Esc — re-show has_body confirm
                    if not result.strip():
                        console.print("[red]✗ Body cannot be empty.[/red]")
                        continue
                    result = result.strip()
                    try:
                        json.loads(result)
                        body = result
                        break
                    except ValueError:
                        console.print("[red]✗ Invalid JSON — check syntax and try again.[/red]")
                        console.print('[dim]  Example: {"key": "value"}[/dim]')
                if result is None:
                    continue  # Esc on body input — re-show has_body
            else:
                body = None
            step += 1

        # ── Step 6: Files ────────────────────────────────────────────────
        elif current == "files":
            if method not in ["POST", "PUT", "PATCH", "DELETE"]:
                files = []
                step += 1
                continue

            if files:
                console.print("\n[bold]Saved file attachments:[/bold]")
                for i, f in enumerate(files, 1):
                    console.print(f"  [{i}] [cyan]{f.get('field', 'file')}[/cyan] → {f.get('path', '')}")
                console.print()

            add_files = questionary.confirm("Attach files to this request?", default=bool(files)).ask()
            if add_files is None:
                step -= 1
                continue
            if add_files:
                console.print("[dim]File path + field name per file. Empty path to finish. Esc to go back.[/dim]\n")
                new_files = []
                while True:
                    file_path = questionary.text("File path:").ask()
                    if file_path is None:
                        break  # Esc — stop adding files
                    if not file_path.strip():
                        break  # empty — done
                    file_path = file_path.strip()
                    if not _Path(file_path).exists():
                        console.print(f"[red]✗ File not found: {file_path}[/red]")
                        continue
                    if not _Path(file_path).is_file():
                        console.print(f"[red]✗ Not a file: {file_path}[/red]")
                        continue
                    field_name = questionary.text("Form field name:", default="file").ask()
                    if field_name is None:
                        break
                    field_name = field_name.strip() or "file"
                    new_files.append({"field": field_name, "path": file_path})
                    console.print(f"[green]✓ {field_name} → {file_path}[/green]")
                files = new_files
                if files:
                    headers.pop("Content-Type", None)
                    console.print("[dim]Content-Type removed — curl sets multipart/form-data automatically.[/dim]")
            else:
                files = []
            step += 1

        # ── Step 7: Name ─────────────────────────────────────────────────
        elif current == "name":
            result = questionary.text("Give this endpoint a name:", default=name).ask()
            if result is None:
                step -= 1
                continue
            if not result.strip():
                console.print("[red]✗ Name is required.[/red]")
                continue
            name = result.strip()
            step += 1

    # Save
    manager = EndpointManager()
    slug = existing_ep['id'].replace("ep_", "") if existing_ep else None
    endpoint_id = manager.save_endpoint(name, method, path, None, headers, auth, body, slug=slug, files=files)
    return endpoint_id



@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="Rouint")
@click.pass_context
def cli(ctx):
    """Rouint — cURL-powered API endpoint management & testing tool.

    Define endpoints once, organize them locally, and test them against
    any environment directly from your terminal.

    Run without a command to see the full command menu.
    """
    reset_banner_state()
    # Load and apply the persisted theme before any rendering happens
    try:
        from rouint.ui.theme import load_theme
        load_theme()
    except Exception:
        pass
    if ctx.invoked_subcommand is None:
        interactive_launcher(ctx)

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
        if not is_in_launcher():
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
      5. Body         — JSON body for POST / PUT / PATCH / DELETE (optional)
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
    if not is_in_launcher():
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
        style=_get_select_style(),
        pointer=_POINTER,
        instruction="",
    ).ask()

    if not action:
        return

    if action == "Add a new base URL":
        console.print("\n[dim]Examples: http://127.0.0.1:8080  |  https://api.myapp.com  |  https://staging.myapp.com[/dim]\n")

        while True:
            url = questionary.text("Base URL:").ask()
            if not url or not url.strip():
                console.print("[yellow]No URL entered. Cancelled.[/yellow]")
                return
            url = url.strip().rstrip("/")
            if not (url.startswith("http://") or url.startswith("https://")):
                console.print(f"[red]✗ Invalid URL — must start with http:// or https://[/red]")
                continue
            host = url.split("/")[2] if url.count("/") >= 2 else ""
            if not host:
                console.print(f"[red]✗ Invalid URL — missing host (e.g. 127.0.0.1:8080)[/red]")
                continue
            break

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
            style=_get_select_style(),
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
                console.print("[yellow]No base URLs configured.[/yellow]")
                console.print("[dim]Run [bold]rouint add-base-url[/bold] to add one first, then come back.[/dim]")
                return
            else:
                env_choices = [f"{e['name']}  →  {e['base_url']}" for e in envs]
                selected_env_label = questionary.select("Select a base URL to test against:", choices=env_choices, style=_get_select_style(), pointer=_POINTER, instruction="").ask()
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
                val = questionary.text(f"Enter value for {p}:", style=_get_select_style()).ask()
                if val is None:
                    console.print("[yellow]Cancelled.[/yellow]")
                    cancelled = True
                    break
                while not val.strip():
                    console.print(f"[red]Value for '{p}' cannot be empty.[/red]")
                    val = questionary.text(f"Enter value for {p}:", style=_get_select_style()).ask()
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

            # ── Validate final URL ────────────────────────────────────────────
            url_ok, url_err = validate_url(final_url)
            if not url_ok:
                console.print(f"[red]✗ {url_err}[/red]")
                continue

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
            # Collect files at test time — validate paths exist
            saved_files = selected_ep.get("files") or []
            effective_files = []
            if saved_files:
                console.print(f"\n[dim]This endpoint has {len(saved_files)} file attachment(s) defined.[/dim]")
                for entry in saved_files:
                    field = entry.get("field", "file")
                    saved_path = entry.get("path", "").strip()
                    file_path = questionary.text(
                        f"File path for field '{field}':",
                        default=saved_path,
                    ).ask()
                    if file_path is None:
                        console.print("[yellow]Cancelled.[/yellow]")
                        cancelled = True
                        break
                    file_path = file_path.strip()
                    if not _Path(file_path).exists():
                        console.print(f"[red]✗ File not found: {file_path} — skipping.[/red]")
                        continue
                    effective_files.append({"field": field, "path": file_path})
                if cancelled:
                    continue

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
            if effective_files:
                request_lines.append("Attachments (multipart/form-data):")
                for f in effective_files:
                    request_lines.append(f"  {f['field']} → {f['path']}")
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
                if not effective_files:
                    request_lines.append("Request Body: None")

            console.print(Panel(
                "\n".join(request_lines),
                title="[bold]REQUEST[/bold]",
                title_align="left",
                border_style=_theme_accent_rich(),
                expand=True,
            ))

            # Execute
            console.print(f"\n[dim]Executing: {selected_ep['method']} {final_url}[/dim]\n")
            response = execute_request(
                url=final_url,
                method=selected_ep['method'],
                headers=effective_headers,
                body=selected_ep['body'],
                files=effective_files if effective_files else None,
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
                title=f"[bold {_theme_accent_rich()}]RESPONSE[/bold {_theme_accent_rich()}]",
                title_align="left",
                border_style=_theme_accent_rich(),
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

# ---------------------------------------------------------------------------
# Wrapper builders (for --show-wrapper)
# ---------------------------------------------------------------------------

def build_curl_wrapper(ep: dict, base_url: str = "<base_url>") -> str:
    """
    Reconstruct the curl command that Rouint would run for a given endpoint.
    Uses a placeholder base URL when none is supplied.
    Mirrors the logic in rouint/platforms/linux/executor.py exactly.
    """
    method  = ep.get("method", "GET")
    path    = ep.get("path", "/")
    headers = dict(ep.get("headers") or {})
    body    = ep.get("body")
    files   = list(ep.get("files") or [])
    auth    = ep.get("auth") or {}

    # Inject auth header preview
    auth_type = auth.get("type", "none")
    if auth_type in ("bearer token", "bearer"):
        headers["Authorization"] = "Bearer <token>"
    elif auth_type == "custom":
        h = auth.get("header", "Authorization")
        headers[h] = auth.get("value", "<value>")

    url = f"{base_url.rstrip('/')}{path}"

    # Build as a list of token-pairs / single tokens (each becomes one line)
    segments = [
        "curl",
        "-i -s",
        f"-X {method}",
        f'-w "\\n%{{http_code}}\\n%{{time_total}}\\n%{{size_download}}"',
        f'"{url}"',
    ]

    if files:
        filtered = {k: v for k, v in headers.items() if k.lower() != "content-type"}
        for k, v in filtered.items():
            segments.append(f'-H "{k}: {v}"')
        for entry in files:
            field = entry.get("field", "file")
            fpath = entry.get("path", "<path>")
            segments.append(f'-F "{field}=@{fpath}"')
        if body:
            segments.append(f'-F "data={body}"')
    else:
        for k, v in headers.items():
            segments.append(f'-H "{k}: {v}"')
        if body:
            segments.append(f"-d '{body}'")

    # First segment on its own line, rest indented with backslash continuation
    lines = [segments[0]]
    for seg in segments[1:]:
        lines.append(f"  {seg}")
    return " \\\n".join(lines)


def build_powershell_wrapper(ep: dict, base_url: str = "<base_url>") -> str:
    """
    Reconstruct the key PowerShell Invoke-WebRequest call that Rouint would
    run for a given endpoint.
    Mirrors the logic in rouint/platforms/windows/executor.py exactly.
    """
    method  = ep.get("method", "GET")
    path    = ep.get("path", "/")
    headers = dict(ep.get("headers") or {})
    body    = ep.get("body")
    files   = list(ep.get("files") or [])
    auth    = ep.get("auth") or {}

    # Inject auth header preview
    auth_type = auth.get("type", "none")
    if auth_type in ("bearer token", "bearer"):
        headers["Authorization"] = "Bearer <token>"
    elif auth_type == "custom":
        h = auth.get("header", "Authorization")
        headers[h] = auth.get("value", "<value>")

    url = f"{base_url.rstrip('/')}{path}"

    lines = []
    lines.append("$headers = @{")
    effective_headers = {k: v for k, v in headers.items()
                         if not (files and k.lower() == "content-type")}
    for k, v in effective_headers.items():
        lines.append(f"    '{k}' = '{v}'")
    lines.append("}")
    lines.append("")

    lines.append("$params = @{")
    lines.append(f"    Uri     = '{url}'")
    lines.append(f"    Method  = '{method}'")
    lines.append( "    Headers = $headers")
    lines.append( "    UseBasicParsing = $true")
    lines.append( "    SkipHttpErrorCheck = $true   # PS 7+ only")
    lines.append("}")
    lines.append("")

    if files:
        lines.append("# PS 7+: native -Form file upload")
        lines.append("$form = @{")
        for entry in files:
            field = entry.get("field", "file")
            fpath = entry.get("path", "<path>")
            lines.append(f"    '{field}' = Get-Item -LiteralPath '{fpath}'")
        if body:
            lines.append(f"    'data' = '{body}'")
        lines.append("}")
        lines.append("$params['Form'] = $form")
        lines.append("")
    elif body:
        lines.append(f"$params['Body'] = [System.Text.Encoding]::UTF8.GetBytes('{body}')")
        lines.append("")

    lines.append("$response = Invoke-WebRequest @params")

    return "\n".join(lines)


def _copy_to_clipboard(text: str) -> bool:
    """
    Copy text to the system clipboard using native tools.
    Returns True on success, False if no clipboard tool is available.

    Platform tools tried (in order):
      Linux   — xclip, xsel, wl-copy (Wayland)
      macOS   — pbcopy
      Windows — clip.exe (built-in)
    """
    import subprocess as _sp
    system = platform.system().lower()

    try:
        if system == "darwin":
            _sp.run(["pbcopy"], input=text.encode(), check=True)
            return True
        elif system == "windows":
            _sp.run(["clip"], input=text.encode("utf-16-le"), check=True)
            return True
        else:
            # Linux / other Unix — try in order of preference
            for cmd in (
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
                ["wl-copy"],
            ):
                if _sp.run(["which", cmd[0]], capture_output=True).returncode == 0:
                    _sp.run(cmd, input=text.encode(), check=True)
                    return True
    except Exception:
        pass
    return False


def _render_wrapper_panel(ep: dict) -> None:
    """
    Detect the current platform, build the matching wrapper command, and
    print it inside a styled panel using Rouint theme colours (no dark background).
    Offers to embed a real base URL if any environments are saved.
    """
    is_windows = platform.system().lower() == "windows"

    # ── Optionally embed a real base URL ─────────────────────────────────
    base_url = "<base_url>"
    try:
        envs = list_environments()
        if envs:
            env_choices = [f"{e['name']}  →  {e['base_url']}" for e in envs]
            env_choices.append("— use <base_url> placeholder —")
            picked = questionary.select(
                "Embed a base URL? (optional):",
                choices=env_choices,
                style=_get_select_style(),
                pointer=_POINTER,
                instruction="",
            ).ask()
            if picked and "→" in picked:
                base_url = picked.split("→")[1].strip()
    except Exception:
        pass

    if is_windows:
        wrapper = build_powershell_wrapper(ep, base_url=base_url)
        lang_label = "PowerShell  ·  Windows"
        border = _theme_accent_rich()
        title_color = _theme_accent_rich()
    else:
        wrapper = build_curl_wrapper(ep, base_url=base_url)
        lang_label = "curl  ·  Linux / macOS"
        border = _theme_accent_rich()
        title_color = _theme_accent_rich()

    from rich.text import Text

    # ── Colour-code the command using the active theme accent ─────────────
    def _style_curl_line(line: str) -> Text:
        accent = _theme_accent()
        t = Text()
        stripped = line.lstrip()
        indent = " " * (len(line) - len(stripped))
        if stripped.startswith("curl"):
            t.append(indent)
            t.append("curl", style=f"bold {accent}")
        elif stripped.startswith("-X "):
            flag, _, val = stripped.partition(" ")
            t.append(indent)
            t.append(flag, style="bold white")
            t.append(" ")
            t.append(val.rstrip(" \\"), style=f"bold {accent}")
        elif stripped.startswith("-H "):
            _, _, rest = stripped.partition(" ")
            rest = rest.strip().rstrip(" \\").strip('"')
            key, _, val = rest.partition(": ")
            t.append(indent)
            t.append("-H ", style="white")
            t.append('"', style="dim")
            t.append(key, style=f"{accent}")
            t.append(": ", style="dim")
            t.append(val, style="white")
            t.append('"', style="dim")
        elif stripped.startswith("-F "):
            _, _, rest = stripped.partition(" ")
            rest = rest.strip().rstrip(" \\").strip('"')
            t.append(indent)
            t.append("-F ", style="white")
            t.append(f'"{rest}"', style=accent)
        elif stripped.startswith("-d "):
            _, _, rest = stripped.partition(" ")
            t.append(indent)
            t.append("-d ", style="white")
            t.append(rest.strip().rstrip(" \\"), style="bright_white")
        elif stripped.startswith("-w "):
            _, _, rest = stripped.partition(" ")
            t.append(indent)
            t.append("-w ", style="white")
            t.append(rest.strip().rstrip(" \\"), style="dim")
        elif stripped.startswith('"') and ("<base_url>" in stripped or stripped.startswith('"http')):
            t.append(indent)
            t.append(stripped.rstrip(" \\"), style="bold bright_white")
        else:
            t.append(indent)
            t.append(stripped.rstrip(" \\"), style="dim white")
        if line.rstrip().endswith("\\"):
            t.append(" \\", style="dim")
        return t

    def _style_ps_line(line: str) -> Text:
        accent = _theme_accent()
        t = Text()
        stripped = line.lstrip()
        indent = " " * (len(line) - len(stripped))
        if stripped.startswith("#"):
            t.append(indent + stripped, style="dim")
        elif stripped.startswith("$headers") or stripped.startswith("$params") or stripped.startswith("$form"):
            varname, _, rest = stripped.partition(" ")
            t.append(indent)
            t.append(varname, style=f"bold {accent}")
            t.append(" " + rest, style="white")
        elif stripped.startswith("$response") or stripped.startswith("Invoke-WebRequest"):
            t.append(indent)
            t.append(stripped, style=f"bold {accent}")
        elif "=" in stripped and not stripped.startswith("}"):
            key, _, val = stripped.partition(" = ")
            t.append(indent)
            t.append(key, style=accent)
            t.append(" = ", style="dim")
            t.append(val, style="bright_white")
        elif stripped in ("{", "}", "@{", "@{}"):
            t.append(indent + stripped, style="dim white")
        else:
            t.append(indent + stripped, style="white")
        return t

    lines = wrapper.splitlines()
    styled_lines: list[Text] = []
    for raw_line in lines:
        if is_windows:
            styled_lines.append(_style_ps_line(raw_line))
        else:
            styled_lines.append(_style_curl_line(raw_line))

    from rich.console import Group as RichGroup

    from rich.text import Text as RText

    content = RichGroup(*styled_lines)

    console.print()
    console.print(Panel(
        content,
        title=f"[bold {title_color}]WRAPPER COMMAND  ({lang_label})[/bold {title_color}]",
        title_align="left",
        border_style=border,
        expand=True,
    ))

    # Auto-copy the raw command to the system clipboard
    if _copy_to_clipboard(wrapper):
        console.print("[dim]✓ Copied to clipboard.[/dim]")
    else:
        console.print("[dim]⚠  Clipboard unavailable — copy manually from above.[/dim]")


@cli.command(name="list-api")
@click.option(
    "--show-wrapper",
    is_flag=True,
    default=False,
    help="Show the native tool command (curl / PowerShell) for each selected endpoint.",
)
def list_api(show_wrapper):
    """List, inspect, edit, or delete saved endpoints.

    Select any saved endpoint to:

    \b
      Edit              — modify method, path, headers, auth, or body
      View Configuration — print the raw JSON config
      Delete            — permanently remove the endpoint
      Show Wrapper      — display the native curl / PowerShell command

    \b
    Options:
      --show-wrapper   Go straight to the wrapper view after selecting an endpoint
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

        # --show-wrapper: skip the action menu, render wrapper and loop back
        if show_wrapper:
            _render_wrapper_panel(selected_ep)
            console.print()
            continue

        # Action Menu
        action = questionary.select("What would you like to do with this endpoint?", choices=[
            "Edit Endpoint",
            "View Configuration",
            "Show Wrapper",
            "Delete Endpoint",
            "Back"
        ], style=_get_select_style(), pointer=_POINTER, instruction="").ask()

        if action == "Edit Endpoint":
            handle_endpoint_creation(existing_ep=selected_ep)
            console.print("[green]✓ Endpoint updated successfully![/green]")
        elif action == "View Configuration":
            console.print("\n[bold]Configuration:[/bold]")
            console.print(json.dumps(selected_ep, indent=2))
        elif action == "Show Wrapper":
            _render_wrapper_panel(selected_ep)
            console.print()
        elif action == "Delete Endpoint":
            confirm = questionary.confirm("Are you sure you want to delete this endpoint?").ask()
            if confirm:
                slug = selected_ep['id'].replace("ep_", "")
                manager.delete_endpoint(slug)
                console.print("[red]✓ Endpoint deleted.[/red]")
        elif action == "Back":
            break

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


@cli.command(name="set-theme")
def set_theme():
    """Choose a colour theme for the Rouint CLI interface.

    An interactive picker with a real-time live preview — as you arrow
    through themes the ROUINT banner above the list instantly repaints in
    the highlighted theme's colour. Press Enter to confirm, Esc to cancel.
    The selection is persisted to .rouint-data/theme and applied immediately.
    """
    from rouint.ui.theme import (
        THEMES,
        get_active_theme_key,
        save_theme,
        apply_theme,
        build_qs_style,
    )
    from prompt_toolkit import Application
    from prompt_toolkit.formatted_text import to_formatted_text, HTML, AnyFormattedText
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl

    theme_keys = list(THEMES.keys())
    active_key = get_active_theme_key()

    # Always open on the first theme so the user sees the full list from the top.
    # The ✓ marker on the active theme shows what's currently selected.
    initial_idx = 0

    # Mutable state shared between the live-preview control and key bindings
    state = {"idx": initial_idx, "confirmed": False, "cancelled": False}

    # ── ANSI colour map from theme → prompt_toolkit colour string ────────────
    # Use the mid-tone (index 1) from ascii_colours as the accent for the list.
    _PT_COLOUR = {
        key: THEMES[key]["ascii_colours"][1]
        for key in THEMES
    }

    # ── Banner control ────────────────────────────────────────────────────────
    # Called on every repaint — reads state["idx"] to pick the preview colour.
    ASCII_LINES = [
        "█▀▀█ █▀▀█ █  █ ▀█▀ █  █ ▀█▀",
        "█▄▄▀ █  █ █  █  █  █▀▄█  █ ",
        "█  █ █▄▄█ ▀▄▄▀ ▄█▄ █  █  █ ",
    ]

    def get_banner_text():
        # Clamp to valid theme index — cancel row (idx == len(theme_keys)) shows
        # the last theme preview rather than crashing with an index error.
        safe_idx = min(state["idx"], len(theme_keys) - 1)
        key    = theme_keys[safe_idx]
        colour = _PT_COLOUR.get(key, "#00bfff")
        theme  = THEMES[key]

        # Per-line colours: bright → mid → deep for depth
        ascii_colours = theme.get("ascii_colours", [colour, colour, colour])

        tokens = []

        # ── Command title (replaces the static display_header above the app) ──
        tokens.append(("bold", "\n"))
        for i, line in enumerate(ASCII_LINES):
            c = ascii_colours[i] if i < len(ascii_colours) else colour
            tokens.append((f"fg:{c} bold", line + "\n"))
        tokens.append(("", "\n"))
        tokens.append((f"fg:{colour} bold", f"  ◆  Set Colour Theme\n"))
        tokens.append(("fg:#555555", f"  ──────────────────────────────\n"))
        tokens.append(("", "\n"))

        # ── Live preview: theme name + description in accent colour ──────────
        tokens.append((f"fg:{colour} bold", f"  {theme['display_name']}\n"))
        tokens.append(("fg:#767676",         f"  {theme['description']}\n"))
        tokens.append(("", "\n"))

        return tokens

    banner_control = FormattedTextControl(get_banner_text, focusable=False)
    banner_window  = Window(content=banner_control, dont_extend_height=True)

    # ── Choice list control ───────────────────────────────────────────────────
    POINTER = "❯"

    def get_list_text():
        tokens = []
        tokens.append(("fg:#888888", "  Select a theme  (↑↓ arrows · Enter confirm · Esc cancel)\n\n"))
        for i, key in enumerate(theme_keys):
            theme  = THEMES[key]
            colour = _PT_COLOUR.get(key, "#00bfff")
            is_sel = i == state["idx"]
            is_act = key == active_key

            if is_sel:
                ptr   = f" {POINTER} "
                style = f"fg:{colour} bold"
            else:
                ptr   = "   "
                style = ""

            active_mark = " ✓" if is_act else "  "
            name_col    = f"{theme['display_name']:<16}{active_mark}  "
            desc_col    = theme["description"]

            tokens.append((style, ptr + name_col))
            tokens.append(("fg:#767676" if not is_sel else "fg:#767676", desc_col + "\n"))

        tokens.append(("", "\n"))

        # Cancel row
        is_cancel = state["idx"] == len(theme_keys)
        if is_cancel:
            tokens.append(("fg:#888888 bold", f" {POINTER}  — Cancel —\n"))
        else:
            tokens.append(("fg:#555555", "    — Cancel —\n"))

        return tokens

    list_control = FormattedTextControl(get_list_text, focusable=True)
    list_window  = Window(content=list_control, dont_extend_height=True)

    # ── Layout ────────────────────────────────────────────────────────────────
    # The filler Window at the bottom absorbs all remaining vertical space so
    # the banner + list stay at the top in full-screen mode.
    root = HSplit([
        banner_window,
        list_window,
        Window(),   # fills remaining space — keeps content pinned to top
    ])
    layout = Layout(root, focused_element=list_window)

    # ── Key bindings ──────────────────────────────────────────────────────────
    kb = KeyBindings()
    total_rows = len(theme_keys) + 1  # themes + cancel row

    @kb.add(Keys.Up,   eager=True)
    @kb.add("k",       eager=True)
    def move_up(event):
        state["idx"] = (state["idx"] - 1) % total_rows

    @kb.add(Keys.Down, eager=True)
    @kb.add("j",       eager=True)
    def move_down(event):
        state["idx"] = (state["idx"] + 1) % total_rows

    @kb.add(Keys.ControlM, eager=True)   # Enter
    def confirm(event):
        state["confirmed"] = True
        event.app.exit()

    @kb.add(Keys.Escape,  eager=True)
    @kb.add(Keys.ControlC, eager=True)
    @kb.add(Keys.ControlQ, eager=True)
    def cancel(event):
        state["cancelled"] = True
        event.app.exit()

    # ── Run the application ───────────────────────────────────────────────────
    # full_screen=True takes over the entire terminal (like vim/htop).
    # On exit the terminal is fully restored — no leftover banner or artifacts.
    app = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        mouse_support=False,
    )
    app.run()

    # ── Handle result ─────────────────────────────────────────────────────────
    if state["cancelled"] or not state["confirmed"]:
        console.print("\n[dim]No changes made.[/dim]")
        return

    selected = theme_keys[state["idx"]] if state["idx"] < len(theme_keys) else None

    if not selected:
        console.print("\n[dim]No changes made.[/dim]")
        return

    if selected == active_key:
        theme = THEMES[selected]
        console.print(
            f"\n[dim]Already using [/dim][bold]{theme['display_name']}[/bold]"
            "[dim]. No change.[/dim]"
        )
        return

    apply_theme(selected)
    save_theme(selected)

    theme  = THEMES[selected]
    colour = theme["accent_rich"]
    console.print()
    console.print(
        f"[bold {colour}]✓ Theme set to {theme['display_name']}[/bold {colour}]"
        f"  [dim]{theme['description']}[/dim]"
    )
    console.print("[dim]Saved to .rouint-data/theme — active across all sessions.[/dim]")
