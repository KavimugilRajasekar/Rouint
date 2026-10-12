"""
Comprehensive tests for the Rouint state-aware interactive CLI launcher.

Covers:
1. Fresh workspace: 'init' is visible; dependent commands show correct disabled states.
2. Initialized workspace: 'init' is hidden.
3. Missing base URLs: the correct hint appears, and testing remains disabled.
4. Missing endpoints: endpoint-dependent commands remain disabled.
5. Fully configured workspace: 'start-test' and 'list-api' become selectable.
6. Missing token: 'clear-token' is disabled with the correct grey hint.
7. Available token: 'clear-token' becomes selectable.
8. Column alignment remains consistent across every menu state.
9. Grey styling affects only the parenthesized hint.
10. Command selection invokes the correct existing handler.
11. Direct command invocations continue to work.
12. Menu cancellation and exit are handled gracefully.
13. Robust state detection across corrupt/empty/missing configs without modification.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from questionary import Choice, Separator

from rouint.cli import cli, save_temp_token
from rouint.ui.screens import (
    AlignedInquirerControl,
    MenuItem,
    WorkspaceState,
    build_questionary_choices,
    format_menu_line,
    get_menu_items,
    get_workspace_state,
    interactive_launcher,
    show_interactive_menu,
)
from rouint.utils.config import (
    CONFIG_FILE,
    DATA_DIR,
    ENDPOINTS_DIR,
    ENV_DIR,
    REGISTRY_FILE,
    TEMP_TOKEN_FILE,
    init_workspace,
    save_environment,
)
from rouint.core.manager import EndpointManager


@pytest.fixture
def clean_workspace(tmp_path, monkeypatch):
    """Switch current working directory to a clean temporary directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Fresh workspace
# ---------------------------------------------------------------------------

def test_fresh_workspace_state_and_menu(clean_workspace):
    """1. Fresh workspace: 'init' is visible; dependent commands show correct disabled states."""
    state = get_workspace_state()
    assert not state.is_initialized
    assert not state.has_base_urls
    assert not state.has_endpoints
    assert not state.has_token

    items = get_menu_items(state)
    names = [i.name for i in items]
    item_map = {i.name: i for i in items}

    # init must be visible and selectable
    assert "init" in names
    assert item_map["init"].enabled is True
    assert item_map["init"].hint is None

    # Dependent commands must be disabled with correct hints
    assert item_map["add-base-url"].enabled is False
    assert item_map["add-base-url"].hint == "run 'init' first"

    assert item_map["add-new-api"].enabled is False
    assert item_map["add-new-api"].hint == "run 'init' first"

    assert item_map["start-test"].enabled is False
    assert item_map["start-test"].hint == "add a base URL & endpoint first"

    assert item_map["list-api"].enabled is False
    assert item_map["list-api"].hint == "no endpoints saved yet"

    assert item_map["clear-token"].enabled is False
    assert item_map["clear-token"].hint == "no token saved"

    assert item_map["Exit"].enabled is True


# ---------------------------------------------------------------------------
# 2. Initialized workspace
# ---------------------------------------------------------------------------

def test_initialized_workspace_init_hidden(clean_workspace):
    """2. Initialized workspace: 'init' is hidden."""
    init_workspace()
    # Remove default environment to test clean initialized state
    env_dir = clean_workspace / DATA_DIR / ENV_DIR
    for f in env_dir.glob("*.json"):
        f.unlink()

    state = get_workspace_state()
    assert state.is_initialized

    items = get_menu_items(state)
    names = [i.name for i in items]
    assert "init" not in names


# ---------------------------------------------------------------------------
# 3. Missing base URLs
# ---------------------------------------------------------------------------

