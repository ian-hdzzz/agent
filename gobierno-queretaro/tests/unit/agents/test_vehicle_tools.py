"""
Unit tests for agents.vehicles.tools

Tests vehicle tool outputs match expected schemas. All tools use mocked/simulated
data so no external services are needed.
"""

import importlib
import importlib.util
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Create a mock config module and register it as the package-relative import
# that vehicles/tools.py expects (from .config import get_settings)
_mock_settings = MagicMock()
_config_mod = types.ModuleType("agents.vehicles.config")
_config_mod.get_settings = lambda: _mock_settings  # type: ignore
sys.modules["agents.vehicles.config"] = _config_mod

# Create the parent package modules so relative imports work
if "agents" not in sys.modules:
    _agents_pkg = types.ModuleType("agents")
    _agents_pkg.__path__ = [str(PROJECT_ROOT / "agents")]  # type: ignore
    sys.modules["agents"] = _agents_pkg

if "agents.vehicles" not in sys.modules:
    _vehicles_pkg = types.ModuleType("agents.vehicles")
    _vehicles_pkg.__path__ = [str(PROJECT_ROOT / "agents" / "vehicles")]  # type: ignore
    _vehicles_pkg.config = _config_mod  # type: ignore
    sys.modules["agents.vehicles"] = _vehicles_pkg

# Now import the tools module using normal import machinery
_tools_path = PROJECT_ROOT / "agents" / "vehicles" / "tools.py"
_spec = importlib.util.spec_from_file_location(
    "agents.vehicles.tools",
    _tools_path,
    submodule_search_locations=[],
)
vehicle_tools = importlib.util.module_from_spec(_spec)
sys.modules["agents.vehicles.tools"] = vehicle_tools
_spec.loader.exec_module(vehicle_tools)


# ===================================================================
# get_vehicle_debt
# ===================================================================

class TestGetVehicleDebt:
    """Test vehicle debt query tool."""

    def test_success_schema(self):
        result = vehicle_tools.get_vehicle_debt.invoke({"placa": "QRO-1234"})
        assert result["success"] is True
        assert "data" in result
        assert "formatted_response" in result

    def test_data_fields(self):
        result = vehicle_tools.get_vehicle_debt.invoke({"placa": "abc-999"})
        data = result["data"]
        assert "placa" in data
        assert "tenencia_2024" in data
        assert "derechos_control" in data
        assert "multas" in data
        assert "total" in data

    def test_placa_uppercased(self):
        result = vehicle_tools.get_vehicle_debt.invoke({"placa": "qro-xyz"})
        assert result["data"]["placa"] == "QRO-XYZ"

    def test_total_equals_sum(self):
        result = vehicle_tools.get_vehicle_debt.invoke({"placa": "QRO-1234"})
        data = result["data"]
        expected_total = (
            data["tenencia_2024"]
            + data["tenencia_2023"]
            + data["derechos_control"]
            + data["multas"]
        )
        assert data["total"] == expected_total


# ===================================================================
# get_plate_requirements
# ===================================================================

class TestGetPlateRequirements:
    """Test plate requirement lookup tool."""

    @pytest.mark.parametrize("tipo", ["alta", "cambio", "reposicion", "baja"])
    def test_valid_types_succeed(self, tipo):
        result = vehicle_tools.get_plate_requirements.invoke({"tipo_tramite": tipo})
        assert result["success"] is True
        assert "data" in result
        assert "requisitos" in result["data"]
        assert len(result["data"]["requisitos"]) > 0

    def test_invalid_type_fails(self):
        result = vehicle_tools.get_plate_requirements.invoke({"tipo_tramite": "inexistente"})
        assert result["success"] is False
        assert "formatted_response" in result

    def test_case_insensitive(self):
        result = vehicle_tools.get_plate_requirements.invoke({"tipo_tramite": "Alta"})
        assert result["success"] is True

    def test_data_contains_costo(self):
        result = vehicle_tools.get_plate_requirements.invoke({"tipo_tramite": "alta"})
        assert "costo" in result["data"]

    def test_data_contains_tiempo(self):
        result = vehicle_tools.get_plate_requirements.invoke({"tipo_tramite": "alta"})
        assert "tiempo" in result["data"]


