import pytest
from rouint.core.manager import EndpointManager
from rouint.utils.config import init_workspace, get_data_path

@pytest.fixture(autouse=True)
def setup_tmp_workspace(tmp_path, monkeypatch):
    """Sets cwd to a temporary workspace for isolated manager testing."""
    monkeypatch.chdir(tmp_path)
    init_workspace()

def test_save_and_get_endpoint_path_normalization():
    manager = EndpointManager()
    
    # Save endpoint with path missing leading slash
    ep_id = manager.save_endpoint(
        name="Login API",
        method="POST",
        path="api/v1/auth/login",
        base_url_ref=None,
        headers={"Accept": "application/json"},
        auth={"type": "none"},
        body=None
    )
    
    assert ep_id == "ep_login-api"
    
    ep = manager.get_endpoint("login-api")
    assert ep is not None
    assert ep["name"] == "Login API"
    # Ensure path was normalized to start with leading slash
    assert ep["path"] == "/api/v1/auth/login"

def test_save_endpoint_empty_name_validation():
    manager = EndpointManager()
    with pytest.raises(ValueError, match="Endpoint name cannot be empty"):
        manager.save_endpoint(
            name="   ",
            method="GET",
            path="/api/v1/users",
            base_url_ref=None,
            headers={},
            auth={"type": "none"},
            body=None
        )