def test_missing_base_urls_hint_and_testing_disabled(clean_workspace):
    """3. Missing base URLs: the correct hint appears, and testing remains disabled."""
    init_workspace()
    # Ensure no environments exist
    env_dir = clean_workspace / DATA_DIR / ENV_DIR
    for f in env_dir.glob("*.json"):
        f.unlink()

    # Add an endpoint
    mgr = EndpointManager()
    mgr.save_endpoint("Get Users", "GET", "/users", None, {}, {"type": "none"}, None)

    state = get_workspace_state()
    assert state.is_initialized
    assert not state.has_base_urls
    assert state.has_endpoints

    item_map = {i.name: i for i in get_menu_items(state)}

    # add-base-url is enabled and shows required hint
    assert item_map["add-base-url"].enabled is True
    assert item_map["add-base-url"].hint == "required — no URLs configured yet"

    # start-test remains disabled with base URL missing hint
    assert item_map["start-test"].enabled is False
    assert item_map["start-test"].hint == "add a base URL first"

    # list-api is enabled because endpoints exist
    assert item_map["list-api"].enabled is True
    assert item_map["list-api"].hint is None


# ---------------------------------------------------------------------------
# 4. Missing endpoints
# ---------------------------------------------------------------------------

def test_missing_endpoints_disables_testing_and_list_api(clean_workspace):
    """4. Missing endpoints: endpoint-dependent commands remain disabled."""
    init_workspace()
    save_environment("production", "https://api.example.com")

    state = get_workspace_state()
    assert state.is_initialized
    assert state.has_base_urls
    assert not state.has_endpoints

    item_map = {i.name: i for i in get_menu_items(state)}

    # add-base-url is available without hint
    assert item_map["add-base-url"].enabled is True
    assert item_map["add-base-url"].hint is None

    # add-new-api shows required hint
    assert item_map["add-new-api"].enabled is True
    assert item_map["add-new-api"].hint == "required — no endpoints saved yet"

    # start-test is disabled with endpoint missing hint
    assert item_map["start-test"].enabled is False
    assert item_map["start-test"].hint == "add an endpoint first"

    # list-api is disabled with no endpoints saved yet hint
    assert item_map["list-api"].enabled is False
    assert item_map["list-api"].hint == "no endpoints saved yet"


# ---------------------------------------------------------------------------
# 5. Fully configured workspace
# ---------------------------------------------------------------------------

def test_fully_configured_workspace_selectable(clean_workspace):
    """5. Fully configured workspace: 'start-test' and 'list-api' become selectable."""
    init_workspace()
    save_environment("local", "http://localhost:8000")

    mgr = EndpointManager()
    mgr.save_endpoint("Create User", "POST", "/users", None, {}, {"type": "none"}, '{"name": "Alice"}')

    state = get_workspace_state()
    assert state.is_initialized
    assert state.has_base_urls
    assert state.has_endpoints

    item_map = {i.name: i for i in get_menu_items(state)}

    assert item_map["add-base-url"].enabled is True
    assert item_map["add-base-url"].hint is None

    assert item_map["add-new-api"].enabled is True
    assert item_map["add-new-api"].hint is None

    assert item_map["start-test"].enabled is True
    assert item_map["start-test"].hint == "--no-metrics available"

    assert item_map["list-api"].enabled is True
    assert item_map["list-api"].hint is None


# ---------------------------------------------------------------------------
# 6 & 7. Bearer token states
# ---------------------------------------------------------------------------

def test_missing_token_disabled_with_hint(clean_workspace):
    """6. Missing token: 'clear-token' is disabled with the correct grey hint."""
    init_workspace()
    state = get_workspace_state()
    assert not state.has_token

    item_map = {i.name: i for i in get_menu_items(state)}
    assert item_map["clear-token"].enabled is False
    assert item_map["clear-token"].hint == "no token saved"


def test_available_token_becomes_selectable(clean_workspace):
    """7. Available token: 'clear-token' becomes selectable without hint."""
    init_workspace()
    save_temp_token("eyJh.eyJzdWIiOiIxMjMifQ.xyz")

    state = get_workspace_state()
    assert state.has_token

    item_map = {i.name: i for i in get_menu_items(state)}
    assert item_map["clear-token"].enabled is True
    assert item_map["clear-token"].hint is None


