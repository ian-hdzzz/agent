"""
Unit tests for agents.water-cea.tools

Tests SOAP XML building, response XML parsing, and tool output schemas.
All HTTP calls are mocked -- no CEA API calls are made.
"""

import importlib
import importlib.util
import re
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Create a mock config module for water-cea agent.
# The directory has a hyphen so we need to handle it specially.
_mock_settings = MagicMock()
_mock_settings.cea_api_base = "https://fake-cea.test/services"
_mock_settings.cea_proxy_url = None

# Register parent package stubs for relative import resolution
_water_cea_dir = PROJECT_ROOT / "agents" / "water-cea"

if "agents" not in sys.modules:
    _agents_pkg = types.ModuleType("agents")
    _agents_pkg.__path__ = [str(PROJECT_ROOT / "agents")]  # type: ignore
    sys.modules["agents"] = _agents_pkg

# Python doesn't allow hyphens in module names, so we register with a
# normalised key that matches how importlib resolves the relative import.
_water_config_mod = types.ModuleType("agents.water-cea.config")
_water_config_mod.get_settings = lambda: _mock_settings  # type: ignore
sys.modules["agents.water-cea.config"] = _water_config_mod

_water_pkg = types.ModuleType("agents.water-cea")
_water_pkg.__path__ = [str(_water_cea_dir)]  # type: ignore
_water_pkg.config = _water_config_mod  # type: ignore
sys.modules["agents.water-cea"] = _water_pkg

# Import the tools module
_tools_path = _water_cea_dir / "tools.py"
_spec = importlib.util.spec_from_file_location(
    "agents.water-cea.tools",
    _tools_path,
    submodule_search_locations=[],
)
water_tools = importlib.util.module_from_spec(_spec)
sys.modules["agents.water-cea.tools"] = water_tools
_spec.loader.exec_module(water_tools)

# Convenient aliases
build_deuda_soap = water_tools.build_deuda_soap
build_consumo_soap = water_tools.build_consumo_soap
build_contrato_soap = water_tools.build_contrato_soap
build_facturas_soap = water_tools.build_facturas_soap
parse_xml_value = water_tools.parse_xml_value


# ===================================================================
# SOAP XML Building
# ===================================================================

class TestBuildDeudaSoap:
    """Test debt SOAP request building."""

    def test_contains_contrato_value(self):
        xml = build_deuda_soap("123456")
        assert "<valor>123456</valor>" in xml

    def test_contains_soap_envelope(self):
        xml = build_deuda_soap("999999")
        assert "soapenv:Envelope" in xml

    def test_contains_security_header(self):
        xml = build_deuda_soap("123456")
        assert "wsse:Security" in xml
        assert "WSGESTIONDEUDA" in xml

    def test_contains_getdeuda_operation(self):
        xml = build_deuda_soap("123456")
        assert "getDeuda" in xml

    def test_contains_explotacion(self):
        xml = build_deuda_soap("123456")
        assert "<explotacion>12</explotacion>" in xml

    def test_different_contrato_values(self):
        xml1 = build_deuda_soap("111111")
        xml2 = build_deuda_soap("222222")
        assert "<valor>111111</valor>" in xml1
        assert "<valor>222222</valor>" in xml2


class TestBuildConsumoSoap:
    """Test consumption SOAP request building."""

    def test_contains_contrato(self):
        xml = build_consumo_soap("123456")
        assert "<contrato>123456</contrato>" in xml

    def test_default_explotacion(self):
        xml = build_consumo_soap("123456")
        assert "<explotacion>1</explotacion>" in xml

    def test_custom_explotacion(self):
        xml = build_consumo_soap("123456", explotacion="12")
        assert "<explotacion>12</explotacion>" in xml

    def test_contains_getconsumos_operation(self):
        xml = build_consumo_soap("123456")
        assert "getConsumos" in xml


class TestBuildContratoSoap:
    """Test contract details SOAP request building."""

    def test_contains_contrato(self):
        xml = build_contrato_soap("123456")
        assert "<numeroContrato>123456</numeroContrato>" in xml

    def test_contains_consulta_operation(self):
        xml = build_contrato_soap("123456")
        assert "consultaDetalleContrato" in xml


class TestBuildFacturasSoap:
    """Test invoices SOAP request building."""

    def test_contains_contrato(self):
        xml = build_facturas_soap("123456")
        assert "<contrato>123456</contrato>" in xml

    def test_contains_getfacturas_operation(self):
        xml = build_facturas_soap("123456")
        assert "getFacturas" in xml


# ===================================================================
# XML Parsing
# ===================================================================

