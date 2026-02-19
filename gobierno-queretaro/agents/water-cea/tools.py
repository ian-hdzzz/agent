"""
Gobierno Querétaro - Water CEA Agent Tools
Domain-specific tools for water services

Ported from TypeScript CEA tools to Python LangChain tools.
"""

import logging
import re
from datetime import datetime
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from langchain_core.tools import tool

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================
# SOAP Request Builders
# ============================================

def build_deuda_total_con_facturas_soap(contrato: str) -> str:
    """Build SOAP request for debt + invoice breakdown query (primary)"""
    return f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:int="http://interfazgenericagestiondeuda.occamcxf.occam.agbar.com/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <soapenv:Header>
        <wsse:Security mustUnderstand="1">
            <wsse:UsernameToken wsu:Id="UsernameToken-{settings.cea_soap_username}">
                <wsse:Username>{settings.cea_soap_username}</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{settings.cea_soap_password}</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <int:getDeudaTotalConFacturas>
            <contrato>{contrato}</contrato>
            <explotacion>12</explotacion>
            <idioma>es</idioma>
        </int:getDeudaTotalConFacturas>
    </soapenv:Body>
</soapenv:Envelope>"""


def build_deuda_contrato_soap(contrato: str) -> str:
    """Build SOAP request for contract debt query (fallback)"""
    return f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:int="http://interfazgenericagestiondeuda.occamcxf.occam.agbar.com/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <soapenv:Header>
        <wsse:Security mustUnderstand="1">
            <wsse:UsernameToken wsu:Id="UsernameToken-{settings.cea_soap_username}">
                <wsse:Username>{settings.cea_soap_username}</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{settings.cea_soap_password}</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <int:getDeudaContrato>
            <tipoIdentificador>CONTRATO</tipoIdentificador>
            <valor>{contrato}</valor>
            <explotacion>12</explotacion>
            <idioma>es</idioma>
        </int:getDeudaContrato>
    </soapenv:Body>
</soapenv:Envelope>"""


def build_consumo_soap(contrato: str, explotacion: str = "1") -> str:
    """Build SOAP request for consumption query"""
    return f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:occ="http://occamWS.ejb.negocio.occam.agbar.com" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <soapenv:Header>
        <wsse:Security mustUnderstand="1">
            <wsse:UsernameToken wsu:Id="UsernameToken-{settings.cea_soap_username}">
                <wsse:Username>{settings.cea_soap_username}</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{settings.cea_soap_password}</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <occ:getConsumos>
            <explotacion>{explotacion}</explotacion>
            <contrato>{contrato}</contrato>
            <idioma>es</idioma>
        </occ:getConsumos>
    </soapenv:Body>
</soapenv:Envelope>"""


def build_contrato_soap(contrato: str) -> str:
    """Build SOAP request for contract details query"""
    return f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:occ="http://occamWS.ejb.negocio.occam.agbar.com" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <soapenv:Header>
        <wsse:Security mustUnderstand="1">
            <wsse:UsernameToken wsu:Id="UsernameToken-{settings.cea_soap_username}">
                <wsse:Username>{settings.cea_soap_username}</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">{settings.cea_soap_password}</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <occ:consultaDetalleContrato>
            <numeroContrato>{contrato}</numeroContrato>
            <idioma>es</idioma>
        </occ:consultaDetalleContrato>
    </soapenv:Body>
</soapenv:Envelope>"""


# ============================================
# XML Parsing Helpers
# ============================================

def parse_xml_value(xml: str, tag: str) -> str | None:
    """Extract value from XML tag"""
    pattern = rf"<{tag}[^>]*>([^<]*)</{tag}>"
    match = re.search(pattern, xml, re.IGNORECASE)
    return match.group(1).strip() if match else None


