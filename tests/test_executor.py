import json
import pytest
from unittest.mock import patch, MagicMock
import subprocess
from rouint.core.executor import execute_request, CurlResponse, HttpResponse, validate_url, validate_files


# ────────────────────────────────────────────────────────────────
# Shared validation tests
# ────────────────────────────────────────────────────────────────

class TestValidateUrl:
    def test_valid_http_url(self):
        ok, err = validate_url("http://example.com/api")
        assert ok is True
        assert err == ""

    def test_valid_https_url(self):
        ok, err = validate_url("https://api.example.com/v1/users")
        assert ok is True

    def test_empty_url(self):
        ok, err = validate_url("")
        assert ok is False
        assert "empty" in err.lower()

    def test_none_url(self):
        ok, err = validate_url(None)
        assert ok is False

    def test_missing_scheme(self):
        ok, err = validate_url("example.com/api")
        assert ok is False
        assert "http://" in err or "https://" in err

    def test_missing_host(self):
        ok, err = validate_url("http:///path")
        assert ok is False
        assert "host" in err.lower()

    def test_whitespace_url(self):
        ok, err = validate_url("   ")
        assert ok is False


class TestValidateFiles:
    def test_valid_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        ok, err = validate_files([{"path": str(f), "field": "file"}])
        assert ok is True

    def test_missing_file(self):
        ok, err = validate_files([{"path": "/nonexistent/file.txt", "field": "file"}])
        assert ok is False
        assert "not found" in err.lower()

    def test_empty_path(self):
        ok, err = validate_files([{"path": "", "field": "file"}])
        assert ok is False

    def test_directory_not_file(self, tmp_path):
        ok, err = validate_files([{"path": str(tmp_path), "field": "file"}])
        assert ok is False
        assert "not a file" in err.lower()


# ────────────────────────────────────────────────────────────────
# CurlResponse backward compatibility
# ────────────────────────────────────────────────────────────────

class TestBackwardCompat:
    def test_curl_response_alias(self):
        """CurlResponse should be the same class as HttpResponse."""
        assert CurlResponse is HttpResponse

    def test_curl_response_creation(self):
        resp = CurlResponse(
            status_code=200, headers={}, body="ok",
            elapsed_time=0.1, status_line="HTTP/1.1 200 OK",
            response_size=2,
        )
        assert resp.status_code == 200
        assert resp.error is None


# ────────────────────────────────────────────────────────────────
# Linux cURL backend tests (mocked)
# ────────────────────────────────────────────────────────────────

class TestLinuxExecutor:
    @patch("rouint.platforms.linux.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Linux")
    def test_execute_request_success(self, mock_system, mock_run):
        mock_stdout = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: 18\r\n"
            "\r\n"
            '{"status": "ok"}'
            "\n200\n0.123\n18"
        )
        mock_run.return_value = MagicMock(stdout=mock_stdout, returncode=0)

        resp = execute_request("http://test.com", "GET", {"Accept": "application/json"})

        assert resp.status_code == 200
        assert resp.elapsed_time == 0.123
        assert resp.body == '{"status": "ok"}'
        assert resp.headers["Content-Type"] == "application/json"
        assert resp.status_line == "HTTP/1.1 200 OK"
        assert resp.response_size == 18
        assert resp.error is None

    @patch("rouint.platforms.linux.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Linux")
    def test_execute_request_curl_error(self, mock_system, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=7,
            cmd="curl ...",
            stderr="curl: (7) Failed to connect to host"
        )

        resp = execute_request("http://invalid.url", "GET", {})

        assert resp.status_code == 0
        assert "curl error" in resp.error
        assert "Failed to connect" in resp.error

    @patch("rouint.platforms.linux.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Linux")
    def test_execute_request_with_body(self, mock_system, mock_run):
        mock_stdout = (
            "HTTP/1.1 201 Created\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
            '{"id": 1}'
            "\n201\n0.200\n9"
        )
        mock_run.return_value = MagicMock(stdout=mock_stdout, returncode=0)

        resp = execute_request(
            "http://test.com/api",
            "POST",
            {"Content-Type": "application/json"},
            body='{"name": "test"}'
        )

        assert resp.status_code == 201
        assert resp.body == '{"id": 1}'

    @patch("rouint.platforms.linux.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Linux")
    def test_execute_request_with_files(self, mock_system, mock_run, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        mock_stdout = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
            '{"uploaded": true}'
            "\n200\n0.500\n18"
        )
        mock_run.return_value = MagicMock(stdout=mock_stdout, returncode=0)

        resp = execute_request(
            "http://test.com/upload",
            "POST",
            {"Content-Type": "application/json"},
            files=[{"field": "file", "path": str(test_file)}]
        )

        assert resp.status_code == 200

    def test_execute_request_invalid_url(self):
        resp = execute_request("not-a-url", "GET", {})
        assert resp.status_code == 0
        assert resp.error is not None

    def test_execute_request_empty_url(self):
        resp = execute_request("", "GET", {})
        assert resp.status_code == 0
        assert "empty" in resp.error.lower()

    def test_execute_request_missing_file(self):
        resp = execute_request(
            "http://test.com/upload",
            "POST",
            {},
            files=[{"field": "file", "path": "/nonexistent/file.txt"}]
        )
        assert resp.status_code == 0
        assert "not found" in resp.error.lower()


