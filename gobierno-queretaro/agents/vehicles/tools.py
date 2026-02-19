"""
Gobierno Queretaro - Vehicles Agent Tools
Domain-specific tools for vehicle registration services
"""

import logging
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================
# Vehicles-Specific Tools
# ============================================

@tool
def get_vehicle_debt(placa: str) -> dict[str, Any]:
    """
    Consulta adeudos de un vehiculo por placa.

    Args:
        placa: Numero de placa del vehiculo

    Returns:
        Desglose de adeudos: tenencia, derechos, multas
    """
    logger.info(f"Getting vehicle debt for plate: {placa}")

    # Simulated debt data
    debt_data = {
        "placa": placa.upper(),
        "tenencia_2024": 1850.00,
        "tenencia_2023": 0.00,
        "derechos_control": 450.00,
        "multas": 0.00,
        "total": 2300.00,
    }

    formatted = f"""Adeudos del vehiculo {placa.upper()}:

**Tenencia 2024:** ${debt_data['tenencia_2024']:.2f}
**Tenencia 2023:** ${debt_data['tenencia_2023']:.2f} (Pagada)
**Derechos de control:** ${debt_data['derechos_control']:.2f}
**Multas:** ${debt_data['multas']:.2f}

**Total a pagar: ${debt_data['total']:.2f}**

Paga en linea: finanzas.queretaro.gob.mx
O en OXXO, bancos autorizados."""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": debt_data,
    }


@tool
def get_plate_requirements(tipo_tramite: str) -> dict[str, Any]:
    """
    Obtiene requisitos para tramite de placas.

    Args:
        tipo_tramite: Tipo de tramite (alta, cambio, reposicion, baja)

    Returns:
        Lista de requisitos y costos
    """
    logger.info(f"Getting plate requirements for: {tipo_tramite}")

    requirements = {
        "alta": {
            "nombre": "Alta de vehiculo nuevo",
            "requisitos": [
                "Factura original del vehiculo",
                "Identificacion oficial vigente",
                "Comprobante de domicilio reciente",
                "CURP",
                "Pago de derechos ($2,800 aprox.)",
            ],
            "costo": "$2,800 - $4,500 segun tipo",
            "tiempo": "Mismo dia",
        },
        "cambio": {
            "nombre": "Cambio de propietario",
            "requisitos": [
                "Factura endosada o carta factura",
                "Tarjeta de circulacion anterior",
                "Identificacion de comprador y vendedor",
                "Comprobante de domicilio",
                "Pago de tenencias al corriente",
            ],
            "costo": "$1,200 - $2,500 segun tipo",
            "tiempo": "Mismo dia",
        },
        "reposicion": {
            "nombre": "Reposicion de placas/tarjeta",
            "requisitos": [
                "Acta de extravio ante MP (si aplica)",
                "Identificacion oficial",
                "Comprobante de domicilio",
                "Pago de derechos",
            ],
            "costo": "$800 - $1,500",
            "tiempo": "3-5 dias habiles",
        },
        "baja": {
            "nombre": "Baja de vehiculo",
            "requisitos": [
                "Tarjeta de circulacion",
                "Placas (ambas)",
                "Identificacion oficial",
                "Sin adeudos de tenencia",
            ],
            "costo": "Sin costo",
            "tiempo": "Mismo dia",
        },
    }

    tipo_lower = tipo_tramite.lower()
    if tipo_lower not in requirements:
        return {
            "success": False,
            "formatted_response": f"Tipo de tramite '{tipo_tramite}' no reconocido. Opciones: alta, cambio, reposicion, baja.",
        }

    req = requirements[tipo_lower]
    formatted = f"""**{req['nombre']}**

**Requisitos:**
"""
    for r in req['requisitos']:
        formatted += f"- {r}\n"

    formatted += f"""
**Costo aproximado:** {req['costo']}
**Tiempo de entrega:** {req['tiempo']}

Agenda cita en: finanzas.queretaro.gob.mx/citas"""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": req,
    }


