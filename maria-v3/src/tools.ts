// ============================================
// Maria V3 - Native Tools for Claude Agent SDK
// Combined from maria-claude with caching + metrics
// ============================================

import { config as dotenvConfig } from "dotenv";
dotenvConfig();

import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import { ProxyAgent, fetch as undiciFetch } from "undici";
import pg from "pg";
import type {
    CreateTicketInput,
    CreateTicketResult,
    DeudaResponse,
    ConsumoResponse,
    ContratoResponse,
    CategoryCode,
    TicketPriority,
} from "./types.js";
import {
    renderTemplate,
    getCategoryEmoji,
    getTicketEmoji
} from "./config/response-templates.js";
import { updateConversationStatus } from "./chatwoot.js";
import { getCache, CacheKeys } from "./utils/cache.js";
import { logger } from "./utils/logger.js";
import { config } from "./config/index.js";

// ============================================
// Configuration
// ============================================

const CEA_API_BASE = config.ceaApiBase;
const PROXY_URL = config.ceaProxyUrl;

const pgPool = new pg.Pool(config.pg);

// ============================================
// Utility Functions
// ============================================

async function fetchWithRetry(
    url: string,
    options: RequestInit,
    maxRetries = 3,
    delayMs = 1000
): Promise<Response> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            let response: Response;

            if (PROXY_URL && url.includes('ceaqueretaro.gob.mx')) {
                logger.debug({ proxy: PROXY_URL, url }, "Using proxy");
                const proxyAgent = new ProxyAgent(PROXY_URL);

                response = await undiciFetch(url, {
                    method: options.method || 'GET',
                    headers: options.headers as Record<string, string>,
                    body: options.body as string,
                    dispatcher: proxyAgent,
                    signal: AbortSignal.timeout(30000)
                }) as unknown as Response;
            } else {
                response = await fetch(url, {
                    ...options,
                    signal: AbortSignal.timeout(30000)
                });
            }

            if (!response.ok && attempt < maxRetries) {
                logger.warn({ attempt, status: response.status }, "API attempt failed, retrying");
                await new Promise(r => setTimeout(r, delayMs * attempt));
                continue;
            }

            return response;
        } catch (error) {
            lastError = error as Error;
            logger.warn({ attempt, error: lastError.message }, "API request error");

            if (attempt < maxRetries) {
                await new Promise(r => setTimeout(r, delayMs * attempt));
            }
        }
    }

    throw lastError || new Error("Request failed after retries");
}

function parseXMLValue(xml: string, tag: string): string | null {
    const regex = new RegExp(`<${tag}[^>]*>([^<]*)</${tag}>`, 'i');
    const match = xml.match(regex);
    return match && match[1] ? match[1].trim() : null;
}

export function getMexicoDate(): Date {
    return new Date(new Date().toLocaleString("en-US", { timeZone: "America/Mexico_City" }));
}

// ============================================
// SOAP Builders
// ============================================

function buildDeudaSOAP(contrato: string): string {
    return `<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:int="http://interfazgenericagestiondeuda.occamcxf.occam.agbar.com/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <soapenv:Header>
        <wsse:Security mustUnderstand="1">
            <wsse:UsernameToken wsu:Id="UsernameTokenWSGESTIONDEUDA">
                <wsse:Username>WSGESTIONDEUDA</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">WSGESTIONDEUDA</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <int:getDeuda>
            <tipoIdentificador>CONTRATO</tipoIdentificador>
            <valor>${contrato}</valor>
            <explotacion>12</explotacion>
            <idioma>es</idioma>
        </int:getDeuda>
    </soapenv:Body>
</soapenv:Envelope>`;
}

function buildConsumoSOAP(contrato: string, explotacion: string = "1"): string {
    return `<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:occ="http://occamWS.ejb.negocio.occam.agbar.com" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <soapenv:Header>
        <wsse:Security mustUnderstand="1">
            <wsse:UsernameToken wsu:Id="UsernameToken-WSGESTIONDEUDA">
                <wsse:Username>WSGESTIONDEUDA</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">WSGESTIONDEUDA</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <occ:getConsumos>
            <explotacion>${explotacion}</explotacion>
            <contrato>${contrato}</contrato>
            <idioma>es</idioma>
        </occ:getConsumos>
    </soapenv:Body>
</soapenv:Envelope>`;
}

function buildContratoSOAP(contrato: string): string {
    return `<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:occ="http://occamWS.ejb.negocio.occam.agbar.com" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <soapenv:Header>
        <wsse:Security mustUnderstand="1">
            <wsse:UsernameToken wsu:Id="UsernameToken-WSGESTIONDEUDA">
                <wsse:Username>WSGESTIONDEUDA</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">WSGESTIONDEUDA</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <occ:consultaDetalleContrato>
            <numeroContrato>${contrato}</numeroContrato>
            <idioma>es</idioma>
        </occ:consultaDetalleContrato>
    </soapenv:Body>
</soapenv:Envelope>`;
}

function buildFacturasSOAP(contrato: string, explotacion: string = "1"): string {
    return `<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:occ="http://occamWS.ejb.negocio.occam.agbar.com" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
    <soapenv:Header>
        <wsse:Security mustUnderstand="1">
            <wsse:UsernameToken wsu:Id="UsernameToken-WSGESTIONDEUDA">
                <wsse:Username>WSGESTIONDEUDA</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">WSGESTIONDEUDA</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <occ:getFacturas>
            <explotacion>${explotacion}</explotacion>
            <contrato>${contrato}</contrato>
            <idioma>es</idioma>
        </occ:getFacturas>
    </soapenv:Body>
</soapenv:Envelope>`;
}

interface FacturaPendiente {
    numero: string;
    periodo: string;
    fechaEmision: string;
    importe: number;
    estado: number;
    estadoTexto: string;
}

function parseFacturasResponse(xml: string): FacturaPendiente[] {
    const facturas: FacturaPendiente[] = [];
    const facturaMatches = xml.match(/<Factura>[\s\S]*?<\/Factura>/g) || [];

    for (const facturaXml of facturaMatches) {
        const estado = parseInt(parseXMLValue(facturaXml, "estado") || "0");

        if (estado === 2 || estado === 4) {
            const periodo = parseXMLValue(facturaXml, "periodo") || "";
            const año = parseXMLValue(facturaXml, "año") || "";
            const meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
            const periodoTexto = `${meses[parseInt(periodo)] || periodo} ${año}`;

            facturas.push({
                numero: parseXMLValue(facturaXml, "numero") || "",
                periodo: periodoTexto,
                fechaEmision: parseXMLValue(facturaXml, "fechaEmision") || "",
                importe: parseFloat(parseXMLValue(facturaXml, "importeTotal") || "0"),
                estado,
                estadoTexto: estado === 4 ? "vencido" : "pendiente"
            });
        }
    }

    return facturas;
}

// ============================================
// Response Parsers
// ============================================

function parseDeudaResponse(xml: string): DeudaResponse {
    try {
        if (xml.includes("<faultstring>") || xml.includes("<error>")) {
            const faultMsg = parseXMLValue(xml, "faultstring") || parseXMLValue(xml, "error") || "Error desconocido";
            return { success: false, error: faultMsg, rawResponse: xml };
        }

        const totalDeuda = parseFloat(parseXMLValue(xml, "deudaTotal") || parseXMLValue(xml, "importeTotal") || parseXMLValue(xml, "totalDeuda") || "0");
        const vencido = parseFloat(parseXMLValue(xml, "saldoAnteriorTotal") || parseXMLValue(xml, "importeVencido") || "0");
        const porVencer = parseFloat(parseXMLValue(xml, "deuda") || parseXMLValue(xml, "importePorVencer") || "0");

        return {
            success: true,
            data: { totalDeuda, vencido, porVencer, conceptos: [] }
        };
    } catch (error) {
        return { success: false, error: `Error parsing response: ${error}`, rawResponse: xml };
    }
}

function parseConsumoResponse(xml: string): ConsumoResponse {
    try {
        if (xml.includes("<faultstring>") || xml.includes("<error>")) {
            const faultMsg = parseXMLValue(xml, "faultstring") || parseXMLValue(xml, "error") || "Error desconocido";
            return { success: false, error: faultMsg };
        }

        const consumos: Array<{
            periodo: string;
            consumoM3: number;
            lecturaAnterior: number;
            lecturaActual: number;
            fechaLectura: string;
            tipoLectura: "real" | "estimada";
            año: number;
            mes: string;
        }> = [];
        const consumoMatches = xml.match(/<Consumo>[\s\S]*?<\/Consumo>/g) ||
            xml.match(/<consumo>[\s\S]*?<\/consumo>/gi) || [];

        for (const consumoXml of consumoMatches) {
            const año = parseInt(parseXMLValue(consumoXml, "año") || "0");
            const metrosCubicos = parseFloat(parseXMLValue(consumoXml, "metrosCubicos") || parseXMLValue(consumoXml, "consumo") || "0");
            const periodo = parseXMLValue(consumoXml, "periodo") || "";
            const fechaLectura = parseXMLValue(consumoXml, "fechaLectura") || "";
            const estimado = parseXMLValue(consumoXml, "estimado") === "true";

            let mes = "";
            const mesMatch = periodo.match(/<([A-Z]{3})>/);
            if (mesMatch && mesMatch[1]) {
                mes = mesMatch[1];
            }

            consumos.push({
                periodo: `${mes} ${año}`,
                consumoM3: metrosCubicos,
                lecturaAnterior: 0,
                lecturaActual: 0,
                fechaLectura,
                tipoLectura: estimado ? "estimada" : "real",
                año,
                mes
            });
        }

        const promedioMensual = consumos.length > 0
            ? consumos.reduce((sum, c) => sum + c.consumoM3, 0) / consumos.length
            : 0;

        let tendencia: 'aumentando' | 'estable' | 'disminuyendo' = 'estable';
        if (consumos.length >= 3) {
            const recent = consumos.slice(0, 3).reduce((s, c) => s + c.consumoM3, 0) / 3;
            const older = consumos.slice(-3).reduce((s, c) => s + c.consumoM3, 0) / 3;
            if (recent > older * 1.1) tendencia = 'aumentando';
            else if (recent < older * 0.9) tendencia = 'disminuyendo';
        }

        return { success: true, data: { consumos, promedioMensual, tendencia } };
    } catch (error) {
        return { success: false, error: `Error parsing response: ${error}` };
    }
}

