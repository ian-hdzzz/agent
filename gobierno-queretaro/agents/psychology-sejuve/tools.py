"""
Gobierno Queretaro - Psychology SEJUVE Agent Tools
Domain-specific tools for psychology/mental health services
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from langchain_core.tools import tool

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================
# Psychology-Specific Tools
# ============================================

@tool
def get_psychology_services() -> dict[str, Any]:
    """
    Obtiene informacion de servicios psicologicos disponibles.

    Returns:
        Lista de servicios y como acceder a ellos
    """
    logger.info("Getting psychology services info")

    services = {
        "atencion_individual": {
            "nombre": "Atencion Psicologica Individual",
            "descripcion": "Sesiones de 50 minutos con psicologo",
            "costo": "Gratuito",
            "requisitos": ["Ser joven de 12-29 anos", "Agendar cita"],
        },
        "terapia_grupal": {
            "nombre": "Terapia Grupal",
            "descripcion": "Grupos de apoyo tematicos",
            "costo": "Gratuito",
            "temas": ["Manejo de ansiedad", "Autoestima", "Duelo"],
        },
        "orientacion_familiar": {
            "nombre": "Orientacion Familiar",
            "descripcion": "Sesiones con familia del joven",
            "costo": "Gratuito",
            "requisitos": ["Joven de 12-29 anos registrado"],
        },
    }

    formatted = """Servicios de Atencion Psicologica SEJUVE:

**Atencion Individual**
- Sesiones de 50 min con psicologo
- Gratuito para jovenes 12-29 anos
- Requiere agendar cita

**Terapia Grupal**
- Grupos de apoyo por tema
- Manejo de ansiedad, autoestima, duelo
- Gratuito

**Orientacion Familiar**
- Sesiones con la familia
- Para mejorar comunicacion

Linea Joven: 442-214-2700
Linea de la Vida (crisis): 800-911-2000"""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": services,
    }


@tool
def get_appointment_availability(tipo_servicio: str = "individual") -> dict[str, Any]:
    """
    Consulta disponibilidad de citas para atencion psicologica.

    Args:
        tipo_servicio: Tipo de servicio (individual, grupal, familiar)

    Returns:
        Horarios disponibles para agendar cita
    """
    logger.info(f"Getting appointment availability for: {tipo_servicio}")

    # Generate simulated available slots
    today = datetime.now()
    available_slots = []

    for i in range(3, 10):
        date = today + timedelta(days=i)
        if date.weekday() < 5:  # Only weekdays
            available_slots.append({
                "fecha": date.strftime("%d/%m/%Y"),
                "horarios": ["10:00", "12:00", "16:00"],
            })

    formatted = f"""Citas disponibles para atencion {tipo_servicio}:

"""
    for slot in available_slots[:3]:
        formatted += f"**{slot['fecha']}:** {', '.join(slot['horarios'])}\n"

    formatted += """
Para agendar, necesito:
- Nombre completo
- Edad
- Telefono de contacto

O llama a Linea Joven: 442-214-2700"""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": {"tipo": tipo_servicio, "slots": available_slots},
    }


@tool
def get_crisis_resources() -> dict[str, Any]:
    """
    Proporciona recursos de ayuda en crisis emocional.

    Returns:
        Lineas de ayuda y recursos de emergencia
    """
    logger.info("Getting crisis resources")

    formatted = """RECURSOS DE AYUDA EN CRISIS:

**Linea de la Vida:** 800-911-2000
(24 horas, todos los dias, gratuita)

**Linea Joven SEJUVE:** 442-214-2700
(Lunes a Viernes 9:00 - 17:00)

**SAPTEL:** 55-5259-8121
(Apoyo emocional 24 horas)

**Emergencias:** 911

No estas solo/a. Hay personas que quieren ayudarte.

Si estas en peligro inmediato, llama al 911."""

    return {
        "success": True,
        "formatted_response": formatted,
        "is_crisis": True,
    }


@tool
def get_addiction_resources() -> dict[str, Any]:
    """
    Proporciona informacion sobre recursos para adicciones.

    Returns:
        Centros de ayuda y lineas de apoyo
    """
    logger.info("Getting addiction resources")

    formatted = """Recursos de apoyo para adicciones:

**Centros de Integracion Juvenil (CIJ)**
- Consulta gratuita
- Tel: 800-911-2000

**Alcoholicos Anonimos Queretaro**
- Grupos de apoyo
- Tel: 442-212-4242

**SEJUVE - Prevencion de Adicciones**
- Orientacion y canalizacion
- Tel: 442-214-2700

