"""
Gobierno Queretaro - Transport AMEQ Agent Tools
Domain-specific tools for transport/bus services
"""

import logging
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================
# Transport-Specific Tools
# ============================================

@tool
def get_route_info(origen: str, destino: str) -> dict[str, Any]:
    """
    Obtiene informacion de rutas de transporte entre dos puntos.

    Args:
        origen: Punto de origen (colonia, zona o direccion)
        destino: Punto de destino (colonia, zona o direccion)

    Returns:
        Opciones de rutas disponibles con detalles
    """
    logger.info(f"Getting route info from {origen} to {destino}")

    # Simulated route data - in production would query AMEQ API
    routes = [
        {
            "ruta": "Ruta 45",
            "nombre": "Centro - Juriquilla",
            "paradas_principales": ["Centro Historico", "Plaza de Armas", "Juriquilla"],
            "tiempo_estimado": "45 min",
            "frecuencia": "Cada 10 min",
        },
        {
            "ruta": "Ruta 27",
            "nombre": "Satellite - Centro",
            "paradas_principales": ["Satellite", "Alameda", "Centro"],
            "tiempo_estimado": "35 min",
            "frecuencia": "Cada 15 min",
        },
    ]

    formatted = f"""Rutas de {origen} a {destino}:

"""
    for r in routes:
        formatted += f"""**{r['ruta']}** - {r['nombre']}
Tiempo: {r['tiempo_estimado']} | Frecuencia: {r['frecuencia']}
Paradas: {' > '.join(r['paradas_principales'])}

"""

    formatted += "Consulta horarios en tiempo real en la app QroBus."

    return {
        "success": True,
        "formatted_response": formatted,
        "data": {
            "origen": origen,
            "destino": destino,
            "rutas": routes,
        },
    }


@tool
def get_schedule_info(ruta: str) -> dict[str, Any]:
    """
    Obtiene horarios de una ruta de transporte.

    Args:
        ruta: Numero o nombre de la ruta

    Returns:
        Horarios de servicio de la ruta
    """
    logger.info(f"Getting schedule for route: {ruta}")

    schedule = {
        "ruta": ruta,
        "primer_servicio": "05:00",
        "ultimo_servicio": "23:00",
        "frecuencia_hora_pico": "5-8 min",
        "frecuencia_normal": "10-15 min",
        "frecuencia_fin_semana": "15-20 min",
    }

    formatted = f"""Horarios de la {ruta}:

Primer servicio: {schedule['primer_servicio']}
Ultimo servicio: {schedule['ultimo_servicio']}

Frecuencia de paso:
- Hora pico (7-9am, 6-8pm): {schedule['frecuencia_hora_pico']}
- Horario normal: {schedule['frecuencia_normal']}
- Fines de semana: {schedule['frecuencia_fin_semana']}

Para horarios en tiempo real, usa la app QroBus."""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": schedule,
    }


@tool
def get_fare_info() -> dict[str, Any]:
    """
    Obtiene informacion de tarifas de transporte publico.

    Returns:
        Tarifas y descuentos disponibles
    """
    logger.info("Getting fare information")

    fares = {
        "tarifa_regular": 11.00,
        "tarifa_estudiante": 5.50,
        "tarifa_tercera_edad": 5.50,
        "tarifa_discapacidad": "Gratuito",
        "transbordo": "Gratuito con QroBus (30 min)",
    }

    formatted = """Tarifas de transporte publico:

**Tarifa regular:** $11.00 MXN
**Estudiantes:** $5.50 MXN (con credencial vigente)
**Tercera edad:** $5.50 MXN (con credencial INAPAM)
**Discapacidad:** Gratuito (con credencial)

**Transbordo:** Gratuito usando tarjeta QroBus (dentro de 30 min)

Formas de pago: Efectivo o tarjeta QroBus"""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": fares,
    }


@tool
def get_qrobus_info(tipo_consulta: str = "general") -> dict[str, Any]:
    """
    Obtiene informacion sobre la tarjeta QroBus.

    Args:
        tipo_consulta: Tipo de consulta (general, recarga, perdida)

    Returns:
        Informacion sobre tarjeta QroBus
    """
    logger.info(f"Getting QroBus info: {tipo_consulta}")

    if tipo_consulta == "recarga":
        formatted = """Puntos de recarga QroBus:

- Tiendas OXXO y 7-Eleven
- Farmacias Guadalajara y del Ahorro
- Centros de atencion AMEQ
- Estaciones de transferencia
- App QroBus (con tarjeta bancaria)

Monto minimo de recarga: $20.00 MXN"""

    elif tipo_consulta == "perdida":
        formatted = """Para reportar tarjeta QroBus perdida:

1. Acude a un centro de atencion AMEQ
2. Presenta identificacion oficial
3. Se bloqueara la tarjeta perdida
4. Costo de reposicion: $30.00 MXN
5. El saldo se transfiere a la nueva tarjeta

Centros: Terminal de autobuses, Plaza de la Tecnologia"""

    else:
        formatted = """Tarjeta QroBus:

- Costo inicial: $30.00 MXN (incluye $10 de saldo)
- Beneficios: Transbordos gratis, descuentos
- Vigencia: Indefinida mientras tenga saldo
- Recarga en OXXO, 7-Eleven, farmacias

Para obtenerla, acude a cualquier centro de atencion AMEQ."""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": {"tipo_consulta": tipo_consulta},
    }


@tool
def create_transport_ticket(
    titulo: str,
    descripcion: str,
    subcategory: str = "TRA-RUT-001",
    numero_ruta: str | None = None,
    numero_unidad: str | None = None,
    ubicacion: str | None = None,
    priority: str = "medium",
) -> dict[str, Any]:
    """
    Crea un ticket de reporte de transporte.

    Args:
        titulo: Titulo breve del reporte
        descripcion: Descripcion detallada del problema
        subcategory: Codigo de subcategoria (TRA-RUT-001, TRA-UNI-001, etc.)
        numero_ruta: Numero de ruta involucrada
        numero_unidad: Numero economico de la unidad
        ubicacion: Ubicacion del incidente
        priority: Prioridad (low, medium, high, urgent)

    Returns:
        Informacion del ticket creado con folio
    """
    import uuid

    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"TRA-{date_str}-{short_id}"

    logger.info(f"Creating transport ticket: {folio}")

    formatted = f"""**Reporte de Transporte Creado**

**Folio:** {folio}
**Asunto:** {titulo}
**Prioridad:** {priority}
**Estado:** Abierto

Tu reporte sera atendido por el area de transporte.
Para seguimiento llama al 442-214-3800."""

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
    Transfiere la conversacion a un agente humano de AMEQ.

    Args:
        reason: Motivo de la transferencia

    Returns:
        Confirmacion de transferencia
    """
    logger.info(f"Handoff to human requested: {reason}")

    return {
        "success": True,
        "reason": reason,
        "formatted_response": """**Transferencia a Asesor**

Te estoy comunicando con un agente de atencion al usuario.

Por favor espera un momento, alguien te atendera pronto.

Telefono directo: 442-214-3800""",
    }


# ============================================
# Tool Registry
# ============================================

def get_tools() -> list:
    """Get all available tools for the Transport AMEQ agent"""
    return [
        get_route_info,
        get_schedule_info,
        get_fare_info,
        get_qrobus_info,
        create_transport_ticket,
        handoff_to_human,
    ]