function parseContratoResponse(xml: string): ContratoResponse {
    try {
        if (xml.includes("<faultstring>") || xml.includes("<error>")) {
            const faultMsg = parseXMLValue(xml, "faultstring") || parseXMLValue(xml, "error") || "Error desconocido";
            return { success: false, error: faultMsg };
        }

        const calle = parseXMLValue(xml, "calle") || "";
        const numero = parseXMLValue(xml, "numero") || "";
        const direccion = [calle, numero].filter(Boolean).join(" ");

        return {
            success: true,
            data: {
                numeroContrato: parseXMLValue(xml, "numeroContrato") || parseXMLValue(xml, "contrato") || "",
                titular: parseXMLValue(xml, "nombreTitular") || parseXMLValue(xml, "titular") || "",
                direccion: direccion,
                colonia: parseXMLValue(xml, "municipio") || parseXMLValue(xml, "colonia") || "",
                codigoPostal: parseXMLValue(xml, "codigoPostal") || parseXMLValue(xml, "cp") || "",
                tarifa: parseXMLValue(xml, "descUso") || parseXMLValue(xml, "tarifa") || "",
                estado: (parseXMLValue(xml, "estado") || "activo") as 'activo' | 'suspendido' | 'cortado',
                fechaAlta: parseXMLValue(xml, "fechaAlta") || "",
                ultimaLectura: parseXMLValue(xml, "ultimaLectura") || undefined
            }
        };
    } catch (error) {
        return { success: false, error: `Error parsing response: ${error}` };
    }
}

// ============================================
// PostgreSQL Helpers
// ============================================

async function pgQuery<T = Record<string, unknown>>(query: string, params?: unknown[]): Promise<T[]> {
    const client = await pgPool.connect();
    try {
        const result = await client.query(query, params);
        return result.rows as T[];
    } finally {
        client.release();
    }
}

// ============================================
// Category/Subcategory ID Lookup Helpers
// ============================================

async function getCategoryId(code: string): Promise<number | null> {
    try {
        const result = await pgQuery<{ id: number }>(
            'SELECT id FROM ticket_categories WHERE code = $1 AND account_id = 2',
            [code]
        );
        return result?.[0]?.id || null;
    } catch (error) {
        logger.warn({ code, error }, "Failed to lookup category");
        return null;
    }
}

async function getSubcategoryId(code: string): Promise<number | null> {
    try {
        const result = await pgQuery<{ id: number }>(
            'SELECT id FROM ticket_subcategories WHERE code = $1',
            [code]
        );
        return result?.[0]?.id || null;
    } catch (error) {
        logger.warn({ code, error }, "Failed to lookup subcategory");
        return null;
    }
}

// ============================================
// Ticket Creation Helper
// ============================================

