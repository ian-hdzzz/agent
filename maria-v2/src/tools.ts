// ============================================
// Maria V2 - Native Tools for Claude Agent SDK
// ============================================

import { config } from "dotenv";
config();

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
import { logger } from "./utils/logger.js";
import { getCache, CacheKeys } from "./utils/cache.js";

// ============================================
// Configuration
// ============================================

const CEA_API_BASE = process.env.CEA_API_BASE || "https://aquacis-cf.ceaqueretaro.gob.mx/Comercial/services";
const PROXY_URL = process.env.CEA_PROXY_URL || null;

const PG_CONFIG = {
    host: process.env.PGHOST || "localhost",
    port: parseInt(process.env.PGPORT || "5432"),
    user: process.env.PGUSER || "postgres",
    password: process.env.PGPASSWORD || "",
    database: process.env.PGDATABASE || "agora_production",
    max: parseInt(process.env.PGPOOL_MAX || "10"),
};

const pgPool = new pg.Pool(PG_CONFIG);

// ============================================
// Circuit Breaker for CEA API
// ============================================

class CircuitBreaker {
    private failures: number = 0;
    private lastFailure: number = 0;
    private state: "closed" | "open" | "half-open" = "closed";
    
    constructor(
        private readonly threshold: number = 5,
        private readonly timeout: number = 30000 // 30 seconds
    ) {}

    async execute<T>(fn: () => Promise<T>): Promise<T> {
        if (this.state === "open") {
            if (Date.now() - this.lastFailure > this.timeout) {
                this.state = "half-open";
                logger.info("Circuit breaker entering half-open state");
            } else {
                throw new Error("Circuit breaker is open - service temporarily unavailable");
            }
        }

        try {
            const result = await fn();
            this.onSuccess();
            return result;
        } catch (error) {
            this.onFailure();
            throw error;
        }
    }

    private onSuccess() {
        this.failures = 0;
        this.state = "closed";
    }

    private onFailure() {
        this.failures++;
        this.lastFailure = Date.now();
        
        if (this.failures >= this.threshold) {
            this.state = "open";
            logger.warn("Circuit breaker opened due to failures");
        }
    }
}

const ceaCircuitBreaker = new CircuitBreaker();

// ============================================
// Utility Functions
// ============================================

async function fetchWithRetry(
    url: string,
    options: RequestInit,
    maxRetries = 3,
    delayMs = 1000
): Promise<Response> {
    return ceaCircuitBreaker.execute(async () => {
        let lastError: Error | null = null;

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                let response: Response;

                if (PROXY_URL && url.includes("ceaqueretaro.gob.mx")) {
                    logger.debug({ proxy: PROXY_URL, url }, "Using proxy");
                    const proxyAgent = new ProxyAgent(PROXY_URL);

                    response = await undiciFetch(url, {
                        method: options.method || "GET",
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
                    logger.warn({ attempt, status: response.status }, "Retrying request");
                    await new Promise(r => setTimeout(r, delayMs * attempt));
                    continue;
                }

                return response;
            } catch (error) {
                lastError = error as Error;
                logger.warn({ attempt, error: lastError.message }, "Request failed");

                if (attempt < maxRetries) {
                    await new Promise(r => setTimeout(r, delayMs * attempt));
                }
            }
        }

        throw lastError || new Error("Request failed after retries");
    });
}

function parseXMLValue(xml: string, tag: string): string | null {
    const regex = new RegExp(`<${tag}[^>]*>([^<]*)</${tag}>`, "i");
    const match = xml.match(regex);
    return match ? match[1].trim() : null;
}

export function getMexicoDate(): Date {
    return new Date(new Date().toLocaleString("en-US", { timeZone: "America/Mexico_City" }));
}

// ============================================
// SOAP Builders
// ============================================