# ---------------------------------------------------------------------------
# 8. Column alignment across every menu state
# ---------------------------------------------------------------------------

def test_column_alignment_consistent_across_all_states(clean_workspace):
    """8. Column alignment remains consistent across every menu state."""
    # Test combinations of states
    states = [
        WorkspaceState(is_initialized=False, has_base_urls=False, has_endpoints=False, has_token=False),
        WorkspaceState(is_initialized=True, has_base_urls=False, has_endpoints=False, has_token=False),
        WorkspaceState(is_initialized=True, has_base_urls=True, has_endpoints=False, has_token=False),
        WorkspaceState(is_initialized=True, has_base_urls=False, has_endpoints=True, has_token=False),
        WorkspaceState(is_initialized=True, has_base_urls=True, has_endpoints=True, has_token=False),
        WorkspaceState(is_initialized=True, has_base_urls=True, has_endpoints=True, has_token=True),
    ]

    for st in states:
        items = get_menu_items(st)
        for item in items:
            if item.is_exit:
                assert item.name == "Exit"
                continue
            line = format_menu_line(item.name, item.description, item.hint, is_exit=False, use_ansi=False)
            # Em dash position must be exactly index CMD_WIDTH (16)
            assert line.find("—") == 16, f"Em dash misplaced in: {line!r}"
            # If hint is present, the hint's opening paren is always the LAST '(' in the line
            if item.hint:
                assert line.rfind("(") == 53, f"Opening paren misplaced in: {line!r}"


def test_long_description_handling():
    """Ensure long descriptions do not push the parenthesis column."""
    long_desc = "A" * 60
    line = format_menu_line("custom-cmd", long_desc, "some hint", is_exit=False, use_ansi=False)
    assert line.find("—") == 16
    assert line.rfind("(") == 53
    assert "..." in line


def test_questionary_choices_alignment():
    """Verify that InquirerControl renders all items with identical dash and paren columns."""
    items = [
        MenuItem("add-base-url", "Add base URLs", "required — no URLs configured yet", True),
        MenuItem("add-new-api", "Define a new endpoint", "required — no endpoints saved yet", True),
        MenuItem("start-test", "Run a test", "add a base URL & endpoint first", False),
        MenuItem("list-api", "Manage saved endpoints", "no endpoints saved yet", False),
        MenuItem("clear-token", "Clear saved Bearer token", "no token saved", False),
        MenuItem("Exit", "", None, True, is_exit=True),
    ]
    choices = build_questionary_choices(items)
    ic = AlignedInquirerControl(choices, pointer="❯", use_indicator=False)
    tokens = ic._get_choice_tokens()

    # Reconstruct text lines
    lines = []
    curr = []
    for t in tokens:
        if t[0] == "[SetCursorPosition]":
            continue
        if t[1] == "\n":
            lines.append("".join(txt for _, txt in curr))
            curr = []
        else:
            curr.append(t)
    if curr:
        lines.append("".join(txt for _, txt in curr))

    # Rendered indent is " ❯ " = 3 chars, so:
    # dash at 3 + CMD_WIDTH(16) = 19, paren (rfind) at 19 + 3 + DESC_WIDTH(34) = 56
    for line in lines[:5]:
        assert line.find("—") == 19, f"Mismatched dash in rendered line: {line!r}"
        assert line.rfind("(") == 56, f"Mismatched paren in rendered line: {line!r}"

    # Verify no separator bar line exists before Exit
    assert not any("─" in line for line in lines)
    assert "Exit" in lines[5]


# ---------------------------------------------------------------------------
# 9. Grey styling affects only parenthesized hint
# ---------------------------------------------------------------------------