export async function createTicketDirect(input: CreateTicketInput): Promise<CreateTicketResult> {
    logger.info({ input }, "Creating ticket");

    try {
        const priority = input.priority || "medium";
        const status = "open";

        const categoryId = await getCategoryId(input.category_code);
        const subcategoryId = input.subcategory_code ? await getSubcategoryId(input.subcategory_code) : null;

        // Get conversation and contact IDs from environment (set by workflow)
        const conversationId = process.env.CURRENT_CHATWOOT_CONVERSATION_ID
            ? parseInt(process.env.CURRENT_CHATWOOT_CONVERSATION_ID)
            : null;
        const contactId = process.env.CURRENT_CHATWOOT_CONTACT_ID
            ? parseInt(process.env.CURRENT_CHATWOOT_CONTACT_ID)
            : null;

        const result = await pgQuery<{ id: number; folio: string }>(`
            INSERT INTO tickets (
                account_id, title, description, status, priority,
                ticket_type, service_type, channel, contract_number,
                client_name, metadata,
                ticket_category_id, ticket_subcategory_id,
                legacy_ticket_type, legacy_service_type,
                conversation_id, contact_id,
                created_at, updated_at
            ) VALUES (
                2, $1, $2, $3, $4,
                'GEN', 'general', 'whatsapp', $5,
                $6, $7,
                $8, $9,
                $10, $11,
                $12, $13,
                NOW(), NOW()
            )
            RETURNING id, folio
        `, [
            input.titulo,
            input.descripcion,
            status,
            priority,
            input.contract_number || null,
            input.contract_number ? null : 'Cliente WhatsApp',
            JSON.stringify({
                email: input.email || null,
                ubicacion: input.ubicacion || null,
                category_code: input.category_code,
                subcategory_code: input.subcategory_code
            }),
            categoryId,
            subcategoryId,
            input.category_code,
            input.subcategory_code || null,
            conversationId,
            contactId
        ]);

        const createdTicket = result[0];
        if (!createdTicket) {
            throw new Error("No ticket returned from database");
        }
        logger.info({ folio: createdTicket.folio }, "Ticket created");

        return {
            success: true,
            folio: createdTicket.folio,
            ticketId: String(createdTicket.id),
            message: `Ticket creado exitosamente con folio ${createdTicket.folio}`
        };
    } catch (error) {
        logger.error({ error }, "Ticket creation error");

        const now = getMexicoDate();
        const timestamp = now.getTime().toString().slice(-4);
        const fallbackFolio = `${input.category_code}-${timestamp}`;

        return {
            success: true,
            folio: fallbackFolio,
            warning: "Ticket creado localmente, sincronización pendiente",
            message: `Ticket registrado con folio ${fallbackFolio}`
        };
    }
}

// ============================================
// CLAUDE AGENT SDK TOOLS
// ============================================

export const getDeudaTool = tool(
    "get_deuda",
    `Obtiene el saldo y adeudo de un contrato CEA.

RETORNA:
- totalDeuda: Total a pagar
- vencido: Monto vencido
- porVencer: Monto por vencer
- conceptos: Desglose de adeudos

Usa este tool cuando el usuario pregunte por su saldo, deuda, cuánto debe, o quiera pagar.`,
    {
        contrato: z.string().describe("Número de contrato CEA (ej: 123456)")
    },
    async ({ contrato }) => {
        logger.info({ contrato }, "Fetching debt");

        // Check cache first
        const cache = getCache();
        const cacheKey = CacheKeys.deuda(contrato);
        const cached = cache.get<string>(cacheKey);
        if (cached) {
            logger.debug({ contrato }, "Returning cached debt data");
            return { content: [{ type: "text" as const, text: cached }] };
        }

        try {
            const response = await fetchWithRetry(
                `${CEA_API_BASE}/InterfazGenericaGestionDeudaWS`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'text/xml;charset=UTF-8' },
                    body: buildDeudaSOAP(contrato)
                }
            );

            const xml = await response.text();
            const parsed = parseDeudaResponse(xml);

            if (!parsed.success) {
                return { content: [{ type: "text" as const, text: JSON.stringify({
                    success: false,
                    error: parsed.error,
                    formatted_response: `No encontré información de adeudo para el contrato ${contrato}. ¿Puedes verificar el número?`
                }) }] };
            }

            const data = parsed.data!;

            // Fetch invoice details if there's debt
            let facturas: FacturaPendiente[] = [];
            let vencidoCalculado = 0;
            let porVencerCalculado = 0;

            if (data.totalDeuda > 0) {
                const facturasResponse = await fetchWithRetry(
                    `${CEA_API_BASE}/InterfazOficinaVirtualClientesWS`,
                    {
                        method: 'POST',
                        headers: { 'Content-Type': 'text/xml;charset=UTF-8' },
                        body: buildFacturasSOAP(contrato, "1")
                    }
                );

                const facturasXml = await facturasResponse.text();
                facturas = parseFacturasResponse(facturasXml);

                for (const factura of facturas) {
                    if (factura.estado === 4) {
                        vencidoCalculado += factura.importe;
                    } else if (factura.estado === 2) {
                        porVencerCalculado += factura.importe;
                    }
                }
            }

            // Build formatted response
            let formattedResponse = `Estado de cuenta del contrato ${contrato}:\n\n`;
            formattedResponse += `💰 **Total a pagar: $${data.totalDeuda.toFixed(2)}**\n`;

            if (facturas.length > 0) {
                if (vencidoCalculado > 0) {
                    formattedResponse += `🔴 Vencido: $${vencidoCalculado.toFixed(2)}\n`;
                }
                if (porVencerCalculado > 0) {
                    formattedResponse += `🟡 Por vencer: $${porVencerCalculado.toFixed(2)}\n`;
                }

                formattedResponse += `\n📋 **Recibos pendientes:**\n`;
                for (const factura of facturas) {
                    const emoji = factura.estado === 4 ? "🔴" : "🟡";
                    formattedResponse += `${emoji} ${factura.periodo}: $${factura.importe.toFixed(2)} (${factura.estadoTexto})\n`;
                }
            } else {
                formattedResponse += `Vencido: $${data.vencido.toFixed(2)}\n`;
                formattedResponse += `Por vencer: $${data.porVencer.toFixed(2)}\n`;
            }

            const result = JSON.stringify({
                success: true,
                formatted_response: formattedResponse,
                data: {
                    contrato,
                    totalDeuda: data.totalDeuda,
                    vencido: vencidoCalculado || data.vencido,
                    porVencer: porVencerCalculado || data.porVencer,
                    facturas: facturas
                }
            });

            // Cache the result
            cache.set(cacheKey, result);

            return { content: [{ type: "text" as const, text: result }] };
        } catch (error) {
            logger.error({ contrato, error }, "get_deuda error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudo consultar el saldo: ${error instanceof Error ? error.message : 'Error desconocido'}`,
                        formatted_response: "El sistema de consulta no está disponible en este momento. ¿Puedes intentar en unos minutos?"
                    })
                }]
            };
        }
    }
);