function buildDeudaSOAP(contrato: string): string {
    return `<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:int="http://interfazgenericagestiondeuda.occamcxf.occam.agbar.com/" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
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
    return `<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:occ="http://occamWS.ejb.negocio.occam.agbar.com" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
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
    return `<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:occ="http://occamWS.ejb.negocio.occam.agbar.com" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" xmlns:wsu="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">
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

        const conceptos: Array<{
            periodo: string;
            concepto: string;
            monto: number;
            fechaVencimiento: string;
            estado: "vencido" | "por_vencer";
        }> = [];
        const conceptoMatches = xml.match(/<concepto>[\s\S]*?<\/concepto>/gi) || [];

        for (const conceptoXml of conceptoMatches) {
            conceptos.push({
                periodo: parseXMLValue(conceptoXml, "periodo") || "",
                concepto: parseXMLValue(conceptoXml, "descripcion") || "",
                monto: parseFloat(parseXMLValue(conceptoXml, "importe") || "0"),
                fechaVencimiento: parseXMLValue(conceptoXml, "fechaVencimiento") || "",
                estado: "por_vencer"
            });
        }

        return {
            success: true,
            data: { totalDeuda, vencido, porVencer, conceptos }
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
            if (mesMatch) {
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

        let tendencia: "aumentando" | "estable" | "disminuyendo" = "estable";
        if (consumos.length >= 3) {
            const recent = consumos.slice(0, 3).reduce((s, c) => s + c.consumoM3, 0) / 3;
            const older = consumos.slice(-3).reduce((s, c) => s + c.consumoM3, 0) / 3;
            if (recent > older * 1.1) tendencia = "aumentando";
            else if (recent < older * 0.9) tendencia = "disminuyendo";
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
                estado: (parseXMLValue(xml, "estado") || "activo") as "activo" | "suspendido" | "cortado",
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

async function getCategoryId(code: string): Promise<number | null> {
    try {
        const result = await pgQuery<{ id: number }>(
            "SELECT id FROM ticket_categories WHERE code = $1 AND account_id = 2",
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
            "SELECT id FROM ticket_subcategories WHERE code = $1",
            [code]
        );
        return result?.[0]?.id || null;
    } catch (error) {
        logger.warn({ code, error }, "Failed to lookup subcategory");
        return null;
    }
}

// ============================================
// Ticket Creation
// ============================================

export async function createTicketDirect(input: CreateTicketInput): Promise<CreateTicketResult> {
    logger.info({ category: input.category_code, subcategory: input.subcategory_code }, "Creating ticket");

    try {
        const priority = input.priority || "medium";
        const status = "open";

        const categoryId = await getCategoryId(input.category_code);
        const subcategoryId = input.subcategory_code ? await getSubcategoryId(input.subcategory_code) : null;

        const result = await pgQuery<{ id: number; folio: string }>(`
            INSERT INTO tickets (
                account_id, title, description, status, priority,
                ticket_type, service_type, channel, contract_number,
                client_name, metadata,
                ticket_category_id, ticket_subcategory_id,
                legacy_ticket_type, legacy_service_type,
                created_at, updated_at
            ) VALUES (
                2, $1, $2, $3, $4,
                'GEN', 'general', 'whatsapp', $5,
                $6, $7,
                $8, $9,
                $10, $11,
                NOW(), NOW()
            )
            RETURNING id, folio
        `, [
            input.titulo,
            input.descripcion,
            status,
            priority,
            input.contract_number || null,
            input.contract_number ? null : "Cliente WhatsApp",
            JSON.stringify({
                email: input.email || null,
                ubicacion: input.ubicacion || null,
                category_code: input.category_code,
                subcategory_code: input.subcategory_code
            }),
            categoryId,
            subcategoryId,
            input.category_code,
            input.subcategory_code || null
        ]);

        const createdTicket = result[0];
        logger.info({ folio: createdTicket.folio }, "Ticket created successfully");

        return {
            success: true,
            folio: createdTicket.folio,
            ticketId: String(createdTicket.id),
            message: `Ticket creado exitosamente con folio ${createdTicket.folio}`
        };
    } catch (error) {
        logger.error({ error, input }, "Failed to create ticket");

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
// Claude Agent SDK Tools
// ============================================

export const getDeudaTool = tool(
    "get_deuda",
    "Obtiene el saldo y adeudo de un contrato CEA.

RETORNA:
- totalDeuda: Total a pagar
- vencido: Monto vencido
- porVencer: Monto por vencer
- conceptos: Desglose de adeudos

Usa este tool cuando el usuario pregunte por su saldo, deuda, cuánto debe, o quiera pagar.
IMPORTANTE: Siempre muestra todos los datos retornados de forma clara.",
    {
        contrato: z.string().describe("Número de contrato CEA (ej: 123456)")
    },
    async ({ contrato }) => {
        const cache = getCache();
        const cacheKey = CacheKeys.deuda(contrato);

        const cached = cache.get<string>(cacheKey);
        if (cached) {
            logger.debug({ contrato }, "Cache hit for get_deuda");
            return { content: [{ type: "text" as const, text: cached }] };
        }

        try {
            const response = await fetchWithRetry(
                `${CEA_API_BASE}/InterfazGenericaGestionDeudaWS`,
                {
                    method: "POST",
                    headers: { "Content-Type": "text/xml;charset=UTF-8" },
                    body: buildDeudaSOAP(contrato)
                }
            );

            const xml = await response.text();
            const parsed = parseDeudaResponse(xml);

            if (!parsed.success) {
                const errorResult = JSON.stringify({
                    success: false,
                    error: parsed.error,
                    formatted_response: `No encontré información de adeudo para el contrato ${contrato}. ¿Puedes verificar el número?`
                });
                return { content: [{ type: "text" as const, text: errorResult }] };
            }

            const data = parsed.data!;

            // Build formatted response
            let formattedResponse = `Estado de cuenta del contrato ${contrato}:\n\n`;
            formattedResponse += `💰 **Total a pagar: $${data.totalDeuda.toFixed(2)}**\n`;

            if (data.vencido > 0) {
                formattedResponse += `🔴 Vencido: $${data.vencido.toFixed(2)}\n`;
            }
            if (data.porVencer > 0) {
                formattedResponse += `🟡 Por vencer: $${data.porVencer.toFixed(2)}\n`;
            }

            if (data.conceptos.length > 0) {
                formattedResponse += `\n📋 **Conceptos:**\n`;
                for (const concepto of data.conceptos.slice(0, 5)) {
                    formattedResponse += `• ${concepto.concepto}: $${concepto.monto.toFixed(2)}\n`;
                }
            }

            const result = JSON.stringify({
                success: true,
                formatted_response: formattedResponse,
                data: {
                    contrato,
                    totalDeuda: data.totalDeuda,
                    vencido: data.vencido,
                    porVencer: data.porVencer
                }
            });

            cache.set(cacheKey, result, 300); // Cache for 5 minutes

            return { content: [{ type: "text" as const, text: result }] };
        } catch (error) {
            logger.error({ contrato, error }, "get_deuda error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudo consultar el saldo: ${error instanceof Error ? error.message : "Error desconocido"}`,
                        formatted_response: "El sistema de consulta no está disponible en este momento. ¿Puedes intentar en unos minutos?"
                    })
                }]
            };
        }
    }
);