async def call_cea_api(endpoint: str, soap_body: str) -> str:
    """Make SOAP call to CEA API"""
    url = f"{settings.cea_api_base}/{endpoint}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            url,
            content=soap_body,
            headers={"Content-Type": "text/xml;charset=UTF-8"},
        )
        return response.text


# ============================================
# Water-Specific Tools
# ============================================

@tool
async def get_water_balance(contrato: str) -> dict[str, Any]:
    """
    Obtiene el saldo y adeudo de un contrato de agua CEA.

    Args:
        contrato: Número de contrato CEA (ej: 123456)

    Returns:
        Información de saldo incluyendo total, vencido, por vencer
    """
    logger.info(f"Getting water balance for contract: {contrato}")

    try:
        # Step 1: Try getDeudaTotalConFacturas (primary - returns debt + invoice breakdown)
        logger.info("[get_water_balance] Calling getDeudaTotalConFacturas...")
        xml = await call_cea_api(
            "InterfazGenericaGestionDeudaWS",
            build_deuda_total_con_facturas_soap(contrato),
        )
        logger.info(f"[get_water_balance] Primary response (first 500 chars): {xml[:500]}")

        primary_ok = "<faultstring>" not in xml and "<error>" not in xml

        if primary_ok:
            total_deuda = float(parse_xml_value(xml, "deudaTotal") or "0")
            nombre_cliente = parse_xml_value(xml, "nombreCliente") or ""

            # Parse invoice blocks
            factura_matches = re.findall(
                r"<(?:factura|datosFacturaDeuda)>[\s\S]*?</(?:factura|datosFacturaDeuda)>",
                xml,
                re.IGNORECASE,
            )

            facturas = []
            vencido_calc = 0.0
            por_vencer_calc = 0.0

            for factura_xml in factura_matches:
                estado = parse_xml_value(factura_xml, "estado") or ""
                codigo_estado = parse_xml_value(factura_xml, "codigoEstado") or ""
                is_vencido = "vencid" in estado.lower() or codigo_estado == "4"
                importe = float(parse_xml_value(factura_xml, "importeTotal") or "0")

                facturas.append({
                    "numero": parse_xml_value(factura_xml, "numFactura") or "",
                    "periodo": parse_xml_value(factura_xml, "ciclo") or "",
                    "fecha_vencimiento": parse_xml_value(factura_xml, "fechaVencimiento") or "",
                    "importe": importe,
                    "estado": codigo_estado or estado,
                    "estado_texto": "vencido" if is_vencido else "pendiente",
                    "referencia_pago": parse_xml_value(factura_xml, "referenciaPago") or "",
                })

                if is_vencido:
                    vencido_calc += importe
                else:
                    por_vencer_calc += importe

            # If no invoices and zero debt, billing in process
            if not facturas and total_deuda == 0:
                return {
                    "success": True,
                    "formatted_response": f"Tu contrato {contrato} está en proceso de facturación. En cuanto se complete, podrás consultar tu saldo actualizado.",
                    "data": {"contrato": contrato, "total_deuda": 0, "mensaje": "proceso de facturación"},
                }

            # Build formatted response
            response = f"Estado de cuenta del contrato {contrato}:\n\n"
            response += f"💰 **Total a pagar: ${total_deuda:.2f}**\n"

            if facturas:
                if vencido_calc > 0:
                    response += f"🔴 Vencido: ${vencido_calc:.2f}\n"
                if por_vencer_calc > 0:
                    response += f"🟡 Por vencer: ${por_vencer_calc:.2f}\n"

                response += "\n📋 **Recibos pendientes:**\n"
                for f in facturas:
                    emoji = "🔴" if f["estado_texto"] == "vencido" else "🟡"
                    label = f["periodo"] or f["numero"]
                    response += f"{emoji} {label}: ${f['importe']:.2f} ({f['estado_texto']})\n"

            return {
                "success": True,
                "formatted_response": response,
                "data": {
                    "contrato": contrato,
                    "total_deuda": total_deuda,
                    "vencido": vencido_calc,
                    "por_vencer": por_vencer_calc,
                    "nombre_cliente": nombre_cliente,
                    "facturas": facturas,
                },
            }

        # Step 2: Fallback to getDeudaContrato
        logger.info("[get_water_balance] Primary failed, trying getDeudaContrato fallback...")
        fallback_xml = await call_cea_api(
            "InterfazGenericaGestionDeudaWS",
            build_deuda_contrato_soap(contrato),
        )
        logger.info(f"[get_water_balance] Fallback response (first 500 chars): {fallback_xml[:500]}")

        if "<faultstring>" in fallback_xml or "<error>" in fallback_xml:
            error_msg = (
                parse_xml_value(fallback_xml, "faultstring")
                or parse_xml_value(fallback_xml, "error")
                or "Error desconocido"
            )
            return {
                "success": False,
                "error": error_msg,
                "formatted_response": f"No encontré información de adeudo para el contrato {contrato}. ¿Puedes verificar el número?",
            }

        total_deuda = float(parse_xml_value(fallback_xml, "deuda") or parse_xml_value(fallback_xml, "deudaTotal") or "0")
        nombre_cliente = parse_xml_value(fallback_xml, "nombreCliente") or ""
        direccion = parse_xml_value(fallback_xml, "direccion") or ""
        mensaje = parse_xml_value(fallback_xml, "descripcionMensaje") or ""

        # Billing in process
        if total_deuda == 0 and mensaje:
            return {
                "success": True,
                "formatted_response": f"Tu contrato {contrato} está en proceso de facturación. En cuanto se complete, podrás consultar tu saldo actualizado.",
                "data": {"contrato": contrato, "total_deuda": 0, "mensaje": mensaje},
            }

        response = f"Estado de cuenta del contrato {contrato}:\n\n"
        response += f"💰 **Total a pagar: ${total_deuda:.2f}**\n"
        if nombre_cliente:
            response += f"👤 Cliente: {nombre_cliente}\n"
        if direccion:
            response += f"📍 Dirección: {direccion}\n"

        return {
            "success": True,
            "formatted_response": response,
            "data": {
                "contrato": contrato,
                "total_deuda": total_deuda,
                "vencido": 0,
                "por_vencer": 0,
                "nombre_cliente": nombre_cliente,
                "facturas": [],
            },
        }

    except Exception as e:
        logger.error(f"Error getting water balance: {e}")
        return {
            "success": False,
            "error": str(e),
            "formatted_response": "El sistema de consulta no está disponible en este momento. ¿Puedes intentar en unos minutos?",
        }