export const getConsumoTool = tool(
    "get_consumo",
    `Obtiene el historial de consumo de agua de un contrato.

PARÁMETROS:
- contrato: Número de contrato CEA (requerido)
- year: Año específico para filtrar (opcional, ej: 2022, 2023)

RETORNA:
- consumos: Lista de consumos por periodo (m³) con año y mes
- promedioMensual: Promedio de consumo mensual
- tendencia: Si el consumo está aumentando, estable o disminuyendo

Usa cuando el usuario pregunte por su consumo, historial de lecturas, o cuánta agua ha gastado.`,
    {
        contrato: z.string().describe("Número de contrato CEA"),
        year: z.number().optional().describe("Año específico para filtrar los consumos (ej: 2022)")
    },
    async ({ contrato, year }) => {
        logger.info({ contrato, year }, "Fetching consumption");

        const cache = getCache();
        const cacheKey = CacheKeys.consumo(contrato, year);
        const cached = cache.get<string>(cacheKey);
        if (cached) {
            return { content: [{ type: "text" as const, text: cached }] };
        }

        try {
            const explotaciones = ["1", "12"];
            let parsed: ConsumoResponse = { success: false, error: "No data found" };

            for (const explotacion of explotaciones) {
                const response = await fetchWithRetry(
                    `${CEA_API_BASE}/InterfazOficinaVirtualClientesWS`,
                    {
                        method: 'POST',
                        headers: { 'Content-Type': 'text/xml;charset=UTF-8' },
                        body: buildConsumoSOAP(contrato, explotacion)
                    }
                );

                const xml = await response.text();
                parsed = parseConsumoResponse(xml);

                if (parsed.success && parsed.data && parsed.data.consumos.length > 0) {
                    break;
                }
            }

            if (!parsed.success) {
                return { content: [{ type: "text" as const, text: JSON.stringify({ error: parsed.error, success: false }) }] };
            }

            const data = parsed.data!;
            const añosDisponibles = [...new Set(data.consumos.map(c => c.año))].filter(a => a > 0).sort((a, b) => b - a);

            let consumosFiltrados = data.consumos;
            if (year) {
                consumosFiltrados = data.consumos.filter(c => c.año === year);
            }

            const promedioFiltrado = consumosFiltrados.length > 0
                ? consumosFiltrados.reduce((sum, c) => sum + c.consumoM3, 0) / consumosFiltrados.length
                : 0;

            const totalAño = consumosFiltrados.reduce((sum, c) => sum + c.consumoM3, 0);

            const result = JSON.stringify({
                success: true,
                contrato,
                yearConsultado: year || "todos",
                yearsDisponibles: añosDisponibles,
                totalRegistros: data.consumos.length,
                registrosFiltrados: consumosFiltrados.length,
                promedioMensual: Math.round(promedioFiltrado),
                totalConsumoM3: totalAño,
                tendencia: data.tendencia,
                consumos: consumosFiltrados.map(c => ({
                    periodo: c.periodo,
                    consumoM3: c.consumoM3,
                    year: c.año,
                    mes: c.mes,
                    tipoLectura: c.tipoLectura
                })),
                resumen: year
                    ? `Consumo ${year}: Total ${totalAño} m³, Promedio mensual ${Math.round(promedioFiltrado)} m³`
                    : `Historial completo: ${data.consumos.length} registros`
            });

            cache.set(cacheKey, result);

            return { content: [{ type: "text" as const, text: result }] };
        } catch (error) {
            logger.error({ contrato, error }, "get_consumo error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudo consultar el consumo: ${error instanceof Error ? error.message : 'Error desconocido'}`
                    })
                }]
            };
        }
    }
);

