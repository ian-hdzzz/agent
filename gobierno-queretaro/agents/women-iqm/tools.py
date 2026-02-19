"""
Gobierno Queretaro - Women IQM Agent Tools
Domain-specific tools for women's services
"""

import logging
from datetime import datetime
from typing import Any
from langchain_core.tools import tool
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@tool
def get_violence_resources() -> dict[str, Any]:
    """
    Proporciona recursos de ayuda en situaciones de violencia.

    Returns:
        Lineas de ayuda y recursos de emergencia
    """
    logger.info("Getting violence resources")

    formatted = """RECURSOS DE AYUDA - VIOLENCIA:

**Emergencias:** 911
**Linea Violeta:** 800-670-3737 (24 horas)

**IQM - Instituto Queretano de la Mujer**
Tel: 442-214-5700
Atencion legal y psicologica gratuita

**Refugios temporales** disponibles
(informacion confidencial via Linea Violeta)

No estas sola. Hay personas que quieren ayudarte."""

    return {
        "success": True,
        "formatted_response": formatted,
        "is_emergency": True,
    }


@tool
def get_empowerment_programs() -> dict[str, Any]:
    """
    Obtiene programas de empoderamiento economico para mujeres.

    Returns:
        Lista de programas disponibles
    """
    logger.info("Getting empowerment programs")

    formatted = """Programas de Empoderamiento Economico:

**Mujer Emprendedora**
- Creditos desde $10,000 hasta $50,000
- Tasa preferencial
- Capacitacion incluida

**Capacitacion Laboral**
- Cursos gratuitos certificados
- Oficios y habilidades tecnicas

**Bolsa de Trabajo IQM**
- Vacantes con empresas aliadas
- Horarios flexibles

Informes: 442-214-5700
www.iqm.gob.mx"""

    return {
        "success": True,
        "formatted_response": formatted,
    }


@tool
def get_legal_services() -> dict[str, Any]:
    """
    Obtiene informacion de servicios juridicos para mujeres.

    Returns:
        Servicios legales disponibles
    """
    logger.info("Getting legal services")

    formatted = """Servicios Juridicos IQM:

**Asesoria Legal Gratuita**
- Pension alimenticia
- Custodia de hijos
- Divorcio
- Ordenes de proteccion

**Requisitos:**
- Identificacion oficial
- Documentos del caso (si tiene)

**Horario de atencion:**
Lunes a Viernes 9:00 - 14:00

Agenda cita: 442-214-5700"""

    return {
        "success": True,
        "formatted_response": formatted,
    }


@tool
def get_health_services() -> dict[str, Any]:
    """
    Obtiene servicios de salud disponibles para mujeres.

    Returns:
        Servicios de salud y bienestar
    """
    logger.info("Getting health services")

    formatted = """Servicios de Salud IQM:

**Atencion Psicologica**
- Terapia individual
- Grupos de apoyo
- Gratuita

**Salud Reproductiva**
- Informacion y orientacion
- Canalizacion a servicios de salud

**Programas de Bienestar**
- Talleres de autoestima
- Manejo del estres

Citas: 442-214-5700"""

    return {
        "success": True,
        "formatted_response": formatted,
    }


@tool
def create_women_ticket(
    titulo: str,
    descripcion: str,
    subcategory: str = "IQM-INF-001",
    es_urgente: bool = False,
    priority: str = "medium",
) -> dict[str, Any]:
    """
    Crea una solicitud de atencion en IQM.

    Args:
        titulo: Titulo breve de la solicitud
        descripcion: Descripcion de la situacion
        subcategory: Codigo de subcategoria
        es_urgente: Si es situacion de violencia/urgencia
        priority: Prioridad

    Returns:
        Informacion de la solicitud creada
    """
    import uuid

    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"IQM-{date_str}-{short_id}"

    if es_urgente:
        priority = "urgent"

    logger.info(f"Creating women services ticket: {folio}")

    formatted = f"""**Solicitud de Atencion Creada**

**Folio:** {folio}
**Prioridad:** {priority}
**Estado:** En proceso

"""
    if es_urgente:
        formatted += """ATENCION PRIORITARIA
Te contactaremos lo antes posible.

Emergencias: 911
Linea Violeta: 800-670-3737"""
    else:
        formatted += """Te contactaremos en 24-48 horas.
Tel: 442-214-5700"""

    return {
        "success": True,
        "folio": folio,
        "titulo": titulo,
        "subcategory": subcategory,
        "priority": priority,
        "status": "open",
        "formatted_response": formatted,
    }


@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """
    Transfiere la conversacion a una especialista del IQM.

    Args:
        reason: Motivo de la transferencia

    Returns:
        Confirmacion de transferencia
    """
    logger.info(f"Handoff to human requested: {reason}")

    is_emergency = any(word in reason.lower() for word in [
        "violencia", "golpe", "amenaza", "peligro", "emergencia"
    ])

    if is_emergency:
        formatted = """**TRANSFERENCIA URGENTE**

Te conecto con una especialista de inmediato.

Mientras tanto:
**Emergencias: 911**
**Linea Violeta: 800-670-3737**

No estas sola."""
    else:
        formatted = """**Transferencia a Especialista**

Te estoy comunicando con una asesora del IQM.

Por favor espera, alguien te atendera pronto.

Tel: 442-214-5700"""

    return {
        "success": True,
        "reason": reason,
        "is_emergency": is_emergency,
        "formatted_response": formatted,
    }


def get_tools() -> list:
    """Get all available tools for the Women IQM agent"""
    return [
        get_violence_resources,
        get_empowerment_programs,
        get_legal_services,
        get_health_services,
        create_women_ticket,
        handoff_to_human,
    ]
