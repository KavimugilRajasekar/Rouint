import click
from rich.console import Console
from rich.table import Table
from rouint.utils.config import init_workspace, is_initialized
from rouint.core.manager import EndpointManager
from rouint.core.parser import extract_placeholders, resolve_placeholders, validate_path
from rouint.core.executor import execute_request
import questionary

console = Console()

def select_endpoint():
    """Shared helper to list and select an endpoint."""
    manager = EndpointManager()
    endpoints = manager.list_endpoints()

    if not endpoints:
        return None

    choices = [f"{ep['name']} [{ep['method']}]" for ep in endpoints]
    selected_label = questionary.select("Select an endpoint:", choices=choices).ask()

    if not selected_label:
        return None

    return next(ep for ep in endpoints if f"{ep['name']} [{ep['method']}]" == selected_label)

def handle_endpoint_creation(existing_ep=None):
    """Shared logic for creating and editing endpoints."""
    # Default values if editing
    defaults = existing_ep or {}

    console.print("[bold blue]Rouint — Endpoint Configuration[/bold blue]\n")

    # 1. Base URL / Environment
    env = defaults.get("base_url_ref", "local")

    # 2. HTTP Method
    method = questionary.select(
        "Which method should this endpoint use?",
        choices=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        default=defaults.get("method")
    ).ask()

    # 3. Path and Placeholders
    path = questionary.text(
        "Enter endpoint path (e.g., /api/v1/users/{user_id})",
        default=defaults.get("path", "")
    ).ask()

    valid, msg = validate_path(path)
    while not valid:
        console.print(f"[red]{msg}[/red]")
        path = questionary.text("Enter endpoint path").ask()
        valid, msg = validate_path(path)

    # 4. Headers
    headers = defaults.get("headers", {"Accept": "application/json", "Content-Type": "application/json"})
    add_header = questionary.confirm("Add/Edit custom headers?", default=True if headers else False).ask()
    if add_header:
        # Simple header editor: keep existing and allow adding
        while True:
            h_key = questionary.text("Header key (or empty to finish)").ask()
            if not h_key: break
            h_val = questionary.text(f"Value for {h_key}").ask()
            headers[h_key] = h_val

    # 5. Auth
    auth_type = questionary.select(
        "Authentication type?",
        choices=["None", "Bearer Token", "Custom"],
        default=defaults.get("auth", {}).get("type", "None").capitalize()
    ).ask()
    auth = {"type": auth_type.lower()}

    # 6. Body
    body = defaults.get("body")
    if method in ["POST", "PUT", "PATCH"]:
        has_body = questionary.confirm("Does this request have a body?", default=True if body else False).ask()
        if has_body:
            body = questionary.text("Enter JSON body", default=body or "").ask()
        else:
            body = None

    # 7. Name
    name = questionary.text("Give this endpoint a name", default=defaults.get("name", "")).ask()

    # Save
    manager = EndpointManager()
    # Determine if we are updating an existing slug
    slug = None
    if existing_ep:
        # Try to derive slug from the current endpoint's stored name or a known slug
        # For now, we use a simple derivation since we don't store slug in the ep object
        slug = name.lower().replace(" ", "-").replace("/", "-") # Simplified
        # In a real scenario, we'd pass the actual slug used in the filesystem

    endpoint_id = manager.save_endpoint(name, method, path, env, headers, auth, body, slug=slug)
    return endpoint_id

@click.group()
def cli():
    """Rouint — CLI-Based API Endpoint Management and Testing Tool"""
    pass

@cli.command()
def init():
    """Initialize the Rouint workspace."""
    success, message = init_workspace()
    if success:
        console.print(f"[green]✓ {message}[/green]")
        console.print("\nWorkspace: .rouint-data/\nGet started:\n  rouint start\n  rouint list")
    else:
        console.print(f"[red]✗ {message}[/red]")

@cli.command()
def add_new():
    """Create a new endpoint interactively."""
    if not is_initialized():
        console.print("[red]Error: Workspace not initialized. Run 'rouint init' first.[/red]")
        return

    id = handle_endpoint_creation()
    console.print(f"\n[green]✓ Endpoint saved successfully! (ID: {id})[/green]")

@cli.command()
def start():
    """Directly test an API endpoint."""
    if not is_initialized():
        console.print("[red]Error: Workspace not initialized. Run 'rouint init' first.[/red]")
        return

    selected_ep = select_endpoint()
    if not selected_ep:
        console.print("[yellow]No endpoints found or selection cancelled.[/yellow]")
        return

    # Resolve Placeholders
    path = selected_ep['path']
    placeholders = extract_placeholders(path)
    values = {}
    for p in placeholders:
        val = questionary.text(f"Enter value for {p}").ask()
        values[p] = val

    resolved_path = resolve_placeholders(path, values)

    # Final URL construction (simplification: just using local env for now)
    base_url = "http://localhost:8000"
    final_url = f"{base_url}{resolved_path}"

    console.print(f"\n[bold]Testing: {selected_ep['name']}[/bold]")
    console.print(f"URL: {final_url} ({selected_ep['method']})")

    # Execute
    response = execute_request(
        url=final_url,
        method=selected_ep['method'],
        headers=selected_ep['headers'],
        body=selected_ep['body']
    )

    # Display Results
    console.print("\n[bold cyan]RESPONSE[/bold cyan]")
    console.print("────────────────────────────────────────")
    if response.error:
        console.print(f"[red]{response.error}[/red]")
    else:
        console.print(f"Status: [green]{response.status_code}[/green]")
        console.print(f"Time: {response.elapsed_time:.3f}s")
        console.print("\nBody:\n", response.body)
    console.print("────────────────────────────────────────")

@cli.command()
def list():
    """List and manage saved endpoints."""
    if not is_initialized():
        console.print("[red]Error: Workspace not initialized. Run 'rouint init' first.[/red]")
        return

    while True:
        manager = EndpointManager()
        endpoints = manager.list_endpoints()

        if not endpoints:
            console.print("[yellow]No endpoints found. Use 'rouint add-new' to create one.[/yellow]")
            break

        # Display as a table for better visibility
        table = Table(title="Saved Endpoints")
        table.add_column("Name", style="cyan")
        table.add_column("Method", style="magenta")
        table.add_column("Path", style="green")

        for ep in endpoints:
            table.add_row(ep['name'], ep['method'], ep['path'])

        console.print(table)

        selected_ep = select_endpoint()
        if not selected_ep:
            break

        # Action Menu
        action = questionary.select(
            "What would you like to do with this endpoint?",
            choices=[
                "Edit Endpoint",
                "View Configuration",
                "Delete Endpoint",
                "Back"
            ]
        ).ask()

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