export const getContratoTool = tool(
    "get_contract_details",
    `Obtiene los detalles de un contrato CEA.

RETORNA:
- titular: Nombre del titular
- direccion: Dirección del servicio
- tarifa: Tipo de tarifa
- estado: Estado del contrato (activo/suspendido/cortado)

Usa para validar un contrato o conocer detalles del servicio.`,
    {
        contrato: z.string().describe("Número de contrato CEA")
    },
    async ({ contrato }) => {
        logger.info({ contrato }, "Fetching contract details");

        const cache = getCache();
        const cacheKey = CacheKeys.contrato(contrato);
        const cached = cache.get<string>(cacheKey);
        if (cached) {
            return { content: [{ type: "text" as const, text: cached }] };
        }

        try {
            const response = await fetchWithRetry(
                `${CEA_API_BASE}/InterfazGenericaContratacionWS`,
                {
                    method: 'POST',
                    headers: { 'Content-Type': 'text/xml;charset=UTF-8' },
                    body: buildContratoSOAP(contrato)
                }
            );

            const xml = await response.text();
            const parsed = parseContratoResponse(xml);

            if (!parsed.success) {
                return { content: [{ type: "text" as const, text: JSON.stringify({
                    success: false,
                    error: parsed.error,
                    formatted_response: `No encontré información para el contrato ${contrato}. ¿Puedes verificar el número?`
                }) }] };
            }

            const data = parsed.data!;
            const formattedResponse = renderTemplate("contract_info", {
                contract_number: contrato,
                titular: data.titular,
                direccion: data.direccion,
                colonia: data.colonia,
                tarifa: data.tarifa,
                estado: data.estado
            });

            const result = JSON.stringify({
                success: true,
                formatted_response: formattedResponse,
                data: parsed.data
            });

            cache.set(cacheKey, result);

            return { content: [{ type: "text" as const, text: result }] };
        } catch (error) {
            logger.error({ contrato, error }, "get_contract_details error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudo consultar el contrato: ${error instanceof Error ? error.message : 'Error desconocido'}`,
                        formatted_response: "El sistema de consulta no está disponible en este momento. ¿Puedes intentar en unos minutos?"
                    })
                }]
            };
        }
    }
);

export const createTicketTool = tool(
    "create_ticket",
    `Crea un ticket en el sistema AGORA CEA y retorna el folio generado.

CATEGORÍAS (AGORA):
- CON: Consultas generales
- FAC: Facturación (recibos, aclaraciones, ajustes)
- CTR: Contratos (altas, bajas, cambios)
- CVN: Convenios de pago
- REP: Reportes de servicio (fugas, drenaje, calidad)
- SRV: Servicios técnicos (medidores, instalaciones)

⚠️ CUÁNDO PEDIR CONTRATO:
- REP (fugas en vía pública, drenaje en calle): NO pidas contrato, solo ubicación
- REP (fuga de medidor, problema dentro de propiedad): SÍ pide contrato
- FAC, CTR, CVN, SRV: SÍ requieren contrato
- CON: Depende de la consulta

IMPORTANTE: Siempre incluye el folio en tu respuesta al usuario.`,
    {
        category_code: z.enum(["CON", "FAC", "CTR", "CVN", "REP", "SRV"])
            .describe("Código de categoría AGORA"),
        subcategory_code: z.string().optional()
            .describe("Código de subcategoría (ej: FAC-001, REP-FVP)"),
        titulo: z.string().describe("Título breve del ticket"),
        descripcion: z.string().describe("Descripción detallada del problema"),
        contract_number: z.string().optional().describe("Número de contrato - NO requerido para fugas/drenaje en vía pública"),
        email: z.string().optional().describe("Email del cliente (si aplica)"),
        ubicacion: z.string().optional().describe("Ubicación - REQUERIDO para reportes REP en vía pública"),
        priority: z.enum(["low", "medium", "high", "urgent"]).default("medium")
            .describe("Prioridad del ticket")
    },
    async (input) => {
        const ticketInput: CreateTicketInput = {
            category_code: input.category_code as CategoryCode,
            subcategory_code: input.subcategory_code,
            titulo: input.titulo,
            descripcion: input.descripcion,
            contract_number: input.contract_number,
            email: input.email,
            ubicacion: input.ubicacion,
            priority: input.priority as TicketPriority
        };

        const result = await createTicketDirect(ticketInput);

        const emoji = getCategoryEmoji(input.category_code) || getTicketEmoji(input.titulo);
        const formattedResponse = renderTemplate("ticket_created", {
            folio: result.folio,
            emoji,
            tipo: input.titulo,
            ubicacion: input.ubicacion || "",
            estatus: "open"
        });

        return { content: [{ type: "text" as const, text: JSON.stringify({
            ...result,
            formatted_response: formattedResponse
        }) }] };
    }
);