@tool
async def get_consumption_history(contrato: str, year: int | None = None) -> dict[str, Any]:
    """
    Obtiene el historial de consumo de agua de un contrato.

    Args:
        contrato: Número de contrato CEA
        year: Año específico para filtrar (opcional)

    Returns:
        Historial de consumos con promedios y tendencias
    """
    logger.info(f"Getting consumption history for contract: {contrato}, year: {year}")

    try:
        # Try different explotacion values
        consumos = []

        for explotacion in ["1", "12"]:
            xml = await call_cea_api("InterfazOficinaVirtualClientesWS", build_consumo_soap(contrato, explotacion))

            if "<faultstring>" in xml:
                continue

            # Parse consumption records
            consumo_matches = re.findall(r"<Consumo>[\s\S]*?</Consumo>", xml)

            for consumo_xml in consumo_matches:
                año = int(parse_xml_value(consumo_xml, "año") or "0")
                metros_cubicos = float(parse_xml_value(consumo_xml, "metrosCubicos") or "0")
                periodo = parse_xml_value(consumo_xml, "periodo") or ""
                fecha_lectura = parse_xml_value(consumo_xml, "fechaLectura") or ""
                estimado = parse_xml_value(consumo_xml, "estimado") == "true"

                # Extract month from periodo like "<JUN> - <JUN>"
                mes = ""
                mes_match = re.search(r"<([A-Z]{3})>", periodo)
                if mes_match:
                    mes = mes_match.group(1)

                consumos.append({
                    "periodo": f"{mes} {año}",
                    "consumo_m3": metros_cubicos,
                    "year": año,
                    "mes": mes,
                    "fecha_lectura": fecha_lectura,
                    "tipo_lectura": "estimada" if estimado else "real",
                })

            if consumos:
                break

        if not consumos:
            return {
                "success": False,
                "error": "No se encontró historial de consumo",
                "formatted_response": f"No encontré historial de consumo para el contrato {contrato}.",
            }

        # Get unique years
        años_disponibles = sorted(set(c["year"] for c in consumos if c["year"] > 0), reverse=True)

        # Filter by year if specified
        consumos_filtrados = consumos
        if year:
            consumos_filtrados = [c for c in consumos if c["year"] == year]

        # Calculate statistics
        promedio = sum(c["consumo_m3"] for c in consumos_filtrados) / len(consumos_filtrados) if consumos_filtrados else 0
        total_año = sum(c["consumo_m3"] for c in consumos_filtrados)

        # Calculate trend
        tendencia = "estable"
        if len(consumos) >= 6:
            recent = sum(c["consumo_m3"] for c in consumos[:3]) / 3
            older = sum(c["consumo_m3"] for c in consumos[-3:]) / 3
            if recent > older * 1.1:
                tendencia = "aumentando"
            elif recent < older * 0.9:
                tendencia = "disminuyendo"

        return {
            "success": True,
            "contrato": contrato,
            "year_consultado": year or "todos",
            "years_disponibles": años_disponibles,
            "total_registros": len(consumos),
            "registros_filtrados": len(consumos_filtrados),
            "promedio_mensual": round(promedio),
            "total_consumo_m3": total_año,
            "tendencia": tendencia,
            "consumos": consumos_filtrados,
            "resumen": f"Consumo {year}: Total {total_año} m³, Promedio mensual {round(promedio)} m³"
            if year else f"Historial: {len(consumos)} registros, años {años_disponibles[-1] if años_disponibles else 'N/A'} a {años_disponibles[0] if años_disponibles else 'N/A'}",
        }

    except Exception as e:
        logger.error(f"Error getting consumption history: {e}")
        return {
            "success": False,
            "error": str(e),
            "formatted_response": "No se pudo consultar el historial de consumo.",
        }


