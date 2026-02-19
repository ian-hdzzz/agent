"""
Gobierno Queretaro - Education USEBEQ Agent Tools
Domain-specific tools for education services
"""

import logging
from datetime import datetime
from typing import Any

from langchain_core.tools import tool

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================
# Education-Specific Tools
# ============================================

@tool
def get_enrollment_info(nivel: str) -> dict[str, Any]:
    """
    Obtiene informacion de inscripciones y preinscripciones.

    Args:
        nivel: Nivel educativo (preescolar, primaria, secundaria)

    Returns:
        Informacion de inscripcion incluyendo fechas y requisitos
    """
    logger.info(f"Getting enrollment info for level: {nivel}")

    enrollment_data = {
        "preescolar": {
            "edad_minima": "3 anos cumplidos al 31 de diciembre",
            "requisitos": [
                "Acta de nacimiento (original y copia)",
                "CURP del menor",
                "Comprobante de domicilio",
                "Cartilla de vacunacion",
                "4 fotografias tamano infantil",
            ],
            "periodo_preinscripcion": "Febrero",
        },
        "primaria": {
            "edad_minima": "6 anos cumplidos al 31 de diciembre",
            "requisitos": [
                "Acta de nacimiento (original y copia)",
                "CURP del menor",
                "Constancia de preescolar",
                "Comprobante de domicilio",
                "4 fotografias tamano infantil",
            ],
            "periodo_preinscripcion": "Febrero",
        },
        "secundaria": {
            "edad_minima": "Haber concluido primaria",
            "requisitos": [
                "Acta de nacimiento (original y copia)",
                "CURP del menor",
                "Certificado de primaria",
                "Comprobante de domicilio",
                "4 fotografias tamano infantil",
            ],
            "periodo_preinscripcion": "Febrero",
        },
    }

    nivel_lower = nivel.lower()
    if nivel_lower not in enrollment_data:
        return {
            "success": False,
            "formatted_response": f"Nivel '{nivel}' no reconocido. Los niveles disponibles son: preescolar, primaria, secundaria.",
        }

    data = enrollment_data[nivel_lower]

    formatted = f"""Inscripcion a {nivel.capitalize()}:

**Requisito de edad:** {data['edad_minima']}
**Periodo de preinscripcion:** {data['periodo_preinscripcion']}

**Documentos necesarios:**
"""
    for req in data['requisitos']:
        formatted += f"- {req}\n"

    formatted += "\nLa preinscripcion se realiza en linea en: www.usebeq.edu.mx"

    return {
        "success": True,
        "formatted_response": formatted,
        "data": data,
    }


@tool
def get_scholarship_info(tipo: str = "general") -> dict[str, Any]:
    """
    Obtiene informacion sobre becas educativas disponibles.

    Args:
        tipo: Tipo de beca (excelencia, apoyo, transporte, general)

    Returns:
        Informacion de becas y requisitos
    """
    logger.info(f"Getting scholarship info: {tipo}")

    scholarships = {
        "excelencia": {
            "nombre": "Beca de Excelencia Academica",
            "monto": "$2,000 MXN bimestral",
            "requisitos": ["Promedio minimo 9.0", "Sin materias reprobadas", "Constancia de inscripcion"],
        },
        "apoyo": {
            "nombre": "Beca de Apoyo Economico",
            "monto": "$1,500 MXN bimestral",
            "requisitos": ["Estudio socioeconomico", "Comprobante de ingresos", "Constancia de inscripcion"],
        },
        "transporte": {
            "nombre": "Beca de Transporte",
            "monto": "$800 MXN mensual",
            "requisitos": ["Comprobante de domicilio lejano", "Constancia de inscripcion"],
        },
    }

    if tipo.lower() == "general":
        formatted = """Becas educativas disponibles:

"""
        for key, beca in scholarships.items():
            formatted += f"**{beca['nombre']}**\nMonto: {beca['monto']}\n\n"

        formatted += "Para mas informacion sobre requisitos, pregunta por una beca especifica."

        return {
            "success": True,
            "formatted_response": formatted,
            "data": scholarships,
        }

    tipo_lower = tipo.lower()
    if tipo_lower not in scholarships:
        return {
            "success": False,
            "formatted_response": f"Tipo de beca '{tipo}' no encontrado. Opciones: excelencia, apoyo, transporte.",
        }

    beca = scholarships[tipo_lower]
    formatted = f"""**{beca['nombre']}**

**Monto:** {beca['monto']}

**Requisitos:**
"""
    for req in beca['requisitos']:
        formatted += f"- {req}\n"

    formatted += "\nConvocatorias en: www.usebeq.edu.mx/becas"

    return {
        "success": True,
        "formatted_response": formatted,
        "data": beca,
    }


@tool
def check_scholarship_status(folio: str) -> dict[str, Any]:
    """
    Consulta el estado de una solicitud de beca.

    Args:
        folio: Numero de folio de la solicitud

    Returns:
        Estado actual de la solicitud
    """
    logger.info(f"Checking scholarship status for: {folio}")

    # Simulated - in production would query database
    return {
        "success": True,
        "formatted_response": f"""Estado de solicitud {folio}:

**Estado:** En revision
**Fecha de solicitud:** Hace 2 semanas
**Siguiente paso:** Esperar resultado de evaluacion

Los resultados se publican en: www.usebeq.edu.mx/becas/resultados""",
        "data": {
            "folio": folio,
            "status": "en_revision",
        },
    }