class TestParseXmlValue:
    """Test XML tag value extraction."""

    def test_parse_simple_tag(self):
        xml = "<deudaTotal>3450.50</deudaTotal>"
        assert parse_xml_value(xml, "deudaTotal") == "3450.50"

    def test_parse_tag_with_attributes(self):
        xml = '<estado id="4">vencido</estado>'
        assert parse_xml_value(xml, "estado") == "vencido"

    def test_parse_missing_tag_returns_none(self):
        xml = "<deudaTotal>100</deudaTotal>"
        assert parse_xml_value(xml, "noExiste") is None

    def test_parse_empty_tag(self):
        xml = "<deudaTotal></deudaTotal>"
        assert parse_xml_value(xml, "deudaTotal") == ""

    def test_parse_from_full_soap(self, deuda_success_xml):
        assert parse_xml_value(deuda_success_xml, "deudaTotal") == "3450.50"
        assert parse_xml_value(deuda_success_xml, "saldoAnteriorTotal") == "1200.00"
        assert parse_xml_value(deuda_success_xml, "importePorVencer") == "2250.50"

    def test_parse_from_error_response(self, deuda_error_xml):
        assert parse_xml_value(deuda_error_xml, "faultstring") == "Contrato no encontrado"

    def test_parse_from_empty_response(self, deuda_empty_xml):
        assert parse_xml_value(deuda_empty_xml, "deudaTotal") == "0"


# ===================================================================
# Tool Output Schemas (high-level tool invocation with mocked HTTP)
# ===================================================================

class TestGetWaterBalanceTool:
    """Test get_water_balance tool output with mocked API."""

    @pytest.mark.asyncio
    async def test_success_response_schema(self, deuda_success_xml, facturas_success_xml):
        """Successful balance query returns expected data structure."""
        async def mock_api(endpoint, soap_body):
            if "GestionDeuda" in endpoint:
                return deuda_success_xml
            return facturas_success_xml

        with patch.object(water_tools, "call_cea_api", side_effect=mock_api):
            result = await water_tools.get_water_balance.ainvoke({"contrato": "123456"})

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["contrato"] == "123456"
        assert result["data"]["total_deuda"] == 3450.50
        assert "formatted_response" in result

    @pytest.mark.asyncio
    async def test_error_response(self, deuda_error_xml):
        """Error response (contrato not found) returns success=False."""
        async def mock_api(endpoint, soap_body):
            return deuda_error_xml

        with patch.object(water_tools, "call_cea_api", side_effect=mock_api):
            result = await water_tools.get_water_balance.ainvoke({"contrato": "999999"})

        assert result["success"] is False
        assert "error" in result
        assert "formatted_response" in result

    @pytest.mark.asyncio
    async def test_zero_debt(self, deuda_empty_xml):
        """Zero debt contract returns success with 0 total."""
        async def mock_api(endpoint, soap_body):
            return deuda_empty_xml

        with patch.object(water_tools, "call_cea_api", side_effect=mock_api):
            result = await water_tools.get_water_balance.ainvoke({"contrato": "123456"})

        assert result["success"] is True
        assert result["data"]["total_deuda"] == 0.0

    @pytest.mark.asyncio
    async def test_api_exception(self):
        """API exception returns graceful error."""
        async def mock_api(endpoint, soap_body):
            raise ConnectionError("CEA API unreachable")

        with patch.object(water_tools, "call_cea_api", side_effect=mock_api):
            result = await water_tools.get_water_balance.ainvoke({"contrato": "123456"})

        assert result["success"] is False
        assert "error" in result


class TestGetContractDetailsTool:
    """Test get_contract_details tool output with mocked API."""

    @pytest.mark.asyncio
    async def test_success_response_schema(self, contrato_success_xml):
        async def mock_api(endpoint, soap_body):
            return contrato_success_xml

        with patch.object(water_tools, "call_cea_api", side_effect=mock_api):
            result = await water_tools.get_contract_details.ainvoke({"contrato": "123456"})

        assert result["success"] is True
        assert result["data"]["titular"] == "Juan Perez Garcia"
        assert result["data"]["estado"] == "activo"
        assert "Constituyentes" in result["data"]["direccion"]


class TestCreateWaterTicket:
    """Test create_water_ticket tool (no external calls)."""

    def test_creates_ticket_with_folio(self):
        result = water_tools.create_water_ticket.invoke({
            "titulo": "Fuga en mi calle",
            "descripcion": "Hay una fuga de agua frente a mi casa",
        })
        assert result["success"] is True
        assert result["folio"].startswith("CEA-")
        assert result["status"] == "open"

    def test_folio_format(self):
        result = water_tools.create_water_ticket.invoke({
            "titulo": "Test",
            "descripcion": "Test",
        })
        assert re.match(r"CEA-\d{8}-[A-Z0-9]{4}", result["folio"])


class TestGetReceiptLink:
    """Test get_receipt_link tool (no external calls)."""

    def test_returns_download_url(self):
        result = water_tools.get_receipt_link.invoke({"contract_number": "123456"})
        assert result["success"] is True
        assert "123456" in result["download_url"]
        assert result["download_url"].startswith("https://")


class TestHandoffToHuman:
    """Test handoff_to_human tool (no external calls)."""

    def test_returns_confirmation(self):
        result = water_tools.handoff_to_human.invoke({"reason": "Customer upset"})
        assert result["success"] is True
        assert "reason" in result
