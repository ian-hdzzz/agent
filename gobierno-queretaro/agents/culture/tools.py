"""Gobierno Queretaro - Culture Agent Tools"""
import logging
from datetime import datetime
from typing import Any
from langchain_core.tools import tool
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@tool
def get_cultural_events(tipo: str = "todos", fecha: str | None = None) -> dict[str, Any]:
    """Obtiene eventos culturales disponibles.
    Args:
        tipo: Tipo de evento (concierto, exposicion, teatro, festival, todos)
        fecha: Fecha especifica (opcional)
    Returns:
        Lista de eventos culturales
    """
    logger.info(f"Getting cultural events: {tipo}, {fecha}")
    events = [
        {"nombre": "Concierto de la Orquesta Filarmonica", "fecha": "Sabado 15", "lugar": "Teatro de la Republica", "costo": "Entrada libre"},
        {"nombre": "Exposicion 'Arte Contemporaneo'", "fecha": "Todo el mes", "lugar": "Museo de Arte", "costo": "$50"},
        {"nombre": "Festival de Danza Folklorica", "fecha": "Domingo 16", "lugar": "Jardin Zenea", "costo": "Entrada libre"},
    ]
    formatted = "Proximos eventos culturales:\n\n"
    for e in events:
        formatted += f"**{e['nombre']}**\n{e['fecha']} | {e['lugar']}\n{e['costo']}\n\n"
    formatted += "Mas eventos en cultura.queretaro.gob.mx"
    return {"success": True, "formatted_response": formatted, "data": events}

@tool
def get_museum_info(museo: str = "todos") -> dict[str, Any]:
    """Obtiene informacion de museos.
    Args:
        museo: Nombre del museo o 'todos'
    Returns:
        Informacion del museo
    """
    logger.info(f"Getting museum info: {museo}")
    museums = [
        {"nombre": "Museo Regional", "direccion": "Corregidora Sur 3", "horario": "Mar-Dom 10:00-18:00", "costo": "$85"},
        {"nombre": "Museo de Arte", "direccion": "Allende Sur 14", "horario": "Mar-Dom 10:00-18:00", "costo": "$50"},
    ]
    formatted = "Museos en Queretaro:\n\n"
    for m in museums:
        formatted += f"**{m['nombre']}**\n{m['direccion']}\nHorario: {m['horario']}\nCosto: {m['costo']}\n\n"
    return {"success": True, "formatted_response": formatted, "data": museums}

@tool
def get_workshops_info(disciplina: str = "todas") -> dict[str, Any]:
    """Obtiene informacion de talleres culturales.
    Args:
        disciplina: Disciplina artistica (musica, danza, pintura, teatro, todas)
    Returns:
        Lista de talleres disponibles
    """
    logger.info(f"Getting workshops: {disciplina}")
    workshops = [
        {"nombre": "Taller de Pintura al Oleo", "horario": "Sabados 10:00", "costo": "Gratuito", "requisitos": "Mayores de 15 anos"},
        {"nombre": "Clase de Guitarra", "horario": "Miercoles 17:00", "costo": "Gratuito", "requisitos": "Traer instrumento"},
    ]
    formatted = "Talleres disponibles:\n\n"
    for w in workshops:
        formatted += f"**{w['nombre']}**\n{w['horario']} | {w['costo']}\n{w['requisitos']}\n\n"
    formatted += "Inscripciones en Casa de Cultura"
    return {"success": True, "formatted_response": formatted, "data": workshops}

@tool
def create_culture_ticket(titulo: str, descripcion: str, subcategory: str = "CUL-INF-001", priority: str = "low") -> dict[str, Any]:
    """Crea una solicitud de servicio cultural."""
    import uuid
    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"CUL-{date_str}-{short_id}"
    logger.info(f"Creating culture ticket: {folio}")
    formatted = f"**Solicitud Creada**\n\n**Folio:** {folio}\n**Estado:** Abierto\n\nTe contactaremos pronto.\nTel: 442-251-9850"
    return {"success": True, "folio": folio, "titulo": titulo, "subcategory": subcategory, "priority": priority, "status": "open", "formatted_response": formatted}

@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """Transfiere a un agente humano de Cultura."""
    logger.info(f"Handoff to human: {reason}")
    return {"success": True, "reason": reason, "formatted_response": "**Transferencia a Asesor**\n\nTe comunico con un agente de Cultura.\nTel: 442-251-9850"}

def get_tools() -> list:
    return [get_cultural_events, get_museum_info, get_workshops_info, create_culture_ticket, handoff_to_human]
