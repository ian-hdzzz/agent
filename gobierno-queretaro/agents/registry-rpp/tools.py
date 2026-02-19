"""Gobierno Queretaro - Registry RPP Agent Tools"""
import logging
from datetime import datetime
from typing import Any
from langchain_core.tools import tool
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@tool
def get_certificate_info(tipo: str) -> dict[str, Any]:
    """Obtiene informacion sobre certificados del RPP.
    Args:
        tipo: Tipo de certificado (libertad_gravamen, propiedad, no_inscripcion)
    Returns:
        Requisitos y costos del certificado
    """
    logger.info(f"Getting certificate info: {tipo}")
    certificates = {
        "libertad_gravamen": {"nombre": "Certificado de Libertad de Gravamen", "costo": "$850", "requisitos": ["Folio real o datos del inmueble", "Identificacion oficial", "Pago de derechos"], "tiempo": "3-5 dias habiles"},
        "propiedad": {"nombre": "Certificado de Propiedad", "costo": "$650", "requisitos": ["Folio real", "Identificacion oficial", "Pago de derechos"], "tiempo": "3-5 dias habiles"},
        "no_inscripcion": {"nombre": "Certificado de No Inscripcion", "costo": "$450", "requisitos": ["Datos del inmueble", "Identificacion oficial", "Pago de derechos"], "tiempo": "5-7 dias habiles"},
    }
    cert = certificates.get(tipo.lower().replace(" ", "_"))
    if not cert:
        return {"success": False, "formatted_response": f"Tipo '{tipo}' no reconocido. Opciones: libertad de gravamen, propiedad, no inscripcion"}
    formatted = f"**{cert['nombre']}**\n\n**Costo:** {cert['costo']}\n**Tiempo:** {cert['tiempo']}\n\n**Requisitos:**\n"
    for r in cert['requisitos']: formatted += f"- {r}\n"
    formatted += "\nTramite en oficinas RPP o en linea: rpp.queretaro.gob.mx"
    return {"success": True, "formatted_response": formatted, "data": cert}

@tool
def get_registration_requirements(tipo: str) -> dict[str, Any]:
    """Obtiene requisitos para inscripcion en RPP.
    Args:
        tipo: Tipo de inscripcion (compraventa, hipoteca, escritura)
    Returns:
        Requisitos y proceso
    """
    logger.info(f"Getting registration requirements: {tipo}")
    registrations = {
        "compraventa": {"nombre": "Inscripcion de Compraventa", "documentos": ["Escritura publica", "Certificado de libertad de gravamen", "Pago de impuestos (ISR, ISAI)", "Identificaciones"], "costo": "Variable segun valor"},
        "hipoteca": {"nombre": "Inscripcion de Hipoteca", "documentos": ["Escritura de hipoteca", "Certificado de libertad de gravamen", "Avaluo vigente", "Identificaciones"], "costo": "Variable segun monto"},
    }
    reg = registrations.get(tipo.lower())
    if not reg:
        return {"success": False, "formatted_response": f"Tipo '{tipo}' no reconocido. Opciones: compraventa, hipoteca"}
    formatted = f"**{reg['nombre']}**\n\n**Costo:** {reg['costo']}\n\n**Documentos:**\n"
    for d in reg['documentos']: formatted += f"- {d}\n"
    formatted += "\nRecomendamos consultar con notario publico."
    return {"success": True, "formatted_response": formatted, "data": reg}

@tool
def check_registry_status(numero_tramite: str) -> dict[str, Any]:
    """Consulta estado de tramite en RPP.
    Args:
        numero_tramite: Numero de tramite a consultar
    Returns:
        Estado actual del tramite
    """
    logger.info(f"Checking registry status: {numero_tramite}")
    # Simulated
    formatted = f"**Estado del tramite {numero_tramite}**\n\n**Estado:** En proceso\n**Etapa:** Revision documental\n**Fecha estimada:** 5 dias habiles\n\nPara mas detalles: 442-238-5400"
    return {"success": True, "formatted_response": formatted, "data": {"numero": numero_tramite, "estado": "en_proceso"}}

@tool
def create_registry_ticket(titulo: str, descripcion: str, subcategory: str = "RPP-CON-001", priority: str = "medium") -> dict[str, Any]:
    """Crea una solicitud de servicio en RPP."""
    import uuid
    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"RPP-{date_str}-{short_id}"
    logger.info(f"Creating registry ticket: {folio}")
    formatted = f"**Solicitud Creada**\n\n**Folio:** {folio}\n**Estado:** Abierto\n\nTe contactaremos pronto.\nTel: 442-238-5400"
    return {"success": True, "folio": folio, "titulo": titulo, "subcategory": subcategory, "priority": priority, "status": "open", "formatted_response": formatted}

@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """Transfiere a un agente del RPP."""
    logger.info(f"Handoff to human: {reason}")
    return {"success": True, "reason": reason, "formatted_response": "**Transferencia a Asesor**\n\nTe comunico con un agente del RPP.\nTel: 442-238-5400"}

def get_tools() -> list:
    return [get_certificate_info, get_registration_requirements, check_registry_status, create_registry_ticket, handoff_to_human]