@tool
async def get_contract_details(contrato: str) -> dict[str, Any]:
    """
    Obtiene los detalles de un contrato de agua CEA.

    Args:
        contrato: Número de contrato CEA

    Returns:
        Información del contrato incluyendo titular, dirección, tarifa, estado
    """
    logger.info(f"Getting contract details for: {contrato}")

    try:
        xml = await call_cea_api("InterfazGenericaContratacionWS", build_contrato_soap(contrato))

        if "<faultstring>" in xml or "<error>" in xml:
            error_msg = parse_xml_value(xml, "faultstring") or "Error desconocido"
            return {
                "success": False,
                "error": error_msg,
                "formatted_response": f"No encontré información para el contrato {contrato}. ¿Puedes verificar el número?",
            }

        # Parse contract details
        calle = parse_xml_value(xml, "calle") or ""
        numero = parse_xml_value(xml, "numero") or ""
        direccion = f"{calle} {numero}".strip()

        titular = parse_xml_value(xml, "nombreTitular") or parse_xml_value(xml, "titular") or ""
        colonia = parse_xml_value(xml, "municipio") or parse_xml_value(xml, "colonia") or ""
        tarifa = parse_xml_value(xml, "descUso") or parse_xml_value(xml, "tarifa") or ""
        estado = parse_xml_value(xml, "estado") or "activo"

        # Format response
        formatted = f"""📋 **Contrato {contrato}**

👤 **Titular:** {titular}
📍 **Dirección:** {direccion}
🏘️ **Colonia:** {colonia}
💳 **Tarifa:** {tarifa}
📊 **Estado:** {estado.capitalize()}"""

        return {
            "success": True,
            "formatted_response": formatted,
            "data": {
                "numero_contrato": contrato,
                "titular": titular,
                "direccion": direccion,
                "colonia": colonia,
                "tarifa": tarifa,
                "estado": estado,
            },
        }

    except Exception as e:
        logger.error(f"Error getting contract details: {e}")
        return {
            "success": False,
            "error": str(e),
            "formatted_response": "El sistema de consulta no está disponible en este momento.",
        }


