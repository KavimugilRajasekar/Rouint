import pytest
from rouint.core.parser import extract_placeholders, resolve_placeholders, validate_path

def test_extract_placeholders():
    path = "/api/v1/users/{user_id}/posts/{post_id}"
    assert extract_placeholders(path) == ["user_id", "post_id"]

    path_none = "/api/v1/status"
    assert extract_placeholders(path_none) == []

def test_resolve_placeholders():
    path = "/api/v1/users/{user_id}"
    values = {"user_id": "123"}
    assert resolve_placeholders(path, values) == "/api/v1/users/123"

    # Test URL encoding
    path_complex = "/search?q={query}"
    values_complex = {"query": "hello world!"}
    assert resolve_placeholders(path_complex, values_complex) == "/search?q=hello%20world!"

def test_validate_path_valid():
    path = "/api/v1/users/{user_id}"
    valid, msg = validate_path(path)
    assert valid is True
    assert msg == "Valid"

def test_validate_path_mismatched_braces():
    path = "/api/v1/users/{user_id"
    valid, msg = validate_path(path)
    assert valid is False
    assert "mismatched curly braces" in msg

def test_validate_path_duplicate_placeholders():
    path = "/api/v1/{id}/detail/{id}"
    valid, msg = validate_path(path)
    assert valid is False
    assert "Duplicate placeholders" in msg