def test_grey_styling_affects_only_parenthesized_hint():
    """9. Grey styling affects only the parenthesized hint and resets cleanly."""
    line = format_menu_line("add-base-url", "Add base URLs", "required — no URLs configured yet", use_ansi=True)
    tokens = to_formatted_text(ANSI(line))

    # Reconstruct styled parts
    normal_text = "".join(txt for style, txt in tokens if style == "")
    grey_text = "".join(txt for style, txt in tokens if style == "ansibrightblack")

    assert normal_text.startswith("add-base-url")
    assert "—  Add base URLs" in normal_text
    assert grey_text == "(required — no URLs configured yet)"
    # Ensure ANSI reset is right after closing paren
    assert line.endswith("\033[0m")
    assert not normal_text.endswith("(")


# ---------------------------------------------------------------------------
# 10. Command selection invokes the correct handler
# ---------------------------------------------------------------------------

def test_command_selection_invokes_handler(clean_workspace):
    """10. Command selection invokes the correct existing handler."""
    runner = CliRunner()
    with patch("rouint.ui.screens.show_interactive_menu", return_value="init"):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "Workspace Initialization" in result.output


def test_disabled_command_not_executed(clean_workspace):
    """Guard: even if a disabled command were returned, it must not execute."""
    runner = CliRunner()
    # Workspace is uninitialized, start-test is disabled
    with patch("rouint.ui.screens.show_interactive_menu", return_value="start-test"):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        # API Endpoint Test Runner must NOT have executed
        assert "API Endpoint Test Runner" not in result.output


# ---------------------------------------------------------------------------
# 11. Direct command invocations continue to work
# ---------------------------------------------------------------------------

def test_direct_command_invocations(clean_workspace):
    """11. Direct command invocations continue to work without showing the menu."""
    runner = CliRunner()
    with patch("rouint.ui.screens.show_interactive_menu") as mock_menu:
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert "Workspace Initialization" in result.output
        mock_menu.assert_not_called()


# ---------------------------------------------------------------------------
# 12. Menu cancellation and exit are handled gracefully
# ---------------------------------------------------------------------------

def test_menu_exit_option_handled_gracefully(clean_workspace):
    """12. Selecting 'Exit' prints Cancelled by user with timestamp and terminates cleanly."""
    runner = CliRunner()
    with patch("rouint.ui.screens.show_interactive_menu", return_value="exit"):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert result.exception is None
        assert "Cancelled by user" in result.output


def test_menu_cancel_none_handled_gracefully(clean_workspace):
    """12. Cancelling via Esc or Ctrl+C prints Cancelled by user with timestamp and terminates cleanly."""
    runner = CliRunner()
    with patch("rouint.ui.screens.show_interactive_menu", return_value=None):
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert result.exception is None
        assert "Cancelled by user" in result.output


# ---------------------------------------------------------------------------
# 13. Robust state detection
# ---------------------------------------------------------------------------

def test_robust_state_detection_corrupted_config(clean_workspace):
    """Malformed config.json is treated as uninitialized without crashing or deleting."""
    cfg_file = clean_workspace / DATA_DIR / CONFIG_FILE
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("{invalid json!", encoding="utf-8")

    state = get_workspace_state()
    assert not state.is_initialized
    # Config file must still exist (not silently deleted)
    assert cfg_file.exists()


def test_robust_state_detection_empty_config(clean_workspace):
    """Empty config.json is treated as uninitialized."""
    cfg_file = clean_workspace / DATA_DIR / CONFIG_FILE
    cfg_file.parent.mkdir(parents=True)
    cfg_file.write_text("", encoding="utf-8")

    state = get_workspace_state()
    assert not state.is_initialized


def test_robust_state_detection_corrupted_env_file(clean_workspace):
    """Corrupted environment file is safely ignored."""
    init_workspace()
    save_environment("production", "https://api.example.com")
    bad_env = clean_workspace / DATA_DIR / ENV_DIR / "bad.json"
    bad_env.write_text("corrupted content", encoding="utf-8")

    state = get_workspace_state()
    assert state.is_initialized
    assert state.has_base_urls  # production.json is valid


def test_robust_state_detection_whitespace_token(clean_workspace):
    """Whitespace-only .temp_token is treated as missing token."""
    init_workspace()
    tok_file = clean_workspace / DATA_DIR / TEMP_TOKEN_FILE
    tok_file.write_text("   \n  ", encoding="utf-8")

    state = get_workspace_state()
    assert not state.has_token


