"""Gobierno Queretaro - Social SEDESOQ Agent Tools"""
import logging
from datetime import datetime
from typing import Any
from langchain_core.tools import tool
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@tool
def get_food_programs() -> dict[str, Any]:
    """Obtiene informacion de programas alimentarios."""
    logger.info("Getting food programs")
    formatted = """**Programas Alimentarios SEDESOQ:**

**Desayunos Escolares**
- Para estudiantes de primaria y secundaria
- Escuelas publicas
- Gratuito

**Despensas Familiares**
- Familias en situacion vulnerable
- Estudio socioeconomico requerido
- Entrega mensual

**Comedores Comunitarios**
- Comida a bajo costo
- Ubicados en zonas prioritarias
- $5-10 MXN por comida

Requisitos generales:
- CURP
- Comprobante de domicilio
- Identificacion

Informes: 442-238-5300"""
    return {"success": True, "formatted_response": formatted}

@tool
def get_economic_support_info(tipo: str = "general") -> dict[str, Any]:
    """Obtiene informacion de apoyos economicos.
    Args:
        tipo: Tipo de apoyo (adulto_mayor, discapacidad, madre_soltera, general)
    """
    logger.info(f"Getting economic support info: {tipo}")
    supports = {
        "adulto_mayor": "**Apoyo Adultos Mayores:**\n- 65 anos o mas\n- $1,500 bimestrales\n- CURP e identificacion\n- Comprobante de domicilio",
        "discapacidad": "**Apoyo por Discapacidad:**\n- Certificado medico de discapacidad\n- Estudio socioeconomico\n- $1,200 mensuales",
        "madre_soltera": "**Apoyo Madres Solteras:**\n- Madres trabajadoras\n- Estancia infantil o apoyo economico\n- Comprobante de empleo",
        "general": "**Apoyos Economicos Disponibles:**\n- Adultos mayores (65+)\n- Personas con discapacidad\n- Madres solteras\n- Jefas de familia"
    }
    info = supports.get(tipo.lower().replace(" ", "_"), supports["general"])
    formatted = f"{info}\n\nInformes: 442-238-5300\nsedesoq.gob.mx"
    return {"success": True, "formatted_response": formatted}

@tool
def get_community_programs() -> dict[str, Any]:
    """Obtiene informacion de programas comunitarios."""
    logger.info("Getting community programs")
    formatted = """**Programas Comunitarios:**

**Proyectos Productivos**
- Financiamiento para micro negocios
- Capacitacion incluida
- Hasta $50,000

**Mejoramiento de Vivienda**
- Materiales para autoconstruccion
- Apoyo en zonas marginadas

**Brigadas de Servicios**
- Jornadas medicas
- Cortes de cabello
- Documentacion

Participacion: Acude a tu centro comunitario
Informes: 442-238-5300"""
    return {"success": True, "formatted_response": formatted}

@tool
def check_application_status(curp: str) -> dict[str, Any]:
    """Consulta estado de solicitud de apoyo social."""
    logger.info(f"Checking social application status for CURP: {curp[:4]}...")
    formatted = f"**Estado de Solicitud:**\n\n**CURP:** {curp[:4]}****\n**Programa:** Despensa Familiar\n**Estado:** En revision\n\nTe notificaremos cuando haya actualizacion.\nTel: 442-238-5300"
    return {"success": True, "formatted_response": formatted}

@tool
def create_social_ticket(titulo: str, descripcion: str, subcategory: str = "SOC-CON-001", priority: str = "medium") -> dict[str, Any]:
    """Crea una solicitud de servicio social."""
    import uuid
    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"SOC-{date_str}-{short_id}"
    logger.info(f"Creating social ticket: {folio}")
    formatted = f"**Solicitud Creada**\n\n**Folio:** {folio}\n**Estado:** Abierto\n\nTe contactaremos pronto.\nTel: 442-238-5300"
    return {"success": True, "folio": folio, "titulo": titulo, "subcategory": subcategory, "priority": priority, "status": "open", "formatted_response": formatted}

@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """Transfiere a un agente de SEDESOQ."""
    logger.info(f"Handoff to human: {reason}")
    return {"success": True, "reason": reason, "formatted_response": "**Transferencia a Asesor**\n\nTe comunico con un agente de SEDESOQ.\nTel: 442-238-5300"}

def get_tools() -> list:
    return [get_food_programs, get_economic_support_info, get_community_programs, check_application_status, create_social_ticket, handoff_to_human]
