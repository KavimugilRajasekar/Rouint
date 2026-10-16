"""
Interactive launcher and state-aware TUI screens for Rouint.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import click
from prompt_toolkit.application import Application
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
import questionary
from questionary import Choice, Question, Separator
from questionary.prompts import common
from questionary.prompts.common import InquirerControl
from questionary.styles import merge_styles_default

from rouint.core.manager import EndpointManager
from rouint.ui.components import console, display_header, set_in_launcher, reset_banner_state, clear_screen
from rich.table import Table
from rouint.utils.config import (
    CONFIG_FILE,
    TEMP_TOKEN_FILE,
    get_data_path,
    get_env_path,
)

# ---------------------------------------------------------------------------
# Formatting constants
# ---------------------------------------------------------------------------

CMD_WIDTH = 16
DESC_WIDTH = 34
SEPARATOR_BAR = "─" * 16


def _build_launcher_style() -> questionary.Style:
    """Build a Questionary Style from the currently active theme."""
    try:
        from rouint.ui.theme import build_qs_style
        return build_qs_style()
    except Exception:
        return questionary.Style([
            ("qmark",          "fg:#00bfff bold"),
            ("question",       "bold"),
            ("answer",         "fg:#00bfff bold"),
            ("pointer",        "fg:#00bfff bold"),
            ("highlighted",    "fg:#00bfff bold"),
            ("selected",       "fg:#00bfff"),
            ("instruction",    "fg:#666666"),
            ("disabled",       ""),
            ("separator",      "fg:#555555"),
            ("ansibrightblack","fg:#767676"),
        ])


# LAUNCHER_STYLE is evaluated lazily via _build_launcher_style() at call-time
# so that theme changes made mid-session are always reflected.
LAUNCHER_STYLE = questionary.Style([
    ("qmark",          "fg:#00bfff bold"),
    ("question",       "bold"),
    ("answer",         "fg:#00bfff bold"),
    ("pointer",        "fg:#00bfff bold"),
    ("highlighted",    "fg:#00bfff bold"),
    ("selected",       "fg:#00bfff"),
    ("instruction",    "fg:#666666"),
    ("disabled",       ""),  # Retain standard styling for disabled entry prefix
    ("separator",      "fg:#555555"),
    ("ansibrightblack","fg:#767676"),  # Dark grey for parenthesized hint
])

# ---------------------------------------------------------------------------
# Workspace state detection
# ---------------------------------------------------------------------------

@dataclass
class WorkspaceState:
    is_initialized: bool
    has_base_urls: bool
    has_endpoints: bool
    has_token: bool


def get_workspace_state() -> WorkspaceState:
    """
    Robustly inspect the current workspace configuration without modifying
    or deleting any user files.

    Handles:
    - Missing, empty, or corrupted config.json
    - Configured base URLs in environments/*.json
    - Endpoints registered in registry.json
    - Temporary token in .temp_token
    """
    data_path = get_data_path()
    config_file = data_path / CONFIG_FILE

    # 1. Initialization check
    is_init = False
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    cfg = json.loads(content)
                    if isinstance(cfg, dict):
                        is_init = True
        except Exception:
            is_init = False

    # 2. Base URLs check
    has_base_urls = False
    if is_init:
        try:
            env_path = get_env_path()
            if env_path.exists():
                for env_file in env_path.glob("*.json"):
                    try:
                        with open(env_file, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            if not content:
                                continue
                            env_data = json.loads(content)
                            if isinstance(env_data, dict) and bool(env_data.get("base_url", "").strip()):
                                has_base_urls = True
                                break
                    except Exception:
                        continue
        except Exception:
            has_base_urls = False

    # 3. Endpoints check
    has_endpoints = False
    if is_init:
        try:
            endpoints = EndpointManager().list_endpoints()
            has_endpoints = len(endpoints) > 0
        except Exception:
            has_endpoints = False

    # 4. Token check
    has_token = False
    if is_init:
        try:
            token_path = data_path / TEMP_TOKEN_FILE
            if token_path.exists():
                token_val = token_path.read_text(encoding="utf-8").strip()
                has_token = bool(token_val)
        except Exception:
            has_token = False

    return WorkspaceState(
        is_initialized=is_init,
        has_base_urls=has_base_urls,
        has_endpoints=has_endpoints,
        has_token=has_token,
    )


# ---------------------------------------------------------------------------
# Menu Item Representation & Generation
# ---------------------------------------------------------------------------

@dataclass
class MenuItem:
    name: str
    description: str
    hint: Optional[str] = None
    enabled: bool = True
    is_exit: bool = False


def get_menu_items(state: Optional[WorkspaceState] = None) -> list[MenuItem]:
    """
    Return the list of state-aware menu items based on workspace configuration.
    """
    if state is None:
        state = get_workspace_state()

    items: list[MenuItem] = []

    # 1. init: Display only when the workspace has not been initialized.
    # Once initialization is complete, remove this option entirely.
    if not state.is_initialized:
        items.append(MenuItem(
            name="init",
            description="Initialize Rouint workspace",
            hint=None,
            enabled=True,
        ))

    # 2. add-base-url: Always available after initialization.
    # If no base URLs are configured, display grey hint (required — no URLs configured yet).
    # When uninitialized, disabled with (run 'init' first).
    if not state.is_initialized:
        items.append(MenuItem(
            name="add-base-url",
            description="Manage base URLs",
            hint="run 'init' first",
            enabled=False,
        ))
    elif not state.has_base_urls:
        items.append(MenuItem(
            name="add-base-url",
            description="Manage base URLs",
            hint="required — no URLs configured yet",
            enabled=True,
        ))
    else:
        items.append(MenuItem(
            name="add-base-url",
            description="Manage base URLs",
            hint=None,
            enabled=True,
        ))

    # 3. add-new-api: Available after initialization.
    # If no endpoints saved, display grey hint (required — no endpoints saved yet).
    # When uninitialized, disabled with (run 'init' first).
    if not state.is_initialized:
        items.append(MenuItem(
            name="add-new-api",
            description="Define a new endpoint",
            hint="run 'init' first",
            enabled=False,
        ))
    elif not state.has_endpoints:
        items.append(MenuItem(
            name="add-new-api",
            description="Define a new endpoint",
            hint="required — no endpoints saved yet",
            enabled=True,
        ))
    else:
        items.append(MenuItem(
            name="add-new-api",
            description="Define a new endpoint",
            hint=None,
            enabled=True,
        ))

    # 4. start-test: Display as disabled when prerequisites missing.
    # When enabled, hint mentions --no-metrics is available so the user
    # knows they can skip the metrics box without a separate menu row.
    if not state.has_base_urls and not state.has_endpoints:
        items.append(MenuItem(
            name="start-test",
            description="Run a test",
            hint="add a base URL & endpoint first",
            enabled=False,
        ))
    elif not state.has_base_urls:
        items.append(MenuItem(
            name="start-test",
            description="Run a test",
            hint="add a base URL first",
            enabled=False,
        ))
    elif not state.has_endpoints:
        items.append(MenuItem(
            name="start-test",
            description="Run a test",
            hint="add an endpoint first",
            enabled=False,
        ))
    else:
        items.append(MenuItem(
            name="start-test",
            description="Run a test",
            hint="--no-metrics available",
            enabled=True,
        ))

    # 5. list-api: Display as disabled when no saved endpoints. Enable when endpoints exist.
    if not state.has_endpoints:
        items.append(MenuItem(
            name="list-api",
            description="Manage saved endpoints",
            hint="no endpoints saved yet",
            enabled=False,
        ))
    else:
        items.append(MenuItem(
            name="list-api",
            description="Manage saved endpoints",
            hint="--show-wrapper available",
            enabled=True,
        ))

    # 6. clear-token: Enable only when a saved Bearer token is available.
    # Otherwise display as disabled with grey hint (no token saved).
    if not state.has_token:
        items.append(MenuItem(
            name="clear-token",
            description="Clear saved Bearer token",
            hint="no token saved",
            enabled=False,
        ))
    else:
        items.append(MenuItem(
            name="clear-token",
            description="Clear saved Bearer token",
            hint=None,
            enabled=True,
        ))

    # 7. set-theme: Always available — choose colour theme.
    try:
        from rouint.ui.theme import get_active_theme_key, THEMES
        active_key = get_active_theme_key()
        active_name = THEMES[active_key]["display_name"]
        items.append(MenuItem(
            name="set-theme",
            description="Choose a colour theme",
            hint=f"active: {active_name}",
            enabled=True,
        ))
    except Exception:
        items.append(MenuItem(
            name="set-theme",
            description="Choose a colour theme",
            hint=None,
            enabled=True,
        ))

    # 8. Exit: Always available to close the interactive menu cleanly.
    items.append(MenuItem(
        name="— Exit —",
        description="",
        hint=None,
        enabled=True,
        is_exit=True,
    ))

    return items



# ---------------------------------------------------------------------------
# Strict Terminal Alignment & Formatting
# ---------------------------------------------------------------------------

def format_menu_line(
    name: str,
    desc: str,
    hint: Optional[str] = None,
    is_exit: bool = False,
    use_ansi: bool = True,
) -> str:
    """
    Format a single menu item with strict column alignment.

    Layout:
    - Command name: padded to CMD_WIDTH (16) characters.
    - Em dash separator: '—  ' (3 characters) starting at index 16.
    - Description: padded to DESC_WIDTH (34) characters, starting at index 19.
      Long descriptions (>34) are truncated with '...' so they never shift
      subsequent columns.
    - Parenthesized hint: begins at index 53.
      Only the hint and parentheses are styled in dark grey (\033[90m...\033[0m).
    """
    if is_exit:
        return name

    cmd_col = f"{name:<{CMD_WIDTH}}"
    sep = "—  "

    # Handle long descriptions gracefully
    if len(desc) > DESC_WIDTH:
        trimmed_desc = desc[:DESC_WIDTH - 3] + "..."
    else:
        trimmed_desc = desc
    desc_col = f"{trimmed_desc:<{DESC_WIDTH}}"

    if hint:
        if use_ansi:
            return f"{cmd_col}{sep}{desc_col}\033[90m({hint})\033[0m"
        return f"{cmd_col}{sep}{desc_col}({hint})"

    return f"{cmd_col}{sep}{desc_col}".rstrip()


# ---------------------------------------------------------------------------
# Aligned Questionary InquirerControl
# ---------------------------------------------------------------------------

from rouint.ui.controls import AlignedInquirerControl


def build_questionary_choices(menu_items: list[MenuItem]) -> list[Union[Choice, Separator]]:
    """Convert MenuItems to questionary Choice and Separator instances.

    Each non-exit choice title is a structured FormattedText where the first
    token is the command name (highlighted on hover) and the remaining tokens
    are the description + hint (never highlighted, grey hint preserved).
    """
    from prompt_toolkit.formatted_text import FormattedText as FT
    choices: list[Union[Choice, Separator]] = []
    for item in menu_items:
        if item.is_exit:
            choices.append(Choice(
                title=item.name,
                value="exit",
            ))
        else:
            cmd_col = f"{item.name:<{CMD_WIDTH}}"
            sep = "—  "

            desc = item.description
            if len(desc) > DESC_WIDTH:
                desc = desc[:DESC_WIDTH - 3] + "..."
            desc_col = f"{desc:<{DESC_WIDTH}}"

            # Two-part title: [name_token, ...rest_tokens]
            # Only name_token gets class:highlighted on hover; rest keeps its style.
            if item.hint:
                tokens = FT([
                    ("", cmd_col),
                    ("", sep + desc_col),
                    ("fg:#666666", f"({item.hint})"),
                ])
            else:
                tokens = FT([
                    ("", cmd_col),
                    ("", (sep + desc_col).rstrip()),
                ])

            choices.append(Choice(
                title=tokens,
                value=item.name,
                disabled=not item.enabled,
            ))
    return choices


def format_answered_tokens(
    item: Optional[MenuItem],
    raw_title: str = "",
) -> list[tuple[str, str]]:
    """
    Format prompt tokens for the answered state:
    Highlights command name in cyan bold ('class:answer'),
    and styles description/hint in dark grey ('class:ansibrightblack')
    with excessive column-padding whitespace stripped out.
    """
    if item:
        if item.is_exit or not item.description:
            return [
                ("class:qmark", "?"),
                ("class:question", " What would you like to do? "),
                ("class:answer", item.name),
            ]
        hint_str = f" ({item.hint})" if item.hint else ""
        desc_str = f" — {item.description}{hint_str}"
        return [
            ("class:qmark", "?"),
            ("class:question", " What would you like to do? "),
            ("class:answer", item.name),
            ("class:ansibrightblack", desc_str),
        ]

    if "—" in raw_title:
        parts = raw_title.split("—", 1)
        cmd_part = parts[0].strip()
        rest_part = " — " + " ".join(parts[1].split())
        return [
            ("class:qmark", "?"),
            ("class:question", " What would you like to do? "),
            ("class:answer", cmd_part),
            ("class:ansibrightblack", rest_part),
        ]

    return [
        ("class:qmark", "?"),
        ("class:question", " What would you like to do? "),
        ("class:answer", raw_title.strip()),
    ]


def prompt_launcher_menu(
    choices: list[Union[Choice, Separator]],
    menu_items: Optional[list[MenuItem]] = None,
    pointer: str = "❯",
    style: Optional[questionary.Style] = None,
    **kwargs: Any,
) -> Question:
    """
    Construct a Question prompt with AlignedInquirerControl and graceful Escape/Ctrl+C handling.
    Shows a '? What would you like to do? (Use arrow keys)' question line.
    When answered, highlights the command name in cyan and styles the description/hint in dark grey,
    with excessive column-padding whitespace stripped out.
    """
    merged_style = merge_styles_default([style or _build_launcher_style()])

    item_map = {item.name: item for item in menu_items} if menu_items else {}

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
        if ic.is_answered:
            pointed = ic.get_pointed_at()
            val = getattr(pointed, "value", None)
            item = item_map.get(val) if item_map else None
            raw_title = pointed.title if isinstance(pointed.title, str) else "".join(t[1] for t in pointed.title)
            return format_answered_tokens(item, raw_title)

        return [
            ("class:qmark", "?"),
            ("class:question", " What would you like to do? "),
        ]

    layout = common.create_inquirer_layout(ic, get_prompt_tokens, **kwargs)

    bindings = KeyBindings()

    @bindings.add(Keys.ControlQ, eager=True)
    @bindings.add(Keys.ControlC, eager=True)
    def _(event):
        event.app.exit(result=None)

    @bindings.add(Keys.Escape, eager=True)
    def _(event):
        event.app.exit(result=None)

    def move_cursor_down(event):
        ic.select_next()
        while not ic.is_selection_valid():
            ic.select_next()

    def move_cursor_up(event):
        ic.select_previous()
        while not ic.is_selection_valid():
            ic.select_previous()

    bindings.add(Keys.Down, eager=True)(move_cursor_down)
    bindings.add(Keys.Up, eager=True)(move_cursor_up)
    bindings.add("j", eager=True)(move_cursor_down)
    bindings.add("k", eager=True)(move_cursor_up)

    @bindings.add(Keys.ControlM, eager=True)
    def set_answer(event):
        ic.is_answered = True
        event.app.exit(result=ic.get_pointed_at().value)

    @bindings.add(Keys.Any)
    def other(event):
        pass

    return Question(
        Application(
            layout=layout,
            key_bindings=bindings,
            style=merged_style,
            **questionary.utils.used_kwargs(kwargs, Application.__init__),
        )
    )


def _print_cancelled() -> None:
    """Print a right-aligned timestamped 'Cancelled by user' message in dimmed styling."""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row("[dim]Cancelled by user[/dim]", f"[dim]{ts}[/dim]")
    console.print(grid)


def show_interactive_menu(state: Optional[WorkspaceState] = None) -> Optional[str]:
    """
    Display the interactive launcher menu and return the selected command value.
    Returns None or 'exit' if cancelled / exited.
    """
    items = get_menu_items(state)
    choices = build_questionary_choices(items)

    try:
        q = prompt_launcher_menu(choices, menu_items=items)
        result = q.ask()
        return result
    except Exception:
        return None


def _show_help_inline(ctx: click.Context) -> None:
    """Print a Rich-formatted command reference panel instead of Click's raw --help."""
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    try:
        from rouint.ui.theme import get_active_theme
        styles = get_active_theme()
        border = styles.get("border_style", "bright_black")
    except Exception:
        border = "bright_black"

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(style="dim")
    table.add_column()

    commands = [
        ("init",         "",                  "Initialize Rouint workspace in the current directory"),
        ("add-base-url", "",                  "Add or delete a named base URL (local, staging, production…)"),
        ("add-new-api",  "",                  "Define a new API endpoint interactively"),
        ("start-test",   "[--no-metrics]",    "Run a test against a saved endpoint"),
        ("list-api",     "[--show-wrapper]",  "List, inspect, edit, or delete saved endpoints"),
        ("clear-token",  "",                  "Clear the saved temporary Bearer token"),
        ("set-theme",    "",                  "Choose a colour theme for the CLI interface"),
    ]

    for cmd, flag, desc in commands:
        flag_text = Text(flag, style="yellow") if flag else Text("")
        table.add_row(cmd, flag_text, desc)

    # Separator + --version flag entry
    table.add_row(Text(""), Text(""), Text(""))
    table.add_row(
        Text("--version", style="bold cyan"),
        Text(""),
        Text("Print the current Rouint version and exit"),
    )

    console.print()
    console.print(Panel(
        table,
        title="[bold]Rouint — Command Reference[/bold]",
        subtitle="[dim]rouint <command> --help  for per-command options[/dim]",
        border_style=border,
        padding=(1, 2),
        title_align="center",
        subtitle_align="center",
    ))
    console.print()


def interactive_launcher(ctx: click.Context) -> None:
    """
    Entry point for typing 'rouint' without subcommands.
    Renders header once per session, displays interactive menu in a loop,
    and keeps the user inside the launcher after subcommands complete until they exit.
    """
    set_in_launcher(True)

    # ── Enter Alternate Screen Buffer ─────────────────────────────────────────
    # This switches the terminal to a separate buffer, preserving the user's
    # shell history and preventing menu artifacts from flooding the scrollback.
    import sys
    sys.stdout.write("\033[?1049h")
    sys.stdout.flush()

    try:
        # Initial screen setup
        clear_screen()
        display_header(force_banner=True)

        _loop_guard = 0
        while True:
            _loop_guard += 1
            if _loop_guard > 100:  # Safety guard for automated tests
                break

            # Clear screen and re-print header before every menu render.
            # Since we are in the alternate screen, this only affects the current viewport.
            clear_screen()
            display_header(force_banner=True)

            state = get_workspace_state()
            items = get_menu_items(state)
            enabled_map = {item.name: item.enabled for item in items}

            selected = show_interactive_menu(state)

            if not selected or selected == "exit":
                # User pressed Esc, Ctrl+C, or chose Exit — print tidy cancellation line
                _print_cancelled()
                break

            # Guard: only execute if actually enabled (safety net, disabled items aren't selectable)
            if not enabled_map.get(selected, False):
                break

            # ── start-test: offer --no-metrics mode selection ────────────────
            if selected == "start-test":
                mode = questionary.select(
                    "Select test mode:",
                    choices=[
                        Choice("Standard test  (with metrics)", value=False),
                        Choice("Skip metrics   (--no-metrics)", value=True),
                    ],
                    style=_build_launcher_style(),
                    pointer="❯",
                    instruction="",
                ).ask()
                if mode is None:
                    continue
                cmd = ctx.command.get_command(ctx, "start-test")
                if cmd is not None:
                    ctx.invoke(cmd, no_metrics=mode)
                continue

            # ── list-api: offer --show-wrapper mode selection ─────────────────
            if selected == "list-api":
                mode = questionary.select(
                    "Select list mode:",
                    choices=[
                        Choice("Manage endpoints     (standard)",       value=False),
                        Choice("View wrapper command (--show-wrapper)",  value=True),
                    ],
                    style=_build_launcher_style(),
                    pointer="❯",
                    instruction="",
                ).ask()
                if mode is None:
                    continue
                cmd = ctx.command.get_command(ctx, "list-api")
                if cmd is not None:
                    ctx.invoke(cmd, show_wrapper=mode)
                continue

            # ── set-theme: invoke directly ────────────────────────────────────
            if selected == "set-theme":
                cmd = ctx.command.get_command(ctx, "set-theme")
                if cmd is not None:
                    ctx.invoke(cmd)
                # Reset banner so it re-renders in the new theme colour next iteration
                reset_banner_state()
                continue

            cmd = ctx.command.get_command(ctx, selected)
            if cmd is not None:
                ctx.invoke(cmd)
    finally:
        # ── Exit Alternate Screen Buffer ──────────────────────────────────────
        # Switch back to the main buffer so the user returns to their original shell state.
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()
        set_in_launcher(False)

        # Print a polished goodbye message to the original shell buffer.
        from rouint.ui.theme import get_active_theme
        styles = get_active_theme()
        accent = styles.get("accent_rich", "cyan")

        from rich.console import Console
        exit_console = Console()
        exit_console.print(f"\n{ ' ' * 4} [bold {accent}]Thank you for using Rouint![/bold {accent}]")
        exit_console.print(f"{ ' ' * 4} [dim]API management made simple in your terminal.[/dim]\n")