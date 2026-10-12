"""
Tests for the platform detection and backend selection logic.
"""

import platform
from unittest.mock import patch

from rouint.platforms import get_platform
from rouint.core.executor import _get_platform_backend, HttpResponse


class TestPlatformDetection:
    @patch("rouint.platforms.platform.system", return_value="Linux")
    def test_linux_detection(self, mock_system):
        assert get_platform() == "linux"

    @patch("rouint.platforms.platform.system", return_value="Darwin")
    def test_macos_detection(self, mock_system):
        assert get_platform() == "linux"  # macOS uses the curl backend

    @patch("rouint.platforms.platform.system", return_value="Windows")
    def test_windows_detection(self, mock_system):
        assert get_platform() == "windows"

    @patch("rouint.platforms.platform.system", return_value="FreeBSD")
    def test_unsupported_detection(self, mock_system):
        assert get_platform() == "unsupported"


class TestBackendSelection:
    @patch("rouint.core.executor.platform.system", return_value="Linux")
    def test_linux_backend(self, mock_system):
        backend = _get_platform_backend()
        from rouint.platforms.linux.executor import execute_request as linux_exec
        assert backend is linux_exec

    @patch("rouint.core.executor.platform.system", return_value="Windows")
    def test_windows_backend(self, mock_system):
        backend = _get_platform_backend()
        from rouint.platforms.windows.executor import execute_request as win_exec
        assert backend is win_exec

    @patch("rouint.core.executor.platform.system", return_value="Darwin")
    def test_macos_uses_linux_backend(self, mock_system):
        backend = _get_platform_backend()
        from rouint.platforms.linux.executor import execute_request as linux_exec
        assert backend is linux_exec


class TestHttpResponse:
    def test_default_values(self):
        resp = HttpResponse(status_code=200, headers={}, body="", elapsed_time=0.1)
        assert resp.status_line == ""
        assert resp.response_size == 0
        assert resp.error is None

    def test_error_response(self):
        resp = HttpResponse(
            status_code=0, headers={}, body="",
            elapsed_time=0.0, error="Something went wrong"
        )
        assert resp.error == "Something went wrong"

    def test_full_response(self):
        resp = HttpResponse(
            status_code=404,
            headers={"Content-Type": "text/html"},
            body="Not Found",
            elapsed_time=0.5,
            status_line="HTTP/1.1 404 Not Found",
            response_size=9,
        )
        assert resp.status_code == 404
        assert resp.body == "Not Found"
        assert resp.response_size == 9
