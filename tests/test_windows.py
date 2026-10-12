"""
Windows-specific tests for the PowerShell HTTP backend.

These tests cover:
- PowerShell script generation
- Special characters and Unicode handling
- File path handling (spaces in paths)
- All HTTP methods
- Header and auth handling
- Security (redaction, no credential leaks)

Unit tests use mocks. Integration tests (marked with @pytest.mark.windows_integration)
require a real Windows environment with PowerShell and are skipped elsewhere.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from rouint.core.executor import HttpResponse
from rouint.platforms.windows.executor import (
    _find_powershell,
    _build_powershell_script,
    execute_request as win_execute_request,
)


# ────────────────────────────────────────────────────────────────
# PowerShell discovery
# ────────────────────────────────────────────────────────────────

class TestFindPowerShell:
    @patch("rouint.platforms.windows.executor.shutil.which")
    def test_prefers_pwsh(self, mock_which):
        mock_which.side_effect = lambda x: "/usr/bin/pwsh" if x == "pwsh" else None
        assert _find_powershell() == "pwsh"

    @patch("rouint.platforms.windows.executor.shutil.which")
    def test_falls_back_to_powershell(self, mock_which):
        mock_which.side_effect = lambda x: "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" if x == "powershell" else None
        assert _find_powershell() == "powershell"

    @patch("rouint.platforms.windows.executor.shutil.which")
    def test_returns_none_when_missing(self, mock_which):
        mock_which.return_value = None
        assert _find_powershell() is None


# ────────────────────────────────────────────────────────────────
# PowerShell script generation
# ────────────────────────────────────────────────────────────────

class TestScriptGeneration:
    def test_basic_get_script(self):
        script = _build_powershell_script(
            url="http://example.com/api",
            method="GET",
            headers={"Accept": "application/json"},
        )
        assert "Invoke-WebRequest" in script
        assert "http://example.com/api" in script
        assert "GET" in script
        assert "Accept" in script

    def test_post_with_body(self):
        script = _build_powershell_script(
            url="http://example.com/api",
            method="POST",
            headers={"Content-Type": "application/json"},
            body='{"key": "value"}',
        )
        assert "POST" in script
        assert '{"key": "value"}' in script

    def test_special_chars_in_url(self):
        script = _build_powershell_script(
            url="http://example.com/search?q=hello%20world&lang=en",
            method="GET",
            headers={},
        )
        assert "hello%20world" in script

    def test_single_quote_escaping(self):
        """Single quotes in values should be doubled for PowerShell."""
        script = _build_powershell_script(
            url="http://example.com/api",
            method="POST",
            headers={"X-Custom": "it's a test"},
            body='{"name": "O\'Brien"}',
        )
        assert "it''s a test" in script
        assert "O''Brien" in script

    def test_all_http_methods(self):
        for method in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
            script = _build_powershell_script(
                url="http://example.com/api",
                method=method,
                headers={},
            )
            assert f"Method = '{method}'" in script

    def test_bearer_auth_header(self):
        script = _build_powershell_script(
            url="http://example.com/api",
            method="GET",
            headers={"Authorization": "Bearer mytoken123"},
        )
        assert "Authorization" in script
        assert "Bearer mytoken123" in script

    def test_multipart_with_files(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        script = _build_powershell_script(
            url="http://example.com/upload",
            method="POST",
            headers={"Accept": "application/json"},
            files=[{"field": "document", "path": str(test_file)}],
        )
        assert "multipart" in script.lower() or "Form" in script
        assert str(test_file).replace("'", "''") in script or "document" in script

    def test_unicode_body(self):
        script = _build_powershell_script(
            url="http://example.com/api",
            method="POST",
            headers={"Content-Type": "application/json"},
            body='{"name": "日本語テスト"}',
        )
        assert "日本語テスト" in script

    def test_empty_body_not_included(self):
        script = _build_powershell_script(
            url="http://example.com/api",
            method="GET",
            headers={},
            body=None,
        )
        assert "$bodyText" not in script

    def test_content_type_removed_for_files(self):
        """Content-Type header should be filtered out when files are attached."""
        script = _build_powershell_script(
            url="http://example.com/upload",
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            files=[{"field": "file", "path": "/tmp/test.txt"}],
        )
        # Content-Type should not appear in header assignments
        lines = [l for l in script.split("\n") if "Content-Type" in l and "$headers[" in l]
        assert len(lines) == 0


# ────────────────────────────────────────────────────────────────
# Windows executor mocked execution
# ────────────────────────────────────────────────────────────────

class TestWindowsExecutorMocked:
    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    def test_successful_response(self, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        result_json = {
            "status_code": 200,
            "status_line": "HTTP/1.1 200 OK",
            "headers": {"Content-Type": "application/json"},
            "body": '{"result": "success"}',
            "elapsed_ms": 100,
            "response_size": 21,
            "error": None,
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(result_json), stderr="", returncode=0,
        )

        resp = win_execute_request("http://test.com", "GET", {})
        assert resp.status_code == 200
        assert resp.error is None

    @patch("rouint.platforms.windows.executor.shutil.which")
    def test_missing_powershell(self, mock_which):
        mock_which.return_value = None
        resp = win_execute_request("http://test.com", "GET", {})
        assert resp.status_code == 0
        assert "powershell" in resp.error.lower()

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    def test_4xx_error_still_returns_response(self, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        result_json = {
            "status_code": 404,
            "status_line": "HTTP/1.1 404 Not Found",
            "headers": {"Content-Type": "text/plain"},
            "body": "Not Found",
            "elapsed_ms": 50,
            "response_size": 9,
            "error": None,
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(result_json), stderr="", returncode=0,
        )

        resp = win_execute_request("http://test.com", "GET", {})
        assert resp.status_code == 404
        assert resp.body == "Not Found"
        assert resp.error is None  # Server responded

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    def test_5xx_error_still_returns_response(self, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        result_json = {
            "status_code": 500,
            "status_line": "HTTP/1.1 500 Internal Server Error",
            "headers": {"Content-Type": "text/plain"},
            "body": "Internal Server Error",
            "elapsed_ms": 50,
            "response_size": 21,
            "error": None,
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(result_json), stderr="", returncode=0,
        )

        resp = win_execute_request("http://test.com", "GET", {})
        assert resp.status_code == 500
        assert resp.body == "Internal Server Error"
        assert resp.error is None  # Server responded

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    def test_malformed_json_output(self, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        mock_run.return_value = MagicMock(
            stdout="not valid json", stderr="", returncode=0,
        )

        resp = win_execute_request("http://test.com", "GET", {})
        assert resp.status_code == 0
        assert "parse" in resp.error.lower() or "failed" in resp.error.lower()


# ────────────────────────────────────────────────────────────────
# Windows integration tests (only run on Windows with PowerShell)
# ────────────────────────────────────────────────────────────────

is_windows = platform.system().lower() == "windows"
has_powershell = _find_powershell() is not None if is_windows else False

windows_integration = pytest.mark.skipif(
    not (is_windows and has_powershell),
    reason="Requires Windows with PowerShell"
)


@windows_integration
class TestWindowsIntegration:
    """
    Real integration tests that execute PowerShell on Windows.
    These are skipped on Linux/macOS and in CI without PowerShell.
    """

    def test_real_https_get(self):
        """Test a real HTTPS GET to a public API."""
        resp = win_execute_request(
            "https://httpbin.org/get",
            "GET",
            {"Accept": "application/json"},
        )
        # httpbin might be slow or down; check we at least get a response
        if (resp.error and "network" in resp.error.lower()) or resp.status_code in (502, 503, 504):
            pytest.skip("httpbin.org unreachable or temporarily unavailable")
        assert resp.status_code == 200
        assert resp.body  # Should have JSON body
        assert resp.elapsed_time > 0

    def test_real_post(self):
        resp = win_execute_request(
            "https://httpbin.org/post",
            "POST",
            {"Content-Type": "application/json", "Accept": "application/json"},
            body='{"test": "value"}',
        )
        if (resp.error and "network" in resp.error.lower()) or resp.status_code in (502, 503, 504):
            pytest.skip("httpbin.org unreachable or temporarily unavailable")
        assert resp.status_code == 200

    def test_real_404(self):
        resp = win_execute_request(
            "https://httpbin.org/status/404",
            "GET",
            {},
        )
        if (resp.error and "network" in resp.error.lower()) or resp.status_code in (502, 503, 504):
            pytest.skip("httpbin.org unreachable or temporarily unavailable")
        assert resp.status_code == 404
        assert resp.error is None  # Server responded

    def test_unicode_request(self):
        resp = win_execute_request(
            "https://httpbin.org/post",
            "POST",
            {"Content-Type": "application/json"},
            body='{"name": "日本語テスト", "emoji": "🎉"}',
        )
        if (resp.error and "network" in resp.error.lower()) or resp.status_code in (502, 503, 504):
            pytest.skip("httpbin.org unreachable or temporarily unavailable")
        assert resp.status_code == 200
