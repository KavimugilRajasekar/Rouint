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
    """Verify that 'rouint --help' runs successfully via Click's test runner."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Usage: " in result.output
    assert "add-base-url" in result.output
    assert "add-new-api" in result.output
    assert "start-test" in result.output


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