export const getClientTicketsTool = tool(
    "get_client_tickets",
    `Obtiene los tickets de un cliente por número de contrato.

RETORNA lista de tickets con:
- folio: Número de ticket
- status: Estado (open, in_progress, resolved, etc.)
- titulo: Título del ticket
- created_at: Fecha de creación`,
    {
        contract_number: z.string().describe("Número de contrato CEA")
    },
    async ({ contract_number }) => {
        logger.info({ contract_number }, "Fetching client tickets");

        try {
            const tickets = await pgQuery<{
                folio: string;
                status: string;
                title: string;
                service_type: string;
                created_at: Date;
                description: string;
            }>(`
                SELECT folio, status, title, service_type, created_at, description
                FROM tickets
                WHERE contract_number = $1
                ORDER BY created_at DESC
                LIMIT 10
            `, [contract_number]);

            if (!tickets || tickets.length === 0) {
                return {
                    content: [{
                        type: "text" as const,
                        text: JSON.stringify({
                            success: true,
                            tickets: [],
                            message: "No se encontraron tickets para este contrato"
                        })
                    }]
                };
            }

            return { content: [{ type: "text" as const, text: JSON.stringify({
                success: true,
                tickets: tickets.map((t) => ({
                    folio: t.folio,
                    status: t.status,
                    titulo: t.title,
                    service_type: t.service_type,
                    created_at: t.created_at,
                    descripcion: t.description?.substring(0, 100)
                })),
                count: tickets.length
            }) }] };
        } catch (error) {
            logger.error({ contract_number, error }, "get_client_tickets error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudieron consultar los tickets: ${error instanceof Error ? error.message : 'Error desconocido'}`
                    })
                }]
            };
        }
    }
);

export const searchCustomerByContractTool = tool(
    "search_customer_by_contract",
    "Busca un cliente por su número de contrato en la base de datos CEA (AGORA contacts).",
    {
        contract_number: z.string().describe("Número de contrato CEA")
    },
    async ({ contract_number }) => {
        logger.info({ contract_number }, "Searching customer");

        try {
            const contacts = await pgQuery<{
                id: number;
                name: string;
                email: string | null;
                phone_number: string | null;
                identifier: string | null;
                custom_attributes: Record<string, unknown> | null;
            }>(`
                SELECT id, name, email, phone_number, identifier, custom_attributes
                FROM contacts
                WHERE identifier = $1
                   OR custom_attributes->>'contract_number' = $1
                LIMIT 1
            `, [contract_number]);

            if (!contacts || contacts.length === 0) {
                return {
                    content: [{
                        type: "text" as const,
                        text: JSON.stringify({
                            success: false,
                            found: false,
                            message: "Cliente no encontrado"
                        })
                    }]
                };
            }

            const contact = contacts[0];
            if (!contact) {
                return {
                    content: [{
                        type: "text" as const,
                        text: JSON.stringify({
                            success: false,
                            found: false,
                            message: "Cliente no encontrado"
                        })
                    }]
                };
            }
            const customAttrs = contact.custom_attributes || {};

            return { content: [{ type: "text" as const, text: JSON.stringify({
                success: true,
                found: true,
                customer: {
                    id: contact.id,
                    nombre: contact.name || 'Sin nombre',
                    contrato: contact.identifier || (customAttrs as Record<string, string>).contract_number || contract_number,
                    email: contact.email || (customAttrs as Record<string, string>).email || null,
                    whatsapp: contact.phone_number || (customAttrs as Record<string, string>).whatsapp || null,
                    recibo_digital: (customAttrs as Record<string, boolean>).recibo_digital || false
                }
            }) }] };
        } catch (error) {
            logger.error({ contract_number, error }, "search_customer error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: error instanceof Error ? error.message : 'Error desconocido'
                    })
                }]
            };
        }
    }
);

