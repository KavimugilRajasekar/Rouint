"""
Reusable Rich-based UI components for Rouint's CLI.

This module centralises all banner / header rendering so that ``cli.py``
(or any other caller) can import a single, well-named function instead of
duplicating Rich boiler-plate.

Components exposed
------------------
- :func:`display_header`  — the boxed ROUINT ASCII-art header with version
  and workspace path.  An optional *subtitle* is printed beneath the box.
- :func:`display_banner`  — the full landing banner (header + available
  commands table) shown when the CLI is invoked without a sub-command.
- :func:`box_width`       — shared helper that computes a responsive panel
  width (60 % of terminal, clamped to 40–100 columns).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from rouint import __version__

# ---------------------------------------------------------------------------
# Shared console instance
# ---------------------------------------------------------------------------

console = Console(legacy_windows=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ASCII_ART = (
    "[bold cyan]█▀▀█ █▀▀█ █  █ ▀█▀ █  █ ▀█▀[/bold cyan]\n"
    "[bold cyan]█▄▄▀ █  █ █  █  █  █▀▄█  █ [/bold cyan]\n"
    "[bold cyan]█  █ █▄▄█ ▀▄▄▀ ▄█▄ █  █  █ [/bold cyan]"
)

_TAGLINE = "cURL-Powered API Management & Testing Tool"

# (command, description) pairs for the available-commands table.
_COMMANDS: list[tuple[str, str]] = [
    ("init",         "Initialize the Rouint workspace in current directory"),
    ("add-base-url", "Add & manage global base URLs (local, staging, server)"),
    ("add-new-api",  "Define a new API endpoint (method, path, headers, body)"),
    ("start-test",   "Select an endpoint & base URL to execute test request"),
    ("list-api",     "List, inspect, edit, or delete saved endpoints"),
    ("clear-token",  "Clear the saved temporary Bearer token"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def box_width(console: Optional[Console] = None) -> int:
    """
    Returns the current terminal width for full-width panels.
    Falls back to 80 if terminal width cannot be detected.
    """
    c = console or Console()
    return c.width or 80


def _truncate_cwd(cwd: Union[Path, str], max_len: int = 42) -> str:
    """Return *cwd* as a string, prefix-truncated to *max_len* characters."""
    cwd_str = str(cwd)
    if len(cwd_str) > max_len:
        return "..." + cwd_str[-(max_len - 3):]
    return cwd_str


# ---------------------------------------------------------------------------
# Banner / header components & session state
# ---------------------------------------------------------------------------

_session_banner_displayed: bool = False
_in_interactive_launcher: bool = False


def is_in_launcher() -> bool:
    """Check whether the current command is running inside the interactive launcher."""
    return _in_interactive_launcher


def set_in_launcher(val: bool) -> None:
    """Set whether the CLI is currently inside the interactive launcher loop."""
    global _in_interactive_launcher
    _in_interactive_launcher = val


def reset_banner_state() -> None:
    """Reset the session banner display tracker so the banner can be shown once again."""
    global _session_banner_displayed
    _session_banner_displayed = False


def display_header(subtitle: Optional[str] = None, force_banner: bool = False) -> None:
    """
    Print the boxed ROUINT ASCII-art header and optional command subtitle.

    The ASCII art banner is displayed only once per session unless *force_banner*
    is True. Subsequent calls within the same session render only the subtitle
    block, eliminating redundant banners across command transitions.

    Parameters
    ----------
    subtitle:
        Optional one-line command subtitle printed beneath the box, e.g.
        ``"Workspace Initialization"``. When provided, a hint about
        pressing *Esc* to exit is appended.
    force_banner:
        Force rendering of the full ASCII logo banner even if already displayed.
    """
    global _session_banner_displayed

    if not _session_banner_displayed or force_banner:
        grid = Table.grid(padding=(0, 4))
        grid.add_column()
        grid.add_column()

        info_text = (
            f"[bold white]Rouint CLI[/bold white] [cyan]v{__version__}[/cyan]\n"
            f"[dim]{_TAGLINE}[/dim]\n"
            f"[dim]Workspace:[/dim] [cyan]{_truncate_cwd(Path.cwd())}[/cyan]"
        )

        grid.add_row(Text.from_markup(_ASCII_ART), Text.from_markup(info_text))

        console.print()
        console.print(grid)
        console.print()
        _session_banner_displayed = True

    if subtitle:
        console.print("[dim cyan]│[/dim cyan]")
        console.print(
            f"[bold cyan]◆  {subtitle}[/bold cyan]  "
            f"[dim](Press Esc to exit anytime)[/dim]"
        )
        console.print("[dim cyan]│[/dim cyan]\n")



def display_banner() -> None:
    """
    Print the full landing banner shown when ``rouint`` is invoked without
    a sub-command.

    This is the header (:func:`display_header`) followed by a bordered
    table of every available CLI command and a short usage hint.
    """
    display_header()

    cmd_table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 2))
    cmd_table.add_column("Command", style="bold cyan")
    cmd_table.add_column("Description", style="white")

    for cmd, desc in _COMMANDS:
        cmd_table.add_row(cmd, desc)

    console.print(Panel(
        cmd_table,
        title="[bold yellow]Available Commands[/bold yellow]",
        title_align="left",
        border_style="yellow",
        expand=False,
        padding=(1, 2),
    ))
    console.print(
        "[dim]  Usage: [bold white]rouint <command>[/bold white]  "
        "(e.g., [bold cyan]rouint start-test[/bold cyan])[/dim]\n"
    )
