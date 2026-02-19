/**
 * CEA Tools MCP Server
 *
 * Provides tools for interacting with CEA Queretaro SOAP APIs:
 * - get_deuda: Get debt/balance for a contract
 * - get_consumo: Get consumption history
 * - get_contract_details: Get contract information
 * - get_recibo_link: Get digital receipt download link
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import express from "express";
import { ProxyAgent, fetch as undiciFetch } from "undici";

// Configuration
const CEA_API_BASE =
  process.env.CEA_API_URL ||
  "https://aquacis-cf.ceaqueretaro.gob.mx/Comercial/services";
const PROXY_URL = process.env.CEA_PROXY_URL || null;

// Utility Functions
async function fetchWithRetry(
  url: string,
  options: {
    method?: string;
    headers?: Record<string, string>;
    body?: string;
  },
  maxRetries = 3,
  delayMs = 1000
): Promise<Response> {
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      let response: Response;

      if (PROXY_URL && url.includes("ceaqueretaro.gob.mx")) {
        const proxyAgent = new ProxyAgent(PROXY_URL);
        response = (await undiciFetch(url, {
          method: options.method || "GET",
          headers: options.headers,
          body: options.body,
          dispatcher: proxyAgent,
          // @ts-ignore
          signal: AbortSignal.timeout(30000),
        })) as unknown as Response;
      } else {
        response = await fetch(url, {
          ...options,
          signal: AbortSignal.timeout(30000),
        });
      }

      if (!response.ok && attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, delayMs * attempt));
        continue;
      }

      return response;
    } catch (error) {
      lastError = error as Error;
      if (attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, delayMs * attempt));
      }
    }
  }

  throw lastError || new Error("Request failed after retries");
}

function parseXMLValue(xml: string, tag: string): string | null {
  const regex = new RegExp(`<${tag}[^>]*>([^<]*)</${tag}>`, "i");
  const match = xml.match(regex);
  return match ? match[1].trim() : null;
}

// SOAP Builders
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

// Response Parsers
interface DeudaData {
  totalDeuda: number;
  vencido: number;
  porVencer: number;
}

function parseDeudaResponse(
  xml: string
): { success: true; data: DeudaData } | { success: false; error: string } {
  try {
    if (xml.includes("<faultstring>") || xml.includes("<error>")) {
      const faultMsg =
        parseXMLValue(xml, "faultstring") ||
        parseXMLValue(xml, "error") ||
        "Error desconocido";
      return { success: false, error: faultMsg };
    }

    const totalDeuda = parseFloat(
      parseXMLValue(xml, "deudaTotal") ||
        parseXMLValue(xml, "importeTotal") ||
        "0"
    );
    const vencido = parseFloat(
      parseXMLValue(xml, "saldoAnteriorTotal") ||
        parseXMLValue(xml, "importeVencido") ||
        "0"
    );
    const porVencer = parseFloat(
      parseXMLValue(xml, "deuda") ||
        parseXMLValue(xml, "importePorVencer") ||
        "0"
    );

    return { success: true, data: { totalDeuda, vencido, porVencer } };
  } catch (error) {
    return { success: false, error: `Error parsing response: ${error}` };
  }
}

interface ConsumoData {
  consumos: Array<{
    periodo: string;
    consumoM3: number;
    año: number;
    mes: string;
    tipoLectura: "real" | "estimada";
  }>;
  promedioMensual: number;
  tendencia: "aumentando" | "estable" | "disminuyendo";
}

function parseConsumoResponse(
  xml: string
): { success: true; data: ConsumoData } | { success: false; error: string } {
  try {
    if (xml.includes("<faultstring>") || xml.includes("<error>")) {
      const faultMsg =
        parseXMLValue(xml, "faultstring") ||
        parseXMLValue(xml, "error") ||
        "Error desconocido";
      return { success: false, error: faultMsg };
    }

    const consumos: ConsumoData["consumos"] = [];
    const consumoMatches =
      xml.match(/<Consumo>[\s\S]*?<\/Consumo>/g) ||
      xml.match(/<consumo>[\s\S]*?<\/consumo>/gi) ||
      [];

    for (const consumoXml of consumoMatches) {
      const año = parseInt(parseXMLValue(consumoXml, "año") || "0");
      const metrosCubicos = parseFloat(
        parseXMLValue(consumoXml, "metrosCubicos") ||
          parseXMLValue(consumoXml, "consumo") ||
          "0"
      );
      const periodo = parseXMLValue(consumoXml, "periodo") || "";
      const estimado = parseXMLValue(consumoXml, "estimado") === "true";

      let mes = "";
      const mesMatch = periodo.match(/<([A-Z]{3})>/);
      if (mesMatch) {
        mes = mesMatch[1];
      }

      consumos.push({
        periodo: `${mes} ${año}`,
        consumoM3: metrosCubicos,
        año,
        mes,
        tipoLectura: estimado ? "estimada" : "real",
      });
    }

    const promedioMensual =
      consumos.length > 0
        ? consumos.reduce((sum, c) => sum + c.consumoM3, 0) / consumos.length
        : 0;

    let tendencia: "aumentando" | "estable" | "disminuyendo" = "estable";
    if (consumos.length >= 3) {
      const recent =
        consumos.slice(0, 3).reduce((s, c) => s + c.consumoM3, 0) / 3;
      const older =
        consumos.slice(-3).reduce((s, c) => s + c.consumoM3, 0) / 3;
      if (recent > older * 1.1) tendencia = "aumentando";
      else if (recent < older * 0.9) tendencia = "disminuyendo";
    }

    return { success: true, data: { consumos, promedioMensual, tendencia } };
  } catch (error) {
    return { success: false, error: `Error parsing response: ${error}` };
  }
}

interface ContratoData {
  numeroContrato: string;
  titular: string;
  direccion: string;
  colonia: string;
  tarifa: string;
  estado: "activo" | "suspendido" | "cortado";
}

function parseContratoResponse(
  xml: string
): { success: true; data: ContratoData } | { success: false; error: string } {
  try {
    if (xml.includes("<faultstring>") || xml.includes("<error>")) {
      const faultMsg =
        parseXMLValue(xml, "faultstring") ||
        parseXMLValue(xml, "error") ||
        "Error desconocido";
      return { success: false, error: faultMsg };
    }

    const calle = parseXMLValue(xml, "calle") || "";
    const numero = parseXMLValue(xml, "numero") || "";
    const direccion = [calle, numero].filter(Boolean).join(" ");

    return {
      success: true,
      data: {
        numeroContrato:
          parseXMLValue(xml, "numeroContrato") ||
          parseXMLValue(xml, "contrato") ||
          "",
        titular:
          parseXMLValue(xml, "nombreTitular") ||
          parseXMLValue(xml, "titular") ||
          "",
        direccion,
        colonia:
          parseXMLValue(xml, "municipio") ||
          parseXMLValue(xml, "colonia") ||
          "",
        tarifa:
          parseXMLValue(xml, "descUso") || parseXMLValue(xml, "tarifa") || "",
        estado: (parseXMLValue(xml, "estado") || "activo") as
          | "activo"
          | "suspendido"
          | "cortado",
      },
    };
  } catch (error) {
    return { success: false, error: `Error parsing response: ${error}` };
  }
}

// Create MCP Server
const server = new Server(
  {
    name: "cea-tools",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List Tools Handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "get_deuda",
        description:
          "Obtiene el saldo y adeudo de un contrato CEA. Retorna: totalDeuda, vencido, porVencer.",
        inputSchema: {
          type: "object",
          properties: {
            contrato: {
              type: "string",
              description: "Número de contrato CEA (ej: 123456)",
            },
          },
          required: ["contrato"],
        },
      },
      {
        name: "get_consumo",
        description:
          "Obtiene el historial de consumo de agua de un contrato. Retorna consumos mensuales en m³.",
        inputSchema: {
          type: "object",
          properties: {
            contrato: {
              type: "string",
              description: "Número de contrato CEA",
            },
            year: {
              type: "number",
              description: "Año específico para filtrar (opcional)",
            },
          },
          required: ["contrato"],
        },
      },
      {
        name: "get_contract_details",
        description:
          "Obtiene los detalles de un contrato CEA: titular, dirección, tarifa, estado.",
        inputSchema: {
          type: "object",
          properties: {
            contrato: {
              type: "string",
              description: "Número de contrato CEA",
            },
          },
          required: ["contrato"],
        },
      },
      {
        name: "get_recibo_link",
        description: "Genera el enlace para descargar el recibo digital de un contrato.",
        inputSchema: {
          type: "object",
          properties: {
            contract_number: {
              type: "string",
              description: "Número de contrato CEA",
            },
          },
          required: ["contract_number"],
        },
      },
    ],
  };
});

// Call Tool Handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "get_deuda": {
        const contrato = (args as { contrato: string }).contrato;
        const response = await fetchWithRetry(
          `${CEA_API_BASE}/InterfazGenericaGestionDeudaWS`,
          {
            method: "POST",
            headers: { "Content-Type": "text/xml;charset=UTF-8" },
            body: buildDeudaSOAP(contrato),
          }
        );
        const xml = await response.text();
        const parsed = parseDeudaResponse(xml);

        if (!parsed.success) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ success: false, error: parsed.error }),
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                contrato,
                ...parsed.data,
              }),
            },
          ],
        };
      }

      case "get_consumo": {
        const { contrato, year } = args as { contrato: string; year?: number };

        // Try explotacion=1 first, then 12
        let parsed: ReturnType<typeof parseConsumoResponse> = {
          success: false,
          error: "No data",
        };

        for (const explotacion of ["1", "12"]) {
          const response = await fetchWithRetry(
            `${CEA_API_BASE}/InterfazOficinaVirtualClientesWS`,
            {
              method: "POST",
              headers: { "Content-Type": "text/xml;charset=UTF-8" },
              body: buildConsumoSOAP(contrato, explotacion),
            }
          );
          const xml = await response.text();
          parsed = parseConsumoResponse(xml);

          if (parsed.success && parsed.data.consumos.length > 0) {
            break;
          }
        }

        if (!parsed.success) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ success: false, error: parsed.error }),
              },
            ],
          };
        }

        let filteredConsumos = parsed.data.consumos;
        if (year) {
          filteredConsumos = parsed.data.consumos.filter((c) => c.año === year);
        }

        const promedioFiltrado =
          filteredConsumos.length > 0
            ? filteredConsumos.reduce((sum, c) => sum + c.consumoM3, 0) /
              filteredConsumos.length
            : 0;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                contrato,
                year: year || "all",
                consumos: filteredConsumos,
                promedioMensual: Math.round(promedioFiltrado),
                tendencia: parsed.data.tendencia,
              }),
            },
          ],
        };
      }

      case "get_contract_details": {
        const contrato = (args as { contrato: string }).contrato;
        const response = await fetchWithRetry(
          `${CEA_API_BASE}/InterfazGenericaContratacionWS`,
          {
            method: "POST",
            headers: { "Content-Type": "text/xml;charset=UTF-8" },
            body: buildContratoSOAP(contrato),
          }
        );
        const xml = await response.text();
        const parsed = parseContratoResponse(xml);

        if (!parsed.success) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({ success: false, error: parsed.error }),
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({ success: true, ...parsed.data }),
            },
          ],
        };
      }

      case "get_recibo_link": {
        const contractNumber = (args as { contract_number: string })
          .contract_number;
        const downloadUrl = `https://ceaqro.gob.mx/consulta-recibo?contrato=${contractNumber}`;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                contract_number: contractNumber,
                download_url: downloadUrl,
              }),
            },
          ],
        };
      }

      default:
        return {
          content: [
            { type: "text", text: JSON.stringify({ error: "Unknown tool" }) },
          ],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error",
          }),
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const app = express();
  const PORT = parseInt(process.env.PORT || "3000");

  const transports = new Map<string, SSEServerTransport>();

  app.get("/sse", async (req, res) => {
    const transport = new SSEServerTransport("/messages", res);
    transports.set(transport.sessionId, transport);
    res.on("close", () => transports.delete(transport.sessionId));
    await server.connect(transport);
  });

  app.post("/messages", express.json(), async (req, res) => {
    const sessionId = req.query.sessionId as string;
    const transport = transports.get(sessionId);
    if (transport) {
      await transport.handlePostMessage(req, res);
    } else {
      res.status(400).json({ error: "No active SSE connection for this session" });
    }
  });

  app.get("/health", (_req, res) => {
    res.json({ status: "ok", name: "cea-tools", version: "1.0.0" });
  });

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`CEA Tools MCP Server running on http://0.0.0.0:${PORT}`);
  });
}

main().catch(console.error);