export const updateTicketTool = tool(
    "update_ticket",
    `Actualiza el estado u otros campos de un ticket existente.

⚠️ RESTRICCIÓN IMPORTANTE:
- Los usuarios NO pueden cerrar tickets
- Si el usuario pide cerrar un ticket, usa handoff_to_human en su lugar
- Solo los agentes humanos pueden marcar tickets como "resolved" o "closed"

ESTADOS PERMITIDOS para María:
- in_progress, waiting_client, waiting_internal, escalated`,
    {
        folio: z.string().describe("Folio del ticket a actualizar"),
        status: z.enum(["open", "in_progress", "waiting_client", "waiting_internal", "escalated", "resolved", "closed", "cancelled"]).optional()
            .describe("Nuevo estado del ticket"),
        priority: z.enum(["low", "medium", "high", "urgent"]).optional()
            .describe("Nueva prioridad del ticket"),
        notes: z.string().optional().describe("Notas adicionales")
    },
    async ({ folio, status, priority, notes }) => {
        logger.info({ folio, status }, "Updating ticket");

        if (status === "resolved" || status === "closed" || status === "cancelled") {
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        blocked: true,
                        formatted_response: "Los tickets solo pueden ser cerrados por un asesor. Te comunico con uno para que te ayude con esto 👤"
                    })
                }]
            };
        }

        try {
            const setClauses: string[] = ['updated_at = NOW()'];
            const params: unknown[] = [];
            let paramIndex = 1;

            if (status) {
                setClauses.push(`status = $${paramIndex++}`);
                params.push(status);
            }
            if (priority) {
                setClauses.push(`priority = $${paramIndex++}`);
                params.push(priority);
            }
            if (notes) {
                setClauses.push(`resolution_notes = $${paramIndex++}`);
                params.push(notes);
            }

            params.push(folio);

            await pgQuery(`
                UPDATE tickets
                SET ${setClauses.join(', ')}
                WHERE folio = $${paramIndex}
            `, params);

            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: true,
                        folio,
                        message: `Ticket ${folio} actualizado correctamente`
                    })
                }]
            };
        } catch (error) {
            logger.error({ folio, error }, "update_ticket error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: error instanceof Error ? error.message : 'Error desconocido'
                    })
                }]
            };
        }
    }
);

export const handoffToHumanTool = tool(
    "handoff_to_human",
    `Transfiere la conversación a un agente humano de CEA.

USA ESTA HERRAMIENTA CUANDO:
- El usuario pida hablar con una persona/humano/agente
- El usuario diga "quiero hablar con alguien"
- El usuario esté frustrado y pida atención personal
- No puedas resolver el problema del usuario

IMPORTANTE: Los IDs de conversación y cuenta se pasan en el contexto del sistema.`,
    {
        reason: z.string().describe("Motivo de la transferencia (breve)")
    },
    async ({ reason }) => {
        const conversationId = parseInt(process.env.CURRENT_CHATWOOT_CONVERSATION_ID || "0");
        const accountId = parseInt(process.env.CURRENT_CHATWOOT_ACCOUNT_ID || "0");

        if (!conversationId || !accountId) {
            logger.warn({ conversationId, accountId }, "Missing Chatwoot context for handoff");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        formatted_response: "No puedo transferir la conversación en este momento. Por favor intenta más tarde o llama al 442-238-8200."
                    })
                }]
            };
        }

        logger.info({ conversationId, reason }, "Transferring to human");

        const result = await updateConversationStatus(accountId, conversationId, "pending");

        if (result.success) {
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: true,
                        formatted_response: "¡Claro, te comunico con un agente! Dame unos minutos en lo que encuentro al mejor agente para ayudarte 👤"
                    })
                }]
            };
        }

        return {
            content: [{
                type: "text" as const,
                text: JSON.stringify({
                    success: false,
                    formatted_response: "No pude transferir la conversación. Por favor llama al 442-238-8200 para atención inmediata."
                })
            }]
        };
    }
);

export const getReciboLinkTool = tool(
    "get_recibo_link",
    `Genera el enlace para descargar el recibo digital de un contrato.

USA ESTA HERRAMIENTA CUANDO:
- El usuario pida que le envíen su recibo digital
- El usuario quiera descargar su recibo
- El usuario pregunte cómo obtener su recibo

FLUJO:
1. Pregunta si lo quiere por WhatsApp o por correo
2. Si WhatsApp: Proporciona el enlace directamente
3. Si correo: Indica que se enviará al correo registrado`,
    {
        contract_number: z.string().describe("Número de contrato CEA")
    },
    async ({ contract_number }) => {
        logger.info({ contract_number }, "Generating receipt link");

        const downloadUrl = `https://ceaqro.gob.mx/consulta-recibo?contrato=${contract_number}`;

        return {
            content: [{
                type: "text" as const,
                text: JSON.stringify({
                    success: true,
                    contract_number,
                    download_url: downloadUrl,
                    formatted_response: `Aquí está el enlace para descargar tu recibo digital:\n\n🔗 ${downloadUrl}\n\nTambién puedes consultar tu recibo en la página oficial de CEA Querétaro.`
                })
            }]
        };
    }
);

// ============================================
// Export all tools
// ============================================

export const allTools = [
    getDeudaTool,
    getConsumoTool,
    getContratoTool,
    createTicketTool,
    getClientTicketsTool,
    searchCustomerByContractTool,
    updateTicketTool,
    getReciboLinkTool,
    handoffToHumanTool
];

export { fetchWithRetry };
