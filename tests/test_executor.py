import pytest
from unittest.mock import patch, MagicMock
import subprocess
from rouint.core.executor import execute_request, CurlResponse

@patch("subprocess.run")
def test_execute_request_success(mock_run):
    # Mock curl output:
    # Headers + Body + \nHTTP_CODE\nTIME\nSIZE_DOWNLOAD
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

@patch("subprocess.run")
def test_execute_request_curl_error(mock_run):
    # Mock a curl failure (e.g. connection refused)
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=7,
        cmd="curl ...",
        stderr="curl: (7) Failed to connect to host"
    )

    resp = execute_request("http://invalid.url", "GET", {})

    assert resp.status_code == 0
    assert "Curl error" in resp.error
    assert "Failed to connect" in resp.error