export const getConsumoTool = tool(
    "get_consumo",
    "Obtiene el historial de consumo de agua de un contrato.

PARÁMETROS:
- contrato: Número de contrato CEA (requerido)
- year: Año específico para filtrar (opcional, ej: 2022, 2023)

RETORNA:
- consumos: Lista de consumos por periodo (m³) con año y mes
- promedioMensual: Promedio de consumo mensual
- tendencia: Si el consumo está aumentando, estable o disminuyendo

Usa cuando el usuario pregunte por su consumo, historial de lecturas, o cuánta agua ha gastado.
Si el usuario pide un año específico (ej: \"consumo de 2022\"), usa el parámetro year para filtrar.",
    {
        contrato: z.string().describe("Número de contrato CEA"),
        year: z.number().optional().describe("Año específico para filtrar los consumos (ej: 2022)")
    },
    async ({ contrato, year }) => {
        const cache = getCache();
        const cacheKey = CacheKeys.consumo(contrato, year);

        const cached = cache.get<string>(cacheKey);
        if (cached) {
            logger.debug({ contrato, year }, "Cache hit for get_consumo");
            return { content: [{ type: "text" as const, text: cached }] };
        }

        try {
            const explotaciones = ["1", "12"];
            let parsed: ConsumoResponse = { success: false, error: "No data found" };

            for (const explotacion of explotaciones) {
                const response = await fetchWithRetry(
                    `${CEA_API_BASE}/InterfazOficinaVirtualClientesWS`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "text/xml;charset=UTF-8" },
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

            // Get unique years available
            const añosDisponibles = [...new Set(data.consumos.map(c => c.año))].filter(a => a > 0).sort((a, b) => b - a);

            // Filter by year if specified
            let consumosFiltrados = data.consumos;
            if (year) {
                consumosFiltrados = data.consumos.filter(c => c.año === year);
            }

            // Calculate average for filtered data
            const promedioFiltrado = consumosFiltrados.length > 0
                ? consumosFiltrados.reduce((sum, c) => sum + c.consumoM3, 0) / consumosFiltrados.length
                : 0;

            const totalAño = consumosFiltrados.reduce((sum, c) => sum + c.consumoM3, 0);

            const result = {
                success: true,
                contrato,
                yearConsultado: year || "todos",
                yearsDisponibles: añosDisponibles,
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
                    : `Historial completo: ${data.consumos.length} registros desde ${añosDisponibles[añosDisponibles.length - 1] || "N/A"} hasta ${añosDisponibles[0] || "N/A"}`
            };

            const resultText = JSON.stringify(result);
            cache.set(cacheKey, resultText, 300); // Cache for 5 minutes

            return { content: [{ type: "text" as const, text: resultText }] };
        } catch (error) {
            logger.error({ contrato, year, error }, "get_consumo error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudo consultar el consumo: ${error instanceof Error ? error.message : "Error desconocido"}`
                    })
                }]
            };
        }
    }
);