# ---------------------------------------------------------------------------
# 14. Session banner rendering & interactive workflow loop
# ---------------------------------------------------------------------------

def test_banner_displayed_only_once_per_session():
    """Rouint ASCII banner is displayed only once per session across multiple headers."""
    from rouint.ui.components import reset_banner_state, display_header, console
    from rich.table import Table

    reset_banner_state()
    printed_tables = []
    with patch.object(console, "print", side_effect=lambda *args, **kwargs: [printed_tables.append(a) for a in args if isinstance(a, Table)]):
        display_header("First Screen")
        display_header("Second Screen")

    # Banner grid Table was printed exactly once
    assert len(printed_tables) == 1


def test_init_skips_command_list_in_launcher(clean_workspace):
    """When running inside the launcher, init skips printing the redundant command list."""
    from rouint.ui.components import set_in_launcher

    runner = CliRunner()
    set_in_launcher(True)
    try:
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert "Workspace initialized successfully" in result.output
        assert "Get started:" not in result.output
    finally:
        set_in_launcher(False)


def test_init_includes_command_list_when_direct(clean_workspace):
    """When running directly from terminal, init prints the Get started command list."""
    from rouint.ui.components import set_in_launcher

    runner = CliRunner()
    set_in_launcher(False)
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0
    assert "Workspace initialized successfully" in result.output
    assert "Get started:" in result.output


def test_launcher_session_keeps_user_in_menu(clean_workspace):
    """After a command like init completes, user is kept inside the launcher until Exit."""
    runner = CliRunner()
    with patch("rouint.ui.screens.show_interactive_menu", side_effect=["init", "exit"]) as mock_menu:
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert mock_menu.call_count == 2
        assert "Workspace Initialization" in result.output
        assert "Get started:" not in result.output
        assert "Cancelled by user" in result.output


def test_answered_prompt_tokens_styling_and_spacing():
    """Once selected, the command is highlighted in answer style and description/hint is grey without padding spaces."""
    from rouint.ui.screens import format_answered_tokens

    # 1. Test with start-test and hint
    item_start = MenuItem("start-test", "Run a test", "--no-metrics available", True)
    tokens_start = format_answered_tokens(item_start)

    # Command name is in class:answer
    answer_tokens = [txt for style, txt in tokens_start if "answer" in style]
    assert answer_tokens == ["start-test"]

    # Description and hint are in grey class:ansibrightblack
    grey_tokens = [txt for style, txt in tokens_start if "ansibrightblack" in style]
    assert len(grey_tokens) == 1
    assert grey_tokens[0] == " — Run a test (--no-metrics available)"
    # Excessive padding spaces (like 6 spaces or 24 spaces) are absent
    assert "  " not in grey_tokens[0]

    # 2. Test with init (no hint)
    item_init = MenuItem("init", "Initialize Rouint workspace", None, True)
    tokens_init = format_answered_tokens(item_init)
    assert [txt for style, txt in tokens_init if "answer" in style] == ["init"]
    assert [txt for style, txt in tokens_init if "ansibrightblack" in style] == [" — Initialize Rouint workspace"]

    # 3. Test with Exit
    item_exit = MenuItem("Exit", "", None, True, is_exit=True)
    tokens_exit = format_answered_tokens(item_exit)
    assert [txt for style, txt in tokens_exit if "answer" in style] == ["Exit"]
    assert len([txt for style, txt in tokens_exit if "ansibrightblack" in style]) == 0

    # 4. Fallback with raw padded title string
    raw_padded = "start-test      —  Run a test                        (--no-metrics available)"
    tokens_fallback = format_answered_tokens(None, raw_padded)
    assert [txt for style, txt in tokens_fallback if "answer" in style] == ["start-test"]
    assert [txt for style, txt in tokens_fallback if "ansibrightblack" in style] == [" — Run a test (--no-metrics available)"]


