"""
Tests for CLI import, compatibility, and help command execution.
"""

import subprocess
import sys
import typing
from click.testing import CliRunner

from rouint.cli import cli, load_temp_token, extract_token_from_response
from rouint.ui.components import box_width, _truncate_cwd, display_header


def test_cli_import():
    """Verify that importing rouint.cli succeeds without TypeError."""
    import rouint.cli
    assert hasattr(rouint.cli, "cli")
    assert callable(rouint.cli.cli)


def test_cli_help_runner():
    """Verify that 'rouint --help' runs successfully and shows command reference."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    # The Rich help panel replaces Click's default 'Usage:' output.
    # Verify the key commands are present in the output.
    assert "add-base-url" in result.output
    assert "add-new-api" in result.output
    assert "start-test" in result.output
    assert "set-theme" in result.output


def test_cli_help_subprocess():
    """Verify that 'python -m rouint.cli --help' or module import works via subprocess."""
    res = subprocess.run(
        [sys.executable, "-c", "from rouint.cli import cli; import sys; sys.exit(0)"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Subprocess import failed with: {res.stderr}"


def test_type_annotations_compatibility():
    """
    Ensure type hints on key functions in rouint.cli and rouint.ui.components
    can be resolved via typing.get_type_hints without raising TypeError on Python 3.9+.
    """
    hints_load = typing.get_type_hints(load_temp_token)
    assert hints_load.get("return") == typing.Optional[str]

    hints_extract = typing.get_type_hints(extract_token_from_response)
    assert hints_extract.get("return") == typing.Optional[str]

    hints_box = typing.get_type_hints(box_width)
    assert "return" in hints_box

    hints_truncate = typing.get_type_hints(_truncate_cwd)
    assert "return" in hints_truncate

    hints_display = typing.get_type_hints(display_header)
    assert "return" in hints_display

    from rouint.ui.screens import format_menu_line, get_workspace_state, get_menu_items, show_interactive_menu
    hints_format = typing.get_type_hints(format_menu_line)
    assert hints_format.get("return") == str

    hints_state = typing.get_type_hints(get_workspace_state)
    assert "return" in hints_state

    hints_menu = typing.get_type_hints(get_menu_items)
    assert "return" in hints_menu

    hints_show = typing.get_type_hints(show_interactive_menu)
    assert hints_show.get("return") == typing.Optional[str]
