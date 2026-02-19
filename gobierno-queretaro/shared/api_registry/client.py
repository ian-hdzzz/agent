"""
Gobierno Queretaro - Unified API Client Factory
Reads apis.yaml and creates configured async HTTP clients for each government API.
Supports REST (JSON) and SOAP (XML) protocols with circuit breaker integration.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml

from ..utils.http_client import (
    CircuitOpenError,
    ResilientHTTPClient,
    get_circuit_breaker,
    get_resilient_client,
)

logger = logging.getLogger(__name__)

REGISTRY_DIR = Path(__file__).parent
APIS_YAML_PATH = REGISTRY_DIR / "apis.yaml"
SCHEMAS_DIR = REGISTRY_DIR / "schemas"
MOCKS_DIR = REGISTRY_DIR / "mocks"


# ============================================
# Data classes
# ============================================

@dataclass
class OperationDef:
    """A single API operation (endpoint/action)."""
    id: str
    description: str
    input_params: list[str] = field(default_factory=list)
    # REST-specific
    method: str = "POST"
    path: str = ""
    # SOAP-specific
    endpoint: str = ""
    soap_action: str = ""


@dataclass
class APIDefinition:
    """Full definition of a government API from the registry."""
    api_id: str
    name: str
    description: str
    base_url: str
    protocol: str  # REST or SOAP
    auth_type: str  # ws-security, api-key, bearer
    auth_config: dict[str, str] = field(default_factory=dict)
    timeout_ms: int = 15000
    rate_limit: dict[str, int] = field(default_factory=dict)
    status: str = "mocked"  # active, planned, mocked
    operations: list[OperationDef] = field(default_factory=list)


# ============================================
# SOAP envelope helpers
# ============================================

_SOAP_ENVELOPE_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<soapenv:Envelope'
    ' xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
    ' xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"'
    ' xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">'
    "{header}"
    "<soapenv:Body>{body}</soapenv:Body>"
    "</soapenv:Envelope>"
)

_WS_SECURITY_HEADER = (
    "<soapenv:Header>"
    '<wsse:Security soapenv:mustUnderstand="1">'
    '<wsse:UsernameToken wsu:Id="{token_id}">'
    "<wsse:Username>{username}</wsse:Username>"
    '<wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/'
    'oasis-200401-wss-username-token-profile-1.0#PasswordText">'
    "{password}</wsse:Password>"
    "</wsse:UsernameToken>"
    "</wsse:Security>"
    "</soapenv:Header>"
)


def build_ws_security_header(
    username: str, password: str, token_id: str = "UsernameToken"
) -> str:
    """Build a WS-Security SOAP header."""
    return _WS_SECURITY_HEADER.format(
        token_id=token_id, username=username, password=password
    )


def build_soap_envelope(header: str, body: str) -> str:
    """Wrap a SOAP body with envelope and optional header."""
    return _SOAP_ENVELOPE_TEMPLATE.format(header=header, body=body)


# ============================================
# Environment variable resolution
# ============================================

_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)(?::([^}]*))?\}")


def _resolve_env(value: str) -> str:
    """Resolve ${VAR:default} patterns in a string."""
    def _replace(match: re.Match) -> str:
        var_name = match.group(1)
        default = match.group(2) or ""
        return os.getenv(var_name, default)
    return _ENV_VAR_PATTERN.sub(_replace, value)


# ============================================
# Mock response loader
# ============================================

def _load_mock_response(api_id: str, operation_id: str, protocol: str) -> str | None:
    """Load a mock response fixture from the mocks/ directory."""
    ext = "xml" if protocol == "SOAP" else "json"
    mock_path = MOCKS_DIR / f"{api_id}" / f"{operation_id}.{ext}"
    if mock_path.exists():
        return mock_path.read_text(encoding="utf-8")
    return None


# ============================================
# API Client wrapper
# ============================================

class APIClient:
    """
    Pre-configured async client for a single government API.
    Handles protocol differences (REST vs SOAP), authentication injection,
    mock fallback, and circuit breaker integration.
    """

    def __init__(
        self,
        definition: APIDefinition,
        http_client: ResilientHTTPClient,
    ):
        self.definition = definition
        self._http = http_client
        self._auth_credentials: dict[str, str] | None = None

    @property
    def api_id(self) -> str:
        return self.definition.api_id

    @property
    def is_active(self) -> bool:
        return self.definition.status == "active"

    @property
    def is_mocked(self) -> bool:
        return self.definition.status == "mocked"

    def _resolve_auth(self) -> dict[str, str]:
        """Resolve authentication credentials from environment variables."""
        if self._auth_credentials is not None:
            return self._auth_credentials

        cfg = self.definition.auth_config
        creds: dict[str, str] = {}

        if self.definition.auth_type == "ws-security":
            creds["username"] = os.getenv(cfg.get("username_env", ""), "")
            creds["password"] = os.getenv(cfg.get("password_env", ""), "")
            creds["token_id"] = cfg.get("token_id_prefix", "UsernameToken")
        elif self.definition.auth_type == "api-key":
            creds["header_name"] = cfg.get("header_name", "X-API-Key")
            creds["key"] = os.getenv(cfg.get("key_env", ""), "")
        elif self.definition.auth_type == "bearer":
            creds["token"] = os.getenv(cfg.get("token_env", ""), "")

        self._auth_credentials = creds
        return creds

    def _build_auth_headers(self) -> dict[str, str]:
        """Build HTTP headers for REST authentication."""
        creds = self._resolve_auth()
        headers: dict[str, str] = {}

        if self.definition.auth_type == "api-key":
            header_name = creds.get("header_name", "X-API-Key")
            headers[header_name] = creds.get("key", "")
        elif self.definition.auth_type == "bearer":
            token = creds.get("token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        return headers

    def get_operation(self, operation_id: str) -> OperationDef | None:
        """Look up an operation by ID."""
        for op in self.definition.operations:
            if op.id == operation_id:
                return op
        return None

    async def call_rest(
        self,
        operation_id: str,
        path_params: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a REST API operation.

        Args:
            operation_id: The operation ID from apis.yaml
            path_params: Values to interpolate into the URL path
            query_params: Query string parameters
            json_body: JSON request body (for POST/PUT)

        Returns:
            Parsed JSON response or mock data
        """
        op = self.get_operation(operation_id)
        if op is None:
            raise ValueError(f"Unknown operation '{operation_id}' for API '{self.api_id}'")

        # Use mock if API is not active
        if self.is_mocked:
            mock = _load_mock_response(self.api_id, operation_id, "REST")
            if mock:
                logger.info(f"[{self.api_id}] Returning mock for {operation_id}")
                return json.loads(mock)
            logger.warning(f"[{self.api_id}] No mock found for {operation_id}, returning empty")
            return {"mock": True, "api": self.api_id, "operation": operation_id, "data": {}}

        # Build URL
        path = op.path
        if path_params:
            for key, val in path_params.items():
                path = path.replace(f"{{{key}}}", val)

        url = f"{self.definition.base_url}{path}"
        headers = self._build_auth_headers()

        method = op.method.upper()
        kwargs: dict[str, Any] = {
            "headers": headers,
            "service_id": self.api_id,
        }
        if query_params:
            kwargs["params"] = query_params
        if json_body and method in ("POST", "PUT", "PATCH"):
            kwargs["json"] = json_body

        response = await self._http.request(method, url, **kwargs)
        return response.json()

    async def call_soap(
        self,
        operation_id: str,
        soap_body_xml: str,
    ) -> str:
        """
        Execute a SOAP API operation.

        Args:
            operation_id: The operation ID from apis.yaml
            soap_body_xml: The inner SOAP body XML (without envelope)

        Returns:
            Raw XML response string or mock XML
        """
        op = self.get_operation(operation_id)
        if op is None:
            raise ValueError(f"Unknown operation '{operation_id}' for API '{self.api_id}'")

        # Use mock if API is not active
        if self.is_mocked:
            mock = _load_mock_response(self.api_id, operation_id, "SOAP")
            if mock:
                logger.info(f"[{self.api_id}] Returning SOAP mock for {operation_id}")
                return mock
            logger.warning(f"[{self.api_id}] No SOAP mock found for {operation_id}")
            return "<empty/>"

        # Build full SOAP envelope with WS-Security
        header_xml = ""
        if self.definition.auth_type == "ws-security":
            creds = self._resolve_auth()
            header_xml = build_ws_security_header(
                username=creds.get("username", ""),
                password=creds.get("password", ""),
                token_id=creds.get("token_id", "UsernameToken"),
            )

        envelope = build_soap_envelope(header=header_xml, body=soap_body_xml)
        url = f"{self.definition.base_url}/{op.endpoint}"

        response = await self._http.request(
            "POST",
            url,
            content=envelope,
            headers={"Content-Type": "text/xml;charset=UTF-8"},
            service_id=self.api_id,
        )
        return response.text

    async def call(
        self,
        operation_id: str,
        *,
        path_params: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        soap_body_xml: str | None = None,
    ) -> dict[str, Any] | str:
        """
        Unified call method - dispatches to REST or SOAP based on protocol.

        Returns dict for REST, raw XML string for SOAP.
        """
        if self.definition.protocol == "SOAP":
            if soap_body_xml is None:
                raise ValueError("soap_body_xml is required for SOAP APIs")
            return await self.call_soap(operation_id, soap_body_xml)
        else:
            return await self.call_rest(
                operation_id,
                path_params=path_params,
                query_params=query_params,
                json_body=json_body,
            )


