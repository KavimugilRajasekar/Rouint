"""
Rouint UI package.

Re-exports the public UI components so callers can do::

    from rouint.ui import display_banner, display_header, box_width
"""

from rouint.ui.components import (
    display_banner,
    display_header,
    box_width,
)

__all__ = [
    "display_banner",
    "display_header",
    "box_width",
]
