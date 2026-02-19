"""Gobierno Queretaro - Labor CCLQ Agent Tools"""
import logging
from datetime import datetime, timedelta
from typing import Any
from langchain_core.tools import tool
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@tool
def get_conciliation_info() -> dict[str, Any]:
    """Obtiene informacion sobre el proceso de conciliacion laboral."""
    logger.info("Getting conciliation info")
    formatted = """**Proceso de Conciliacion Laboral**

La conciliacion es OBLIGATORIA antes de iniciar un juicio laboral.

**Que necesitas:**
- Identificacion oficial
- Contrato de trabajo (si tienes)
- Recibos de nomina
- Datos del patron (RFC, domicilio)

**Proceso:**
1. Agendar cita en CCLQ
2. Audiencia de conciliacion (45 min aprox)
3. Si hay acuerdo, se firma convenio
4. Si no hay acuerdo, se emite constancia para juicio

**Servicio gratuito**
Tel: 442-238-5600"""
    return {"success": True, "formatted_response": formatted}

@tool
def get_labor_rights_info(tema: str = "general") -> dict[str, Any]:
    """Obtiene orientacion sobre derechos laborales basicos.
    Args:
        tema: Tema de consulta (despido, salario, aguinaldo, vacaciones, general)
    """
    logger.info(f"Getting labor rights info: {tema}")
    topics = {
        "despido": "En caso de despido injustificado, tienes derecho a: 3 meses de salario + 20 dias por ano + salarios caidos. La conciliacion es obligatoria antes de demandar.",
        "salario": "El salario minimo en Queretaro es $248.93 diarios (2024). Los pagos deben ser semanales o quincenales como maximo.",
        "aguinaldo": "Derecho a minimo 15 dias de salario antes del 20 de diciembre. Proporcional si trabajaste menos de un ano.",
        "vacaciones": "6 dias de vacaciones al cumplir 1 ano, aumenta 2 dias por cada ano hasta 12. Despues aumenta 2 dias por cada 5 anos.",
        "general": "Los derechos laborales basicos incluyen: salario justo, jornada maxima de 8 horas, descanso semanal, vacaciones, aguinaldo, seguridad social."
    }
    info = topics.get(tema.lower(), topics["general"])
    formatted = f"**Orientacion sobre {tema}:**\n\n{info}\n\nPara asesoria especifica, agenda cita en CCLQ.\nTel: 442-238-5600"
    return {"success": True, "formatted_response": formatted}

@tool
def get_appointment_availability() -> dict[str, Any]:
    """Obtiene disponibilidad de citas para conciliacion."""
    logger.info("Getting appointment availability")
    today = datetime.now()
    slots = []
    for i in range(5, 12):
        date = today + timedelta(days=i)
        if date.weekday() < 5:
            slots.append({"fecha": date.strftime("%d/%m/%Y"), "horarios": ["9:00", "11:00", "13:00"]})
    formatted = "**Citas disponibles:**\n\n"
    for slot in slots[:3]:
        formatted += f"{slot['fecha']}: {', '.join(slot['horarios'])}\n"
    formatted += "\nPara agendar: 442-238-5600 o en linea"
    return {"success": True, "formatted_response": formatted, "data": slots}

@tool
def check_case_status(numero_expediente: str) -> dict[str, Any]:
    """Consulta estado de expediente laboral."""
    logger.info(f"Checking case status: {numero_expediente}")
    formatted = f"**Expediente {numero_expediente}**\n\n**Estado:** En proceso de conciliacion\n**Proxima audiencia:** Pendiente de programar\n\nPara mas detalles: 442-238-5600"
    return {"success": True, "formatted_response": formatted}

@tool
def create_labor_ticket(titulo: str, descripcion: str, subcategory: str = "LAB-ORI-001", priority: str = "medium") -> dict[str, Any]:
    """Crea una solicitud de servicio laboral."""
    import uuid
    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"LAB-{date_str}-{short_id}"
    logger.info(f"Creating labor ticket: {folio}")
    formatted = f"**Solicitud Creada**\n\n**Folio:** {folio}\n**Estado:** Abierto\n\nTe contactaremos pronto.\nTel: 442-238-5600"
    return {"success": True, "folio": folio, "titulo": titulo, "subcategory": subcategory, "priority": priority, "status": "open", "formatted_response": formatted}

@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """Transfiere a un agente del CCLQ."""
    logger.info(f"Handoff to human: {reason}")
    return {"success": True, "reason": reason, "formatted_response": "**Transferencia a Asesor**\n\nTe comunico con un conciliador.\nTel: 442-238-5600"}

def get_tools() -> list:
    return [get_conciliation_info, get_labor_rights_info, get_appointment_availability, check_case_status, create_labor_ticket, handoff_to_human]
