"""Gobierno Queretaro - AppQro Agent Tools"""
import logging
from datetime import datetime
from typing import Any
from langchain_core.tools import tool
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

@tool
def get_troubleshooting_guide(problema: str) -> dict[str, Any]:
    """Obtiene guia de solucion de problemas tecnicos.
    Args:
        problema: Tipo de problema (login, error, lento, crash)
    """
    logger.info(f"Getting troubleshooting guide: {problema}")
    guides = {
        "login": "**Problemas de Login:**\n1. Verifica tu email y contrasena\n2. Usa 'Olvide mi contrasena' si es necesario\n3. Verifica conexion a internet\n4. Actualiza la app a la ultima version",
        "error": "**Errores en la App:**\n1. Cierra y abre la app\n2. Borra cache (Ajustes > Apps > AppQro > Borrar cache)\n3. Reinstala la app si persiste\n4. Reporta el error con captura de pantalla",
        "lento": "**App Lenta:**\n1. Verifica tu conexion a internet\n2. Cierra otras apps\n3. Reinicia tu telefono\n4. Actualiza la app",
        "crash": "**App se Cierra:**\n1. Actualiza la app\n2. Reinicia el telefono\n3. Borra datos de la app\n4. Reinstala si persiste"
    }
    guide = guides.get(problema.lower(), guides["error"])
    formatted = f"{guide}\n\nSi el problema persiste, contacta soporte: 442-238-5000"
    return {"success": True, "formatted_response": formatted}

@tool
def get_app_feature_guide(funcion: str) -> dict[str, Any]:
    """Obtiene guia de uso de funciones de la app.
    Args:
        funcion: Funcion a explicar (reporte, pago, tramite, consulta)
    """
    logger.info(f"Getting feature guide: {funcion}")
    guides = {
        "reporte": "**Crear Reporte Ciudadano:**\n1. Abre AppQro\n2. Toca 'Nuevo Reporte'\n3. Selecciona categoria\n4. Describe el problema\n5. Agrega foto (opcional)\n6. Marca ubicacion\n7. Envia",
        "pago": "**Realizar Pago:**\n1. Abre AppQro\n2. Ve a 'Pagos'\n3. Selecciona servicio (agua, predial, etc.)\n4. Ingresa datos\n5. Elige metodo de pago\n6. Confirma",
        "tramite": "**Hacer Tramite:**\n1. Abre AppQro\n2. Ve a 'Tramites'\n3. Busca tu tramite\n4. Sigue los pasos indicados",
        "consulta": "**Consultar Estado:**\n1. Abre AppQro\n2. Ve a 'Mis Reportes' o 'Mis Tramites'\n3. Selecciona el que quieres consultar"
    }
    guide = guides.get(funcion.lower(), "Funcion no encontrada. Opciones: reporte, pago, tramite, consulta")
    return {"success": True, "formatted_response": guide}

@tool
def check_report_status(folio_reporte: str) -> dict[str, Any]:
    """Consulta estado de reporte ciudadano."""
    logger.info(f"Checking report status: {folio_reporte}")
    formatted = f"**Reporte {folio_reporte}**\n\n**Estado:** En atencion\n**Dependencia:** Servicios Publicos\n**Fecha:** Hace 3 dias\n\nSera notificado cuando se resuelva."
    return {"success": True, "formatted_response": formatted}

@tool
def create_app_ticket(titulo: str, descripcion: str, subcategory: str = "APP-TEC-001", priority: str = "medium") -> dict[str, Any]:
    """Crea un ticket de soporte para AppQro."""
    import uuid
    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"APP-{date_str}-{short_id}"
    logger.info(f"Creating app ticket: {folio}")
    formatted = f"**Ticket de Soporte Creado**\n\n**Folio:** {folio}\n**Estado:** Abierto\n\nEl equipo tecnico revisara tu caso.\nSoporte: 442-238-5000"
    return {"success": True, "folio": folio, "titulo": titulo, "subcategory": subcategory, "priority": priority, "status": "open", "formatted_response": formatted}

@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """Transfiere a soporte tecnico."""
    logger.info(f"Handoff to human: {reason}")
    return {"success": True, "reason": reason, "formatted_response": "**Transferencia a Soporte**\n\nTe comunico con soporte tecnico.\nTel: 442-238-5000"}

def get_tools() -> list:
    return [get_troubleshooting_guide, get_app_feature_guide, check_report_status, create_app_ticket, handoff_to_human]