# ────────────────────────────────────────────────────────────────
# Windows PowerShell backend tests (mocked)
# ────────────────────────────────────────────────────────────────

class TestWindowsExecutor:
    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Windows")
    def test_execute_success(self, mock_system, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        result_json = {
            "status_code": 200,
            "status_line": "HTTP/1.1 200 OK",
            "headers": {"Content-Type": "application/json"},
            "body": '{"status": "ok"}',
            "elapsed_ms": 150,
            "response_size": 16,
            "error": None,
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(result_json),
            stderr="",
            returncode=0,
        )

        resp = execute_request("http://test.com", "GET", {"Accept": "application/json"})

        assert resp.status_code == 200
        assert resp.body == '{"status": "ok"}'
        assert resp.headers["Content-Type"] == "application/json"
        assert resp.error is None

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.core.executor.platform.system", return_value="Windows")
    def test_no_powershell(self, mock_system, mock_which):
        mock_which.return_value = None

        resp = execute_request("http://test.com", "GET", {})

        assert resp.status_code == 0
        assert "powershell" in resp.error.lower()

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Windows")
    def test_http_error_response(self, mock_system, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        result_json = {
            "status_code": 404,
            "status_line": "HTTP/1.1 404 Not Found",
            "headers": {"Content-Type": "text/html"},
            "body": "Not Found",
            "elapsed_ms": 100,
            "response_size": 9,
            "error": None,
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(result_json),
            stderr="",
            returncode=0,
        )

        resp = execute_request("http://test.com/missing", "GET", {})

        assert resp.status_code == 404
        assert resp.body == "Not Found"
        assert resp.error is None  # Server responded — not an execution error

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Windows")
    def test_network_error(self, mock_system, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        result_json = {
            "status_code": 0,
            "status_line": "",
            "headers": {},
            "body": "",
            "elapsed_ms": 50,
            "response_size": 0,
            "error": "Network error: No such host is known",
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(result_json),
            stderr="",
            returncode=0,
        )

        resp = execute_request("http://nonexistent.invalid", "GET", {})

        assert resp.status_code == 0
        assert resp.error is not None
        assert "network" in resp.error.lower()

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Windows")
    def test_post_with_body(self, mock_system, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        result_json = {
            "status_code": 201,
            "status_line": "HTTP/1.1 201 Created",
            "headers": {"Content-Type": "application/json"},
            "body": '{"id": 42}',
            "elapsed_ms": 200,
            "response_size": 10,
            "error": None,
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(result_json),
            stderr="",
            returncode=0,
        )

        resp = execute_request(
            "http://test.com/api",
            "POST",
            {"Content-Type": "application/json"},
            body='{"name": "test"}'
        )

        assert resp.status_code == 201

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Windows")
    def test_timeout(self, mock_system, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pwsh", timeout=300)

        resp = execute_request("http://slow.server", "GET", {})

        assert resp.status_code == 0
        assert "timed out" in resp.error.lower()

    @patch("rouint.platforms.windows.executor.shutil.which")
    @patch("rouint.platforms.windows.executor.subprocess.run")
    @patch("rouint.core.executor.platform.system", return_value="Windows")
    def test_powershell_execution_failure(self, mock_system, mock_run, mock_which):
        mock_which.side_effect = lambda x: "pwsh" if x == "pwsh" else None
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="Script execution error",
            returncode=1,
        )

        resp = execute_request("http://test.com", "GET", {})

        assert resp.status_code == 0
        assert resp.error is not None