@tool
def create_water_ticket(
    titulo: str,
    descripcion: str,
    subcategory: str = "REP-FG-001",
    contract_number: str | None = None,
    ubicacion: str | None = None,
    priority: str = "medium",
) -> dict[str, Any]:
    """
    Crea un ticket de servicio de agua (fuga, drenaje, calidad, etc.)

    Args:
        titulo: Título breve del reporte
        descripcion: Descripción detallada del problema
        subcategory: Código de subcategoría (REP-FG-001, REP-DR-001, etc.)
        contract_number: Número de contrato (opcional para fugas en vía pública)
        ubicacion: Ubicación del problema (requerido para fugas en calle)
        priority: Prioridad (low, medium, high, urgent)

    Returns:
        Información del ticket creado con folio
    """
    import uuid

    # Generate folio
    date_str = datetime.now().strftime("%Y%m%d")
    short_id = str(uuid.uuid4())[:4].upper()
    folio = f"CEA-{date_str}-{short_id}"

    logger.info(f"Creating water ticket: {folio}")

    # Determine emoji based on subcategory
    emoji_map = {
        "REP-FG": "💧",  # Fuga
        "REP-DR": "🚿",  # Drenaje
        "REP-CA": "🌊",  # Calidad agua
        "REP-SA": "🚫",  # Sin agua
    }
    emoji = "💧"
    for prefix, e in emoji_map.items():
        if subcategory.startswith(prefix):
            emoji = e
            break

    formatted = f"""{emoji} **Reporte Creado**

📋 **Folio:** {folio}
📝 **Asunto:** {titulo}
⚡ **Prioridad:** {priority}
📊 **Estado:** Abierto

Recibirás seguimiento a tu reporte. Para emergencias llama al 442-238-8200."""

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
def get_receipt_link(contract_number: str) -> dict[str, Any]:
    """
    Genera el enlace para descargar el recibo digital de agua.

    Args:
        contract_number: Número de contrato CEA

    Returns:
        Enlace para descarga del recibo
    """
    download_url = f"https://ceaqro.gob.mx/consulta-recibo?contrato={contract_number}"

    return {
        "success": True,
        "contract_number": contract_number,
        "download_url": download_url,
        "formatted_response": f"""Aquí está el enlace para descargar tu recibo digital:

🔗 {download_url}

También puedes consultar tu recibo en la página oficial de CEA Querétaro.""",
    }


@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """
    Transfiere la conversación a un agente humano de CEA.

    Args:
        reason: Motivo de la transferencia

    Returns:
        Confirmación de transferencia
    """
    logger.info(f"Handoff to human requested: {reason}")

    return {
        "success": True,
        "reason": reason,
        "formatted_response": """👤 **Transferencia a Asesor**

Te estoy comunicando con un agente de CEA.

Por favor espera un momento, alguien te atenderá pronto.

📞 Para emergencias: 442-238-8200""",
    }


# ============================================
# Tool Registry
# ============================================

def get_tools() -> list:
    """Get all available tools for the Water CEA agent"""
    return [
        get_water_balance,
        get_consumption_history,
        get_contract_details,
        create_water_ticket,
        get_receipt_link,
        handoff_to_human,
    ]