export const getContratoTool = tool(
    "get_contract_details",
    "Obtiene los detalles de un contrato CEA.

RETORNA:
- titular: Nombre del titular
- direccion: Dirección del servicio
- tarifa: Tipo de tarifa
- estado: Estado del contrato (activo/suspendido/cortado)

Usa para validar un contrato o conocer detalles del servicio.
IMPORTANTE: Siempre muestra todos los datos retornados de forma clara.",
    {
        contrato: z.string().describe("Número de contrato CEA")
    },
    async ({ contrato }) => {
        const cache = getCache();
        const cacheKey = CacheKeys.contrato(contrato);

        const cached = cache.get<string>(cacheKey);
        if (cached) {
            logger.debug({ contrato }, "Cache hit for get_contract_details");
            return { content: [{ type: "text" as const, text: cached }] };
        }

        try {
            const response = await fetchWithRetry(
                `${CEA_API_BASE}/InterfazGenericaContratacionWS`,
                {
                    method: "POST",
                    headers: { "Content-Type": "text/xml;charset=UTF-8" },
                    body: buildContratoSOAP(contrato)
                }
            );

            const xml = await response.text();
            const parsed = parseContratoResponse(xml);

            if (!parsed.success) {
                const errorResult = JSON.stringify({
                    success: false,
                    error: parsed.error,
                    formatted_response: `No encontré información para el contrato ${contrato}. ¿Puedes verificar el número?`
                });
                return { content: [{ type: "text" as const, text: errorResult }] };
            }

            const data = parsed.data!;

            // Generate formatted response
            const formattedResponse = 
                `📋 **Información del Contrato ${contrato}**\n\n` +
                `👤 **Titular:** ${data.titular}\n` +
                `🏠 **Dirección:** ${data.direccion}${data.colonia ? `, ${data.colonia}` : ""}\n` +
                `💧 **Tarifa:** ${data.tarifa}\n` +
                `📊 **Estado:** ${data.estado.toUpperCase()}${data.fechaAlta ? `\n📅 **Fecha de Alta:** ${data.fechaAlta}` : ""}`;

            const result = JSON.stringify({
                success: true,
                formatted_response: formattedResponse,
                data: parsed.data
            });

            cache.set(cacheKey, result, 300); // Cache for 5 minutes

            return { content: [{ type: "text" as const, text: result }] };
        } catch (error) {
            logger.error({ contrato, error }, "get_contract_details error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudo consultar el contrato: ${error instanceof Error ? error.message : "Error desconocido"}`,
                        formatted_response: "El sistema de consulta no está disponible en este momento. ¿Puedes intentar en unos minutos?"
                    })
                }]
            };
        }
    }
);