# ============================================
# Factory
# ============================================

class APIClientFactory:
    """
    Central factory that reads apis.yaml and produces pre-configured
    APIClient instances for each government service API.
    """

    def __init__(self, yaml_path: Path | None = None):
        self._yaml_path = yaml_path or APIS_YAML_PATH
        self._definitions: dict[str, APIDefinition] = {}
        self._clients: dict[str, APIClient] = {}
        self._http_client: ResilientHTTPClient | None = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy-load the YAML catalog on first access."""
        if self._loaded:
            return
        self._load_catalog()
        self._loaded = True

    def _load_catalog(self) -> None:
        """Parse apis.yaml into APIDefinition objects."""
        raw = self._yaml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        apis = data.get("apis", {})

        for api_id, api_raw in apis.items():
            ops = []
            for op_raw in api_raw.get("operations", []):
                ops.append(OperationDef(
                    id=op_raw["id"],
                    description=op_raw.get("description", ""),
                    input_params=op_raw.get("input_params", []),
                    method=op_raw.get("method", "POST"),
                    path=op_raw.get("path", ""),
                    endpoint=op_raw.get("endpoint", ""),
                    soap_action=op_raw.get("soap_action", ""),
                ))

            self._definitions[api_id] = APIDefinition(
                api_id=api_id,
                name=api_raw["name"],
                description=api_raw.get("description", ""),
                base_url=_resolve_env(api_raw["base_url"]),
                protocol=api_raw.get("protocol", "REST"),
                auth_type=api_raw.get("auth_type", "api-key"),
                auth_config=api_raw.get("auth_config", {}),
                timeout_ms=api_raw.get("timeout_ms", 15000),
                rate_limit=api_raw.get("rate_limit", {}),
                status=api_raw.get("status", "mocked"),
                operations=ops,
            )

        logger.info(f"API registry loaded: {len(self._definitions)} APIs")

    def _get_http_client(self) -> ResilientHTTPClient:
        """Get or create the shared resilient HTTP client."""
        if self._http_client is None:
            self._http_client = get_resilient_client(timeout=30.0, max_retries=3)
        return self._http_client

    def get_client(self, api_id: str) -> APIClient:
        """
        Get a pre-configured APIClient for the given API.

        Args:
            api_id: API identifier from apis.yaml (e.g. 'cea-water', 'ameq-transport')

        Returns:
            Configured APIClient instance

        Raises:
            KeyError: If api_id is not in the registry
        """
        self._ensure_loaded()

        if api_id in self._clients:
            return self._clients[api_id]

        if api_id not in self._definitions:
            available = ", ".join(sorted(self._definitions.keys()))
            raise KeyError(
                f"API '{api_id}' not found in registry. Available: {available}"
            )

        definition = self._definitions[api_id]
        client = APIClient(
            definition=definition,
            http_client=self._get_http_client(),
        )
        self._clients[api_id] = client
        return client

    def list_apis(self) -> list[dict[str, Any]]:
        """List all registered APIs with their status."""
        self._ensure_loaded()
        return [
            {
                "id": d.api_id,
                "name": d.name,
                "protocol": d.protocol,
                "status": d.status,
                "operations": len(d.operations),
            }
            for d in self._definitions.values()
        ]

    def get_definition(self, api_id: str) -> APIDefinition:
        """Get the raw API definition."""
        self._ensure_loaded()
        return self._definitions[api_id]

    def get_active_apis(self) -> list[str]:
        """Return IDs of APIs with status 'active'."""
        self._ensure_loaded()
        return [d.api_id for d in self._definitions.values() if d.status == "active"]

    def get_mocked_apis(self) -> list[str]:
        """Return IDs of APIs with status 'mocked'."""
        self._ensure_loaded()
        return [d.api_id for d in self._definitions.values() if d.status == "mocked"]


# ============================================
# Singleton access
# ============================================

_factory: APIClientFactory | None = None


def get_api_client_factory() -> APIClientFactory:
    """Get or create the singleton APIClientFactory."""
    global _factory
    if _factory is None:
        _factory = APIClientFactory()
    return _factory