# ===================================================================
# get_verification_info
# ===================================================================

class TestGetVerificationInfo:
    """Test vehicle verification info tool."""

    def test_success_schema(self):
        result = vehicle_tools.get_verification_info.invoke({"placa": "QRO-1234"})
        assert result["success"] is True
        assert "data" in result
        assert "formatted_response" in result

    def test_placa_uppercased(self):
        result = vehicle_tools.get_verification_info.invoke({"placa": "abc-xyz"})
        assert result["data"]["placa"] == "ABC-XYZ"

    @pytest.mark.parametrize("last_char,expected_period", [
        ("1", "Enero y Febrero"),
        ("5", "Mayo y Junio"),
        ("0", "Octubre y Noviembre"),
    ])
    def test_period_by_last_digit(self, last_char, expected_period):
        placa = f"QRO-{last_char}"
        result = vehicle_tools.get_verification_info.invoke({"placa": placa})
        assert result["data"]["periodo"] == expected_period

    def test_non_digit_last_char_defaults_to_zero(self):
        result = vehicle_tools.get_verification_info.invoke({"placa": "QRO-A"})
        assert result["data"]["periodo"] == "Octubre y Noviembre"

    def test_costo_is_numeric(self):
        result = vehicle_tools.get_verification_info.invoke({"placa": "QRO-1"})
        assert isinstance(result["data"]["costo"], (int, float))


# ===================================================================
# get_fines_info
# ===================================================================

class TestGetFinesInfo:
    """Test vehicle fines query tool."""

    def test_success_schema(self):
        result = vehicle_tools.get_fines_info.invoke({"placa": "QRO-1234"})
        assert result["success"] is True
        assert "data" in result

    def test_no_fines_response(self):
        result = vehicle_tools.get_fines_info.invoke({"placa": "QRO-1234"})
        assert result["data"]["infracciones"] == []
        assert result["data"]["total"] == 0.0

    def test_placa_uppercased(self):
        result = vehicle_tools.get_fines_info.invoke({"placa": "abc-999"})
        assert result["data"]["placa"] == "ABC-999"


# ===================================================================
# create_vehicle_ticket
# ===================================================================

class TestCreateVehicleTicket:
    """Test vehicle ticket creation tool."""

    def test_creates_ticket(self):
        result = vehicle_tools.create_vehicle_ticket.invoke({
            "titulo": "Problema con placas",
            "descripcion": "Mis placas se daniaron con la lluvia",
        })
        assert result["success"] is True
        assert result["status"] == "open"
        assert "folio" in result

    def test_folio_format(self):
        result = vehicle_tools.create_vehicle_ticket.invoke({
            "titulo": "Test",
            "descripcion": "Test",
        })
        assert re.match(r"VEH-\d{8}-[A-Z0-9]{4}", result["folio"])

    def test_custom_priority(self):
        result = vehicle_tools.create_vehicle_ticket.invoke({
            "titulo": "Urgente",
            "descripcion": "Urgente",
            "priority": "high",
        })
        assert result["priority"] == "high"


# ===================================================================
# handoff_to_human
# ===================================================================

class TestHandoffToHuman:
    """Test vehicle handoff to human tool."""

    def test_returns_confirmation(self):
        result = vehicle_tools.handoff_to_human.invoke({"reason": "Complex case"})
        assert result["success"] is True
        assert result["reason"] == "Complex case"
        assert "formatted_response" in result


# ===================================================================
# get_tools registry
# ===================================================================

class TestToolRegistry:
    """Test that the tool registry returns all expected tools."""

    def test_tool_count(self):
        tools = vehicle_tools.get_tools()
        assert len(tools) == 6

    def test_tool_names(self):
        tools = vehicle_tools.get_tools()
        names = {t.name for t in tools}
        expected = {
            "get_vehicle_debt",
            "get_plate_requirements",
            "get_verification_info",
            "get_fines_info",
            "create_vehicle_ticket",
            "handoff_to_human",
        }
        assert names == expected