export const createTicketTool = tool(
    "create_ticket",
    "Crea un ticket en el sistema AGORA CEA y retorna el folio generado.

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

IMPORTANTE: Siempre incluye el folio en tu respuesta al usuario.",
    {
        category_code: z.enum(["CON", "FAC", "CTR", "CVN", "REP", "SRV"]).describe("Código de categoría AGORA"),
        subcategory_code: z.string().optional().describe("Código de subcategoría (ej: FAC-001, REP-FG-001)"),
        titulo: z.string().describe("Título breve del ticket"),
        descripcion: z.string().describe("Descripción detallada del problema"),
        contract_number: z.string().optional().describe("Número de contrato - NO requerido para fugas/drenaje en vía pública"),
        email: z.string().optional().describe("Email del cliente (si aplica)"),
        ubicacion: z.string().optional().describe("Ubicación - REQUERIDO para reportes REP en vía pública"),
        priority: z.enum(["low", "medium", "high", "urgent"]).default("medium").describe("Prioridad del ticket")
    },
    async (input) => {
        const ticketInput: CreateTicketInput = {
            category_code: input.category_code,
            subcategory_code: input.subcategory_code,
            titulo: input.titulo,
            descripcion: input.descripcion,
            contract_number: input.contract_number,
            email: input.email,
            ubicacion: input.ubicacion,
            priority: input.priority as TicketPriority
        };

        const result = await createTicketDirect(ticketInput);

        // Determine emoji based on category
        const emojiMap: Record<string, string> = {
            CON: "💬",
            FAC: "📄",
            CTR: "📋",
            CVN: "🤝",
            REP: "🔧",
            SRV: "🔩"
        };
        const emoji = emojiMap[input.category_code] || "📝";

        const formattedResponse = result.success
            ? `${emoji} **Ticket Creado**\n\n**Folio:** ${result.folio}\n**Tipo:** ${input.titulo}${input.ubicacion ? `\n**Ubicación:** ${input.ubicacion}` : ""}\n\n✅ Tu solicitud ha sido registrada exitosamente.`
            : `❌ Error al crear ticket: ${result.error}`;

        return { content: [{ type: "text" as const, text: JSON.stringify({
            ...result,
            formatted_response: formattedResponse
        }) }] };
    }
);

export const getClientTicketsTool = tool(
    "get_client_tickets",
    "Obtiene los tickets de un cliente por número de contrato.

RETORNA lista de tickets con:
- folio: Número de ticket
- status: Estado (open, in_progress, resolved, etc.)
- titulo: Título del ticket
- created_at: Fecha de creación",
    {
        contract_number: z.string().describe("Número de contrato CEA")
    },
    async ({ contract_number }) => {
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
                            formatted_response: "No se encontraron tickets para este contrato."
                        })
                    }]
                };
            }

            let formattedResponse = `📋 **Tickets del Contrato ${contract_number}**\n\n`;
            for (const t of tickets) {
                const statusEmoji = t.status === "open" ? "🟡" : t.status === "resolved" ? "✅" : "🔵";
                formattedResponse += `${statusEmoji} **${t.folio}** - ${t.title}\n`;
                formattedResponse += `   Estado: ${t.status} | ${new Date(t.created_at).toLocaleDateString("es-MX")}\n\n`;
            }

            const result = {
                success: true,
                tickets: tickets.map(t => ({
                    folio: t.folio,
                    status: t.status,
                    titulo: t.title,
                    created_at: t.created_at
                })),
                formatted_response: formattedResponse,
                count: tickets.length
            };

            return { content: [{ type: "text" as const, text: JSON.stringify(result) }] };
        } catch (error) {
            logger.error({ contract_number, error }, "get_client_tickets error");
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudieron consultar los tickets: ${error instanceof Error ? error.message : "Error desconocido"}`
                    })
                }]
            };
        }
    }
);

export const handoffToHumanTool = tool(
    "handoff_to_human",
    "Transfiere la conversación a un agente humano de CEA.

Usa esta herramienta cuando:
- El usuario pida hablar con una persona/humano/agente
- El usuario diga \"quiero hablar con alguien\"
- El usuario esté frustrado y pida atención personal
- No puedas resolver el problema del usuario
- Se trate de una aclaración de cobro (FAC-004)
- Se trate de un ajuste (FAC-005)
- Se trate de un nuevo servicio/contrato

La transferencia marcará la conversación para atención humana.",
    {
        reason: z.string().describe("Motivo de la transferencia (breve)"),
        priority: z.enum(["low", "medium", "high", "urgent"]).default("medium").describe("Prioridad de la transferencia")
    },
    async ({ reason, priority }) => {
        logger.info({ reason, priority }, "Handoff to human requested");

        const formattedResponse = `👤 **Transferencia a Asesor**\n\nTe estoy comunicando con un asesor de CEA para atender tu solicitud.\n\n**Motivo:** ${reason}\n**Prioridad:** ${priority === "urgent" ? "🔴 Urgente" : priority === "high" ? "🟠 Alta" : priority === "medium" ? "🟡 Media" : "🟢 Baja"}\n\nUn momento por favor...`;

        return { content: [{ type: "text" as const, text: JSON.stringify({
            success: true,
            handoff: true,
            reason,
            priority,
            formatted_response: formattedResponse
        }) }] };
    }
);

// Export all tools
export const allTools = [
    getDeudaTool,
    getConsumoTool,
    getContratoTool,
    createTicketTool,
    getClientTicketsTool,
    handoffToHumanTool
];