@tool
def get_verification_info(placa: str) -> dict[str, Any]:
    """
    Obtiene informacion de verificacion vehicular.

    Args:
        placa: Numero de placa del vehiculo

    Returns:
        Calendario de verificacion y centros cercanos
    """
    logger.info(f"Getting verification info for: {placa}")

    # Determine verification month based on last digit of plate
    last_digit = placa[-1] if placa[-1].isdigit() else "0"
    months = {
        "1": "Enero y Febrero",
        "2": "Febrero y Marzo",
        "3": "Marzo y Abril",
        "4": "Abril y Mayo",
        "5": "Mayo y Junio",
        "6": "Junio y Julio",
        "7": "Julio y Agosto",
        "8": "Agosto y Septiembre",
        "9": "Septiembre y Octubre",
        "0": "Octubre y Noviembre",
    }

    verification_period = months.get(last_digit, "Consultar calendario")

    formatted = f"""Verificacion vehicular para {placa.upper()}:

**Tu periodo de verificacion:** {verification_period}

**Requisitos:**
- Tarjeta de circulacion
- Pago de derechos ($650)
- Vehiculo en condiciones de circular

**Centros de verificacion:**
- Centro 1: Av. Constituyentes 123
- Centro 2: Blvd. Bernardo Quintana 456
- Centro 3: Av. 5 de Febrero 789

Horario: Lunes a Sabado 8:00 - 18:00"""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": {
            "placa": placa.upper(),
            "periodo": verification_period,
            "costo": 650.00,
        },
    }


@tool
def get_fines_info(placa: str) -> dict[str, Any]:
    """
    Consulta infracciones pendientes de un vehiculo.

    Args:
        placa: Numero de placa del vehiculo

    Returns:
        Lista de infracciones y montos
    """
    logger.info(f"Getting fines for: {placa}")

    # Simulated - in production would query database
    fines = []  # No fines for demo
    total = 0.0

    if fines:
        formatted = f"""Infracciones del vehiculo {placa.upper()}:

"""
        for fine in fines:
            formatted += f"- {fine['fecha']}: {fine['motivo']} - ${fine['monto']:.2f}\n"
        formatted += f"\n**Total: ${total:.2f}**"
    else:
        formatted = f"""El vehiculo {placa.upper()} no tiene infracciones pendientes.

Sigue respetando las normas de transito."""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": {
            "placa": placa.upper(),
            "infracciones": fines,
            "total": total,
        },
    }


@tool
def create_vehicle_ticket(
    titulo: str,
    descripcion: str,
    subcategory: str = "VEH-INF-001",
    placa: str | None = None,
    priority: str = "medium",
) -> dict[str, Any]:
    """
    Crea un ticket de servicio vehicular.

    Args:
        titulo: Titulo breve del reporte
        descripcion: Descripcion detallada del problema
        subcategory: Codigo de subcategoria
        placa: Placa del vehiculo involucrado
        priority: Prioridad (low, medium, high, urgent)

    Returns:
        Informacion del ticket creado con folio
    """
    import uuid

    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"VEH-{date_str}-{short_id}"

    logger.info(f"Creating vehicle ticket: {folio}")

    formatted = f"""**Solicitud de Servicio Vehicular Creada**

**Folio:** {folio}
**Asunto:** {titulo}
**Prioridad:** {priority}
**Estado:** Abierto

Tu solicitud sera atendida por el area de control vehicular.
Para seguimiento llama al 442-238-5000."""

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
    Transfiere la conversacion a un agente humano.

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

Te estoy comunicando con un agente de atencion de Finanzas.

Por favor espera un momento, alguien te atendera pronto.

Telefono directo: 442-238-5000
Linea de citas: 442-238-5100""",
    }


# ============================================
# Tool Registry
# ============================================

def get_tools() -> list:
    """Get all available tools for the Vehicles agent"""
    return [
        get_vehicle_debt,
        get_plate_requirements,
        get_verification_info,
        get_fines_info,
        create_vehicle_ticket,
        handoff_to_human,
    ]