@tool
def get_school_info(zona: str, nivel: str = "primaria") -> dict[str, Any]:
    """
    Busca escuelas en una zona especifica.

    Args:
        zona: Zona, colonia o municipio de busqueda
        nivel: Nivel educativo (preescolar, primaria, secundaria)

    Returns:
        Lista de escuelas en la zona
    """
    logger.info(f"Getting school info for zone: {zona}, level: {nivel}")

    # Simulated school data
    schools = [
        {
            "nombre": f"Escuela {nivel.capitalize()} Benito Juarez",
            "direccion": f"Av. Principal 123, {zona}",
            "telefono": "442-123-4567",
            "turno": "Matutino y Vespertino",
        },
        {
            "nombre": f"Escuela {nivel.capitalize()} Miguel Hidalgo",
            "direccion": f"Calle Secundaria 456, {zona}",
            "telefono": "442-234-5678",
            "turno": "Matutino",
        },
    ]

    formatted = f"""Escuelas de {nivel} en {zona}:

"""
    for school in schools:
        formatted += f"""**{school['nombre']}**
Direccion: {school['direccion']}
Telefono: {school['telefono']}
Turno: {school['turno']}

"""

    formatted += "Para mas opciones, consulta el directorio completo en www.usebeq.edu.mx"

    return {
        "success": True,
        "formatted_response": formatted,
        "data": {"zona": zona, "nivel": nivel, "escuelas": schools},
    }


@tool
def get_certificate_info(tipo: str) -> dict[str, Any]:
    """
    Obtiene informacion sobre tramite de certificados.

    Args:
        tipo: Tipo de documento (certificado, constancia, duplicado)

    Returns:
        Requisitos y proceso para obtener el documento
    """
    logger.info(f"Getting certificate info: {tipo}")

    certificates = {
        "certificado": {
            "nombre": "Certificado de Estudios",
            "requisitos": ["CURP", "Acta de nacimiento", "Pago de derechos ($150)"],
            "tiempo": "5-10 dias habiles",
            "donde": "Oficinas de USEBEQ o escuela de egreso",
        },
        "constancia": {
            "nombre": "Constancia de Inscripcion",
            "requisitos": ["CURP", "Estar inscrito actualmente"],
            "tiempo": "Inmediato",
            "donde": "Escuela donde esta inscrito",
        },
        "duplicado": {
            "nombre": "Duplicado de Certificado",
            "requisitos": ["CURP", "Acta de nacimiento", "Pago de derechos ($200)", "Carta de extravio"],
            "tiempo": "10-15 dias habiles",
            "donde": "Oficinas de USEBEQ",
        },
    }

    tipo_lower = tipo.lower()
    if tipo_lower not in certificates:
        return {
            "success": False,
            "formatted_response": f"Tipo de documento '{tipo}' no reconocido. Opciones: certificado, constancia, duplicado.",
        }

    doc = certificates[tipo_lower]
    formatted = f"""**{doc['nombre']}**

**Requisitos:**
"""
    for req in doc['requisitos']:
        formatted += f"- {req}\n"

    formatted += f"""
**Tiempo de entrega:** {doc['tiempo']}
**Donde tramitarlo:** {doc['donde']}"""

    return {
        "success": True,
        "formatted_response": formatted,
        "data": doc,
    }


@tool
def create_education_ticket(
    titulo: str,
    descripcion: str,
    subcategory: str = "EDU-INF-001",
    nombre_escuela: str | None = None,
    cct: str | None = None,
    priority: str = "medium",
) -> dict[str, Any]:
    """
    Crea un ticket de servicio educativo.

    Args:
        titulo: Titulo breve del reporte
        descripcion: Descripcion detallada del problema
        subcategory: Codigo de subcategoria
        nombre_escuela: Nombre de la escuela involucrada
        cct: Clave de Centro de Trabajo de la escuela
        priority: Prioridad (low, medium, high, urgent)

    Returns:
        Informacion del ticket creado con folio
    """
    import uuid

    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"EDU-{date_str}-{short_id}"

    logger.info(f"Creating education ticket: {folio}")

    formatted = f"""**Solicitud de Servicio Educativo Creada**

**Folio:** {folio}
**Asunto:** {titulo}
**Prioridad:** {priority}
**Estado:** Abierto

Tu solicitud sera atendida por el area correspondiente.
Para seguimiento llama al 442-238-5700."""

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
    Transfiere la conversacion a un agente humano de USEBEQ.

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

Te estoy comunicando con un agente de atencion de USEBEQ.

Por favor espera un momento, alguien te atendera pronto.

Telefono directo: 442-238-5700
Linea de denuncia: 800-841-0022""",
    }


# ============================================
# Tool Registry
# ============================================

def get_tools() -> list:
    """Get all available tools for the Education USEBEQ agent"""
    return [
        get_enrollment_info,
        get_scholarship_info,
        check_scholarship_status,
        get_school_info,
        get_certificate_info,
        create_education_ticket,
        handoff_to_human,
    ]
