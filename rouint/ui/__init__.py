"""
Rouint UI package.

Re-exports the public UI components and interactive launcher screens.
"""

from rouint.ui.components import (
    display_banner,
    display_header,
    box_width,
    is_in_launcher,
    set_in_launcher,
    reset_banner_state,
    clear_screen,
)
from rouint.ui.screens import (
    WorkspaceState,
    MenuItem,
    get_workspace_state,
    get_menu_items,
    format_menu_line,
    format_answered_tokens,
    build_questionary_choices,
    show_interactive_menu,
    interactive_launcher,
)
from rouint.ui.theme import (
    THEMES,
    DEFAULT_THEME,
    get_active_theme,
    get_active_theme_key,
    load_theme,
    save_theme,
    apply_theme,
    build_qs_style,
    render_preview,
)

__all__ = [
    # components
    "display_banner",
    "display_header",
    "box_width",
    "is_in_launcher",
    "set_in_launcher",
    "reset_banner_state",
    "clear_screen",
    # screens
    "WorkspaceState",
    "MenuItem",
    "get_workspace_state",
    "get_menu_items",
    "format_menu_line",
    "format_answered_tokens",
    "build_questionary_choices",
    "show_interactive_menu",
    "interactive_launcher",
    # theme
    "THEMES",
    "DEFAULT_THEME",
    "get_active_theme",
    "get_active_theme_key",
    "load_theme",
    "save_theme",
    "apply_theme",
    "build_qs_style",
    "render_preview",
]