El primer paso es pedir ayuda.
No tienes que enfrentar esto solo/a."""

    return {
        "success": True,
        "formatted_response": formatted,
    }


@tool
def get_youth_programs() -> dict[str, Any]:
    """
    Obtiene informacion de programas juveniles.

    Returns:
        Lista de programas y talleres disponibles
    """
    logger.info("Getting youth programs")

    programs = [
        {
            "nombre": "Taller de Manejo del Estres",
            "descripcion": "Tecnicas de relajacion y mindfulness",
            "duracion": "4 sesiones",
            "horario": "Sabados 10:00",
        },
        {
            "nombre": "Grupo de Habilidades Sociales",
            "descripcion": "Comunicacion asertiva y autoestima",
            "duracion": "6 sesiones",
            "horario": "Miercoles 16:00",
        },
        {
            "nombre": "Orientacion Vocacional",
            "descripcion": "Descubre tu vocacion",
            "duracion": "3 sesiones individuales",
            "horario": "Cita previa",
        },
    ]

    formatted = """Programas y talleres SEJUVE:

"""
    for p in programs:
        formatted += f"""**{p['nombre']}**
{p['descripcion']}
Duracion: {p['duracion']} | {p['horario']}

"""

    formatted += "Inscripciones: Linea Joven 442-214-2700"

    return {
        "success": True,
        "formatted_response": formatted,
        "data": programs,
    }


@tool
def create_psychology_ticket(
    titulo: str,
    descripcion: str,
    subcategory: str = "PSI-ATE-001",
    edad: int | None = None,
    urgencia: str = "normal",
    priority: str = "medium",
) -> dict[str, Any]:
    """
    Crea una solicitud de atencion psicologica.

    Args:
        titulo: Titulo breve de la solicitud
        descripcion: Descripcion de la situacion
        subcategory: Codigo de subcategoria
        edad: Edad del solicitante
        urgencia: Nivel de urgencia (normal, urgente, crisis)
        priority: Prioridad (low, medium, high, urgent)

    Returns:
        Informacion de la solicitud creada con folio
    """
    import uuid

    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"PSI-{date_str}-{short_id}"

    # Adjust priority for crisis
    if urgencia == "crisis":
        priority = "urgent"
        subcategory = "PSI-CRI-001"

    logger.info(f"Creating psychology ticket: {folio}, urgency: {urgencia}")

    formatted = f"""**Solicitud de Atencion Creada**

**Folio:** {folio}
**Tipo:** {subcategory}
**Urgencia:** {urgencia}
**Estado:** En proceso

"""
    if urgencia == "crisis":
        formatted += """IMPORTANTE: Tu solicitud es prioritaria.
Un especialista te contactara pronto.

Mientras tanto: Linea de la Vida 800-911-2000"""
    else:
        formatted += """Te contactaremos en los proximos 2 dias habiles.
Linea Joven: 442-214-2700"""

    return {
        "success": True,
        "folio": folio,
        "titulo": titulo,
        "subcategory": subcategory,
        "urgencia": urgencia,
        "priority": priority,
        "status": "open",
        "formatted_response": formatted,
    }


@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """
    Transfiere la conversacion a un profesional de SEJUVE.

    Args:
        reason: Motivo de la transferencia

    Returns:
        Confirmacion de transferencia
    """
    logger.info(f"Handoff to human requested: {reason}")

    is_crisis = any(word in reason.lower() for word in [
        "crisis", "suicid", "autolesion", "emergencia"
    ])

    if is_crisis:
        formatted = """**TRANSFERENCIA URGENTE**

Te estoy conectando con un profesional de inmediato.

Mientras tanto:
**Linea de la Vida: 800-911-2000** (24 horas)

No estas solo/a. Alguien te atendera muy pronto."""
    else:
        formatted = """**Transferencia a Profesional**

Te estoy comunicando con un orientador de SEJUVE.

Por favor espera un momento, alguien te atendera pronto.

Linea Joven: 442-214-2700"""

    return {
        "success": True,
        "reason": reason,
        "is_crisis": is_crisis,
        "formatted_response": formatted,
    }


# ============================================
# Tool Registry
# ============================================

def get_tools() -> list:
    """Get all available tools for the Psychology SEJUVE agent"""
    return [
        get_psychology_services,
        get_appointment_availability,
        get_crisis_resources,
        get_addiction_resources,
        get_youth_programs,
        create_psychology_ticket,
        handoff_to_human,
    ]
