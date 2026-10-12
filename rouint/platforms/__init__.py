"""
Rouint platform-specific backends.

This package provides platform-specific HTTP execution backends.
The appropriate backend is selected at runtime based on the operating system.
"""

import platform
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def get_platform() -> str:
    """Return the current platform identifier: 'linux', 'windows', or 'unsupported'."""
    system = platform.system().lower()
    if system == "linux" or system == "darwin":
        return "linux"
    elif system == "windows":
        return "windows"
    return "unsupported"
