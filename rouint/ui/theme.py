"""
Theme engine for Rouint's CLI.

Five named themes, each tuned to a different aesthetic. Themes control:
- ASCII banner colour
- Rich panel border colour
- Primary accent (used for highlights, selected text, pointer, qmark)
- Dim / muted colour (hints, timestamps, separators)
- Questionary prompt style overrides

Themes are persisted to ``.rouint-data/theme`` (a plain text file containing
the theme key).  On every launch the active theme is loaded and applied
globally so that every component — launcher, panels, banners — renders in the
chosen palette.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import questionary

# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------

THEMES: Dict[str, dict] = {
    "neon": {
        "display_name":  "Neon Pulse",
        "description":   "Electric cyan-green on deep black — classic hacker terminal",
        "accent":        "#00bfff",          # electric cyan
        "accent_rich":   "cyan",
        "dim":           "#444444",
        "banner_style":  "bold cyan",
        "border_style":  "cyan",
        "panel_title":   "bold cyan",
        # Three-line gradient: cyan → teal → green for that neon-cyberpunk vibe
        "ascii_colours": ["#00d4ff", "#00bfaa", "#00ff88"],
        "qs_style": [
            ("qmark",        "fg:#00bfff bold"),
            ("question",     "bold"),
            ("answer",       "fg:#00bfff bold"),
            ("pointer",      "fg:#00bfff bold"),
            ("highlighted",  "fg:#00bfff bold"),
            ("selected",     "fg:#00bfff"),
            ("instruction",  "fg:#555555"),
            ("disabled",     ""),
            ("separator",    "fg:#444444"),
            ("ansibrightblack", "fg:#767676"),
        ],
    },

    "aurora": {
        "display_name":  "Aurora",
        "description":   "Soft violet-green gradient — calm and focused",
        "accent":        "#a78bfa",          # muted violet
        "accent_rich":   "bright_magenta",
        "dim":           "#4a4a6a",
        "banner_style":  "bold bright_magenta",
        "border_style":  "bright_magenta",
        "panel_title":   "bold bright_magenta",
        "ascii_colours": ["#c4b5fd", "#a78bfa", "#8b5cf6"],
        "qs_style": [
            ("qmark",        "fg:#a78bfa bold"),
            ("question",     "bold"),
            ("answer",       "fg:#a78bfa bold"),
            ("pointer",      "fg:#a78bfa bold"),
            ("highlighted",  "fg:#a78bfa bold"),
            ("selected",     "fg:#a78bfa"),
            ("instruction",  "fg:#4a4a6a"),
            ("disabled",     ""),
            ("separator",    "fg:#4a4a6a"),
            ("ansibrightblack", "fg:#767676"),
        ],
    },

    "ash": {
        "display_name":  "Ash",
        "description":   "White-grey-black minimalism — no distractions",
        "accent":        "#d4d4d4",          # near-white
        "accent_rich":   "white",
        "dim":           "#555555",
        "banner_style":  "bold white",
        "border_style":  "bright_black",
        "panel_title":   "bold white",
        "ascii_colours": ["#ffffff", "#d4d4d4", "#a8a8a8"],
        "qs_style": [
            ("qmark",        "fg:#d4d4d4 bold"),
            ("question",     "bold"),
            ("answer",       "fg:#d4d4d4 bold"),
            ("pointer",      "fg:#d4d4d4 bold"),
            ("highlighted",  "fg:#ffffff bold"),
            ("selected",     "fg:#d4d4d4"),
            ("instruction",  "fg:#555555"),
            ("disabled",     ""),
            ("separator",    "fg:#444444"),
            ("ansibrightblack", "fg:#767676"),
        ],
    },

    "ember": {
        "display_name":  "Ember",
        "description":   "Warm amber-orange glow — productive, warm energy",
        "accent":        "#fb923c",          # warm amber-orange
        "accent_rich":   "yellow",
        "dim":           "#4a3a2a",
        "banner_style":  "bold yellow",
        "border_style":  "yellow",
        "panel_title":   "bold yellow",
        "ascii_colours": ["#fbbf24", "#fb923c", "#f97316"],
        "qs_style": [
            ("qmark",        "fg:#fb923c bold"),
            ("question",     "bold"),
            ("answer",       "fg:#fb923c bold"),
            ("pointer",      "fg:#fb923c bold"),
            ("highlighted",  "fg:#fb923c bold"),
            ("selected",     "fg:#fb923c"),
            ("instruction",  "fg:#4a3a2a"),
            ("disabled",     ""),
            ("separator",    "fg:#4a3a2a"),
            ("ansibrightblack", "fg:#767676"),
        ],
    },

    "frost": {
        "display_name":  "Frost",
        "description":   "Icy steel-blue precision — clean and sharp",
        "accent":        "#67e8f9",          # ice blue
        "accent_rich":   "bright_cyan",
        "dim":           "#2a4a5a",
        "banner_style":  "bold bright_cyan",
        "border_style":  "bright_cyan",
        "panel_title":   "bold bright_cyan",
        "ascii_colours": ["#a5f3fc", "#67e8f9", "#22d3ee"],
        "qs_style": [
            ("qmark",        "fg:#67e8f9 bold"),
            ("question",     "bold"),
            ("answer",       "fg:#67e8f9 bold"),
            ("pointer",      "fg:#67e8f9 bold"),
            ("highlighted",  "fg:#67e8f9 bold"),
            ("selected",     "fg:#67e8f9"),
            ("instruction",  "fg:#2a4a5a"),
            ("disabled",     ""),
            ("separator",    "fg:#2a4a5a"),
            ("ansibrightblack", "fg:#767676"),
        ],
    },
}

# The default theme key used when no theme file exists.
DEFAULT_THEME = "neon"

# ---------------------------------------------------------------------------
# Runtime active theme (module-level singleton)
# ---------------------------------------------------------------------------

_active_theme_key: str = DEFAULT_THEME


def get_active_theme() -> dict:
    """Return the currently active theme dictionary."""
    return THEMES.get(_active_theme_key, THEMES[DEFAULT_THEME])


def get_active_theme_key() -> str:
    """Return the key of the currently active theme (e.g. 'ember')."""
    return _active_theme_key


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _theme_file_path() -> Optional[Path]:
    """
    Return the path to the theme persistence file, or None if the workspace
    hasn't been initialised yet.  We import lazily to avoid circular imports.
    """
    try:
        from rouint.utils.config import get_data_path, is_initialized
        if is_initialized():
            return get_data_path() / "theme"
    except Exception:
        pass
    return None


def load_theme() -> str:
    """
    Load the saved theme key from disk.  Falls back to DEFAULT_THEME if the
    file doesn't exist or contains an unrecognised key.
    """
    global _active_theme_key
    path = _theme_file_path()
    if path and path.exists():
        try:
            key = path.read_text(encoding="utf-8").strip()
            if key in THEMES:
                _active_theme_key = key
                return key
        except Exception:
            pass
    _active_theme_key = DEFAULT_THEME
    return DEFAULT_THEME


def save_theme(key: str) -> None:
    """Persist *key* to the theme file so it survives across sessions."""
    if key not in THEMES:
        raise ValueError(f"Unknown theme '{key}'. Valid: {list(THEMES)}")
    global _active_theme_key
    _active_theme_key = key
    path = _theme_file_path()
    if path:
        try:
            path.write_text(key, encoding="utf-8")
        except Exception:
            pass  # Non-fatal — theme reverts to default next launch


def apply_theme(key: str) -> None:
    """
    Set *key* as the active theme in-process (no disk write).
    Use :func:`save_theme` to also persist it.
    """
    global _active_theme_key
    if key in THEMES:
        _active_theme_key = key


# ---------------------------------------------------------------------------
# Questionary style builder
# ---------------------------------------------------------------------------

def build_qs_style(key: Optional[str] = None) -> questionary.Style:
    """Return a Questionary ``Style`` for *key* (defaults to active theme)."""
    theme = THEMES.get(key or _active_theme_key, THEMES[DEFAULT_THEME])
    return questionary.Style(theme["qs_style"])


# ---------------------------------------------------------------------------
# Preview renderer
# ---------------------------------------------------------------------------

def render_preview(key: str) -> None:
    """
    Print a compact live preview of theme *key* to the terminal using Rich.

    Shows:
    - A coloured sample panel with title and body text
    - A miniature command row in the theme's accent colour
    - A dim hint line in the theme's dim colour
    """
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text

    console = Console(legacy_windows=False)
    theme = THEMES.get(key, THEMES[DEFAULT_THEME])

    accent     = theme["accent_rich"]
    border     = theme["border_style"]
    title_sty  = theme["panel_title"]
    banner_sty = theme["banner_style"]

    # Mini ASCII snippet in theme colour
    ascii_sample = Text("█▀▀█ █▀▀█ █  █ ▀█▀  ", style=banner_sty)

    # Command row sample
    cmd_row = Text.assemble(
        Text("start-test ", style=f"bold {accent}"),
        Text("— Run a test ", style="white"),
        Text("(--no-metrics available)", style="dim"),
    )

    # Metric row sample
    metric_row = Text.assemble(
        Text("200 OK ", style=f"bold {accent}"),
        Text("· 142 ms · 1.2 KB", style="dim"),
    )

    body = Text.assemble(ascii_sample, "\n", cmd_row, "\n", metric_row)

    console.print(Panel(
        body,
        title=f"[{title_sty}]{theme['display_name']}[/{title_sty}]",
        subtitle=f"[dim]{theme['description']}[/dim]",
        border_style=border,
        padding=(0, 2),
        expand=False,
    ))
