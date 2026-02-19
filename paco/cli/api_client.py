"""
PACO API client.

httpx-based client with automatic JWT authentication.
"""

from typing import Any, Dict, Optional

import httpx

from cli.config import get_api_url, get_token


class AuthError(Exception):
    """Raised when the user is not authenticated."""


class APIError(Exception):
    """Raised on non-2xx API responses."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


def _headers() -> Dict[str, str]:
    token = get_token()
    if not token:
        raise AuthError(
            "Not authenticated. Run 'paco auth login' first."
        )
    return {"Authorization": f"Bearer {token}"}


def _base_url() -> str:
    return get_api_url()


def _handle_response(resp: httpx.Response) -> Any:
    if resp.status_code == 204:
        return None
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise APIError(resp.status_code, detail)
    return resp.json()


# -- Auth (no token required) ------------------------------------------------

def login(email: str, password: str) -> dict:
    """POST /api/auth/login -- returns {token, user}."""
    with httpx.Client(timeout=15.0) as c:
        resp = c.post(
            f"{_base_url()}/auth/login",
            json={"email": email, "password": password},
        )
    return _handle_response(resp)


def get_me() -> dict:
    """GET /api/auth/me -- returns current user info."""
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/auth/me", headers=_headers())
    return _handle_response(resp)


# -- Agents ------------------------------------------------------------------

def list_agents() -> list:
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/agents", headers=_headers())
    return _handle_response(resp)


def get_agent(agent_id: str) -> dict:
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/agents/{agent_id}", headers=_headers())
    return _handle_response(resp)


def start_agent(agent_id: str) -> dict:
    with httpx.Client(timeout=30.0) as c:
        resp = c.post(f"{_base_url()}/agents/{agent_id}/start", headers=_headers())
    return _handle_response(resp)


def stop_agent(agent_id: str) -> dict:
    with httpx.Client(timeout=30.0) as c:
        resp = c.post(f"{_base_url()}/agents/{agent_id}/stop", headers=_headers())
    return _handle_response(resp)


def restart_agent(agent_id: str) -> dict:
    with httpx.Client(timeout=30.0) as c:
        resp = c.post(f"{_base_url()}/agents/{agent_id}/restart", headers=_headers())
    return _handle_response(resp)


def get_agent_status(agent_id: str) -> dict:
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/agents/{agent_id}/status", headers=_headers())
    return _handle_response(resp)


# -- Skills ------------------------------------------------------------------

def list_skills() -> list:
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/skills", headers=_headers())
    return _handle_response(resp)


def get_skill(code: str) -> dict:
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/skills/{code}", headers=_headers())
    return _handle_response(resp)


def sync_skills() -> dict:
    with httpx.Client(timeout=30.0) as c:
        resp = c.post(f"{_base_url()}/skills/sync", headers=_headers())
    return _handle_response(resp)


# -- Tools -------------------------------------------------------------------

def list_tools(server_id: Optional[str] = None) -> list:
    params: Dict[str, Any] = {}
    if server_id:
        params["server_id"] = server_id
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/tools", headers=_headers(), params=params)
    return _handle_response(resp)


def list_mcp_servers() -> list:
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/tools/servers", headers=_headers())
    return _handle_response(resp)


def sync_tools(server_id: str) -> list:
    with httpx.Client(timeout=30.0) as c:
        resp = c.post(
            f"{_base_url()}/tools/servers/{server_id}/sync",
            headers=_headers(),
        )
    return _handle_response(resp)


# -- Infrastructures ---------------------------------------------------------

def list_infrastructures() -> list:
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/infrastructures", headers=_headers())
    return _handle_response(resp)


def get_infrastructure(infra_id: str) -> dict:
    with httpx.Client(timeout=10.0) as c:
        resp = c.get(f"{_base_url()}/infrastructures/{infra_id}", headers=_headers())
    return _handle_response(resp)
