"""Gobierno Queretaro - Citizen Attention Agent Tools"""
import logging
from datetime import datetime
from typing import Any
from langchain_core.tools import tool
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@tool
def get_government_directory() -> dict[str, Any]:
    """Obtiene directorio de dependencias del gobierno."""
    logger.info("Getting government directory")
    formatted = """**Directorio de Dependencias:**

**Agua y Drenaje (CEA)**
Tel: 442-238-8200

**Transporte (AMEQ)**
Tel: 442-214-3800

**Educacion (USEBEQ)**
Tel: 442-238-5700

**Vivienda (IVEQ)**
Tel: 442-238-5200

**Programas Sociales (SEDESOQ)**
Tel: 442-238-5300

**Atencion a la Mujer (IQM)**
Tel: 442-214-5700
Linea Violeta: 800-670-3737

**Juventud (SEJUVE)**
Tel: 442-214-2700

**Linea Ciudadana General**
Tel: 442-238-5000"""
    return {"success": True, "formatted_response": formatted}

@tool
def get_service_info(servicio: str) -> dict[str, Any]:
    """Obtiene informacion sobre un servicio gubernamental.
    Args:
        servicio: Nombre del servicio a consultar
    """
    logger.info(f"Getting service info: {servicio}")
    formatted = f"""Para informacion sobre "{servicio}", te recomiendo:

1. Consultar el portal: queretaro.gob.mx
2. Llamar a Linea Ciudadana: 442-238-5000
3. Acudir a ventanilla unica en Centro Civico

Si me dices mas detalles, puedo canalizarte a la dependencia correcta."""
    return {"success": True, "formatted_response": formatted}

@tool
def get_office_hours() -> dict[str, Any]:
    """Obtiene horarios de atencion de oficinas gubernamentales."""
    logger.info("Getting office hours")
    formatted = """**Horarios de Atencion:**

**Ventanilla Unica (Centro Civico)**
Lunes a Viernes: 8:00 - 15:00

**Linea Ciudadana (442-238-5000)**
Lunes a Viernes: 8:00 - 20:00
Sabados: 9:00 - 14:00

**Modulos de Atencion**
Lunes a Viernes: 9:00 - 15:00

**Emergencias (911)**
24 horas, todos los dias"""
    return {"success": True, "formatted_response": formatted}

@tool
def create_citizen_ticket(titulo: str, descripcion: str, tipo: str = "informacion", subcategory: str = "ATC-INF-001", priority: str = "medium") -> dict[str, Any]:
    """Crea un ticket de atencion ciudadana.
    Args:
        titulo: Titulo breve
        descripcion: Descripcion detallada
        tipo: Tipo (informacion, queja, sugerencia)
        subcategory: Subcategoria
        priority: Prioridad
    """
    import uuid
    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"ATC-{date_str}-{short_id}"

    # Adjust subcategory based on type
    if tipo == "queja": subcategory = "ATC-QUE-001"
    elif tipo == "sugerencia": subcategory = "ATC-SUG-001"

    logger.info(f"Creating citizen ticket: {folio}")
    formatted = f"**Solicitud Ciudadana Creada**\n\n**Folio:** {folio}\n**Tipo:** {tipo.capitalize()}\n**Estado:** Abierto\n\nDaremos seguimiento a tu solicitud.\nLinea Ciudadana: 442-238-5000"
    return {"success": True, "folio": folio, "titulo": titulo, "tipo": tipo, "subcategory": subcategory, "priority": priority, "status": "open", "formatted_response": formatted}

@tool
def check_ticket_status(folio: str) -> dict[str, Any]:
    """Consulta estado de un ticket ciudadano."""
    logger.info(f"Checking ticket status: {folio}")
    formatted = f"**Estado del Folio {folio}:**\n\n**Estado:** En proceso\n**Dependencia:** Por asignar\n**Fecha de creacion:** Reciente\n\nPara seguimiento: 442-238-5000"
    return {"success": True, "formatted_response": formatted}

@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """Transfiere a un agente de Atencion Ciudadana."""
    logger.info(f"Handoff to human: {reason}")
    return {"success": True, "reason": reason, "formatted_response": "**Transferencia a Asesor**\n\nTe comunico con un agente de Atencion Ciudadana.\nLinea Ciudadana: 442-238-5000"}

def get_tools() -> list:
    return [get_government_directory, get_service_info, get_office_hours, create_citizen_ticket, check_ticket_status, handoff_to_human]
