"""Gobierno Queretaro - Housing IVEQ Agent Tools"""
import logging
from datetime import datetime
from typing import Any
from langchain_core.tools import tool
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@tool
def get_housing_programs() -> dict[str, Any]:
    """Obtiene programas de vivienda disponibles."""
    logger.info("Getting housing programs")
    formatted = """**Programas de Vivienda IVEQ:**

**1. Credito IVEQ**
- Hasta $350,000 para vivienda
- Tasa preferencial
- Plazos hasta 20 anos

**2. Vivienda Social**
- Para familias de bajos ingresos
- Subsidio hasta 90%
- Sorteo periodico

**3. Autoconstruccion**
- Apoyo para construir tu casa
- Asesoria tecnica incluida

Requisitos basicos:
- Ser residente de Queretaro
- No tener vivienda propia
- Comprobar ingresos

Informes: 442-238-5200"""
    return {"success": True, "formatted_response": formatted}

@tool
def get_improvement_programs() -> dict[str, Any]:
    """Obtiene programas de mejoramiento de vivienda."""
    logger.info("Getting improvement programs")
    formatted = """**Programas de Mejoramiento:**

**Piso Firme**
- Sustitucion de piso de tierra
- Gratuito para familias vulnerables

**Techo Seguro**
- Laminas o losa de concreto
- Apoyo parcial o total

**Ampliacion**
- Cuartos adicionales
- Banos, cocinas

**Requisitos:**
- Ser propietario o tener posesion
- Estudio socioeconomico
- Identificacion oficial

Aplica en: iveq.gob.mx o modulos"""
    return {"success": True, "formatted_response": formatted}

@tool
def get_regularization_info() -> dict[str, Any]:
    """Obtiene informacion sobre regularizacion de terrenos."""
    logger.info("Getting regularization info")
    formatted = """**Regularizacion / Escrituracion:**

Para obtener escrituras de tu terreno:

**Requisitos:**
- Comprobante de posesion (recibos, testimonios)
- Identificacion oficial
- Comprobante de domicilio
- Plano del terreno

**Proceso:**
1. Acudir a IVEQ con documentos
2. Estudio juridico del predio
3. Pago de derechos
4. Emision de escritura

**Costo:** Variable segun valor del terreno

Informes: 442-238-5200"""
    return {"success": True, "formatted_response": formatted}

@tool
def check_application_status(folio: str) -> dict[str, Any]:
    """Consulta estado de solicitud de vivienda."""
    logger.info(f"Checking application status: {folio}")
    formatted = f"**Solicitud {folio}**\n\n**Estado:** En revision\n**Etapa:** Validacion de documentos\n\nTe notificaremos cuando haya actualizacion.\nTel: 442-238-5200"
    return {"success": True, "formatted_response": formatted}

@tool
def create_housing_ticket(titulo: str, descripcion: str, subcategory: str = "VIV-CON-001", priority: str = "medium") -> dict[str, Any]:
    """Crea una solicitud de servicio de vivienda."""
    import uuid
    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"VIV-{date_str}-{short_id}"
    logger.info(f"Creating housing ticket: {folio}")
    formatted = f"**Solicitud Creada**\n\n**Folio:** {folio}\n**Estado:** Abierto\n\nTe contactaremos pronto.\nTel: 442-238-5200"
    return {"success": True, "folio": folio, "titulo": titulo, "subcategory": subcategory, "priority": priority, "status": "open", "formatted_response": formatted}

@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """Transfiere a un agente del IVEQ."""
    logger.info(f"Handoff to human: {reason}")
    return {"success": True, "reason": reason, "formatted_response": "**Transferencia a Asesor**\n\nTe comunico con un agente del IVEQ.\nTel: 442-238-5200"}

def get_tools() -> list:
    return [get_housing_programs, get_improvement_programs, get_regularization_info, check_application_status, create_housing_ticket, handoff_to_human]
