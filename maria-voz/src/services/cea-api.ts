/**
 * CEA SOAP API client for maria-voz
 * Adapted from maria-claude/src/tools.ts
 */

import { ProxyAgent, fetch as undiciFetch } from "undici";

// Configuration
const CEA_API_BASE = "https://aquacis-cf.ceaqueretaro.gob.mx/Comercial/services";
const PROXY_URL = process.env.CEA_PROXY_URL || null;

// Types
export interface DeudaData {
  totalDeuda: number;
  vencido: number;
  porVencer: number;
  facturas: Array<{
    periodo: string;
    importe: number;
    estado: "vencido" | "pendiente";
  }>;
}

export interface ConsumoData {
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

export interface ContratoData {
  numeroContrato: string;
  titular: string;
  direccion: string;
  colonia: string;
  tarifa: string;
  estado: "activo" | "suspendido" | "cortado";
}

// Utility: Fetch with retry and proxy support
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

      if (PROXY_URL && url.includes("ceaqueretaro.gob.mx")) {
        console.log(`[CEA-API] Using proxy: ${PROXY_URL}`);
        const proxyAgent = new ProxyAgent(PROXY_URL);

        response = (await undiciFetch(url, {
          method: options.method || "GET",
          headers: options.headers as Record<string, string>,
          body: options.body as string,
          dispatcher: proxyAgent,
          signal: AbortSignal.timeout(30000),
        })) as unknown as Response;
      } else {
        response = await fetch(url, {
          ...options,
          signal: AbortSignal.timeout(30000),
        });
      }

      if (!response.ok && attempt < maxRetries) {
        console.warn(`[CEA-API] Attempt ${attempt} failed with status ${response.status}, retrying...`);
        await new Promise((r) => setTimeout(r, delayMs * attempt));
        continue;
      }

      return response;
    } catch (error) {
      lastError = error as Error;
      console.warn(`[CEA-API] Attempt ${attempt} error: ${lastError.message}`);

      if (attempt < maxRetries) {
        await new Promise((r) => setTimeout(r, delayMs * attempt));
      }
    }
  }

  throw lastError || new Error("Request failed after retries");
}

// Utility: Parse XML value
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

// Response parsers
function parseFacturasResponse(xml: string): Array<{ periodo: string; importe: number; estado: "vencido" | "pendiente" }> {
  const facturas: Array<{ periodo: string; importe: number; estado: "vencido" | "pendiente" }> = [];
  const facturaMatches = xml.match(/<Factura>[\s\S]*?<\/Factura>/g) || [];

  const meses = [
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
  ];

  for (const facturaXml of facturaMatches) {
    const estadoNum = parseInt(parseXMLValue(facturaXml, "estado") || "0");

    // Only include unpaid invoices (estado 2=pendiente, 4=vencido)
    if (estadoNum === 2 || estadoNum === 4) {
      const periodo = parseXMLValue(facturaXml, "periodo") || "";
      const año = parseXMLValue(facturaXml, "año") || "";
      const periodoTexto = `${meses[parseInt(periodo)] || periodo} ${año}`;

      facturas.push({
        periodo: periodoTexto,
        importe: parseFloat(parseXMLValue(facturaXml, "importeTotal") || "0"),
        estado: estadoNum === 4 ? "vencido" : "pendiente",
      });
    }
  }

  return facturas;
}

// API Functions

/**
 * Get debt/balance for a contract
 */
export async function getDeuda(contrato: string): Promise<{ success: boolean; data?: DeudaData; error?: string }> {
  console.log(`[CEA-API] getDeuda for contract: ${contrato}`);

  try {
    const response = await fetchWithRetry(`${CEA_API_BASE}/InterfazGenericaGestionDeudaWS`, {
      method: "POST",
      headers: { "Content-Type": "text/xml;charset=UTF-8" },
      body: buildDeudaSOAP(contrato),
    });

    const xml = await response.text();

    if (xml.includes("<faultstring>") || xml.includes("<error>")) {
      const faultMsg = parseXMLValue(xml, "faultstring") || parseXMLValue(xml, "error") || "Error desconocido";
      return { success: false, error: faultMsg };
    }

    const totalDeuda = parseFloat(
      parseXMLValue(xml, "deudaTotal") || parseXMLValue(xml, "importeTotal") || parseXMLValue(xml, "totalDeuda") || "0"
    );
    const vencido = parseFloat(parseXMLValue(xml, "saldoAnteriorTotal") || parseXMLValue(xml, "importeVencido") || "0");
    const porVencer = parseFloat(parseXMLValue(xml, "deuda") || parseXMLValue(xml, "importePorVencer") || "0");

    // Fetch invoice details if there's debt
    let facturas: Array<{ periodo: string; importe: number; estado: "vencido" | "pendiente" }> = [];

    if (totalDeuda > 0) {
      const facturasResponse = await fetchWithRetry(`${CEA_API_BASE}/InterfazOficinaVirtualClientesWS`, {
        method: "POST",
        headers: { "Content-Type": "text/xml;charset=UTF-8" },
        body: buildFacturasSOAP(contrato, "1"),
      });

      const facturasXml = await facturasResponse.text();
      facturas = parseFacturasResponse(facturasXml);
    }

    // Calculate vencido and porVencer from invoices
    let vencidoCalculado = 0;
    let porVencerCalculado = 0;
    for (const factura of facturas) {
      if (factura.estado === "vencido") {
        vencidoCalculado += factura.importe;
      } else {
        porVencerCalculado += factura.importe;
      }
    }

    return {
      success: true,
      data: {
        totalDeuda,
        vencido: vencidoCalculado || vencido,
        porVencer: porVencerCalculado || porVencer,
        facturas,
      },
    };
  } catch (error) {
    console.error(`[CEA-API] getDeuda error:`, error);
    return { success: false, error: error instanceof Error ? error.message : "Error desconocido" };
  }
}

/**
 * Get consumption history for a contract
 */
export async function getConsumo(
  contrato: string,
  year?: number
): Promise<{ success: boolean; data?: ConsumoData; error?: string }> {
  console.log(`[CEA-API] getConsumo for contract: ${contrato}, year: ${year || "all"}`);

  try {
    // Try explotacion=1 first, then 12 if no data
    const explotaciones = ["1", "12"];
    let consumos: ConsumoData["consumos"] = [];

    for (const explotacion of explotaciones) {
      const response = await fetchWithRetry(`${CEA_API_BASE}/InterfazOficinaVirtualClientesWS`, {
        method: "POST",
        headers: { "Content-Type": "text/xml;charset=UTF-8" },
        body: buildConsumoSOAP(contrato, explotacion),
      });

      const xml = await response.text();

      if (xml.includes("<faultstring>") || xml.includes("<error>")) {
        continue;
      }

      const consumoMatches =
        xml.match(/<Consumo>[\s\S]*?<\/Consumo>/g) ||
        xml.match(/<consumo>[\s\S]*?<\/consumo>/gi) ||
        xml.match(/<lectura>[\s\S]*?<\/lectura>/gi) ||
        [];

      for (const consumoXml of consumoMatches) {
        const año = parseInt(parseXMLValue(consumoXml, "año") || "0");
        const metrosCubicos = parseFloat(
          parseXMLValue(consumoXml, "metrosCubicos") || parseXMLValue(consumoXml, "consumo") || parseXMLValue(consumoXml, "m3") || "0"
        );
        const periodo = parseXMLValue(consumoXml, "periodo") || "";
        const estimado = parseXMLValue(consumoXml, "estimado") === "true";

        // Extract month from periodo like "<JUN> - <JUN>"
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

      if (consumos.length > 0) break;
    }

    if (consumos.length === 0) {
      return { success: false, error: "No se encontró historial de consumo" };
    }

    // Filter by year if specified
    if (year) {
      consumos = consumos.filter((c) => c.año === year);
    }

    // Calculate average
    const promedioMensual = consumos.length > 0 ? consumos.reduce((sum, c) => sum + c.consumoM3, 0) / consumos.length : 0;

    // Calculate trend
    let tendencia: "aumentando" | "estable" | "disminuyendo" = "estable";
    if (consumos.length >= 3) {
      const recent = consumos.slice(0, 3).reduce((s, c) => s + c.consumoM3, 0) / 3;
      const older = consumos.slice(-3).reduce((s, c) => s + c.consumoM3, 0) / 3;
      if (recent > older * 1.1) tendencia = "aumentando";
      else if (recent < older * 0.9) tendencia = "disminuyendo";
    }

    return {
      success: true,
      data: {
        consumos,
        promedioMensual: Math.round(promedioMensual),
        tendencia,
      },
    };
  } catch (error) {
    console.error(`[CEA-API] getConsumo error:`, error);
    return { success: false, error: error instanceof Error ? error.message : "Error desconocido" };
  }
}

/**
 * Get contract details
 */
export async function getContractDetails(contrato: string): Promise<{ success: boolean; data?: ContratoData; error?: string }> {
  console.log(`[CEA-API] getContractDetails for contract: ${contrato}`);

  try {
    const response = await fetchWithRetry(`${CEA_API_BASE}/InterfazGenericaContratacionWS`, {
      method: "POST",
      headers: { "Content-Type": "text/xml;charset=UTF-8" },
      body: buildContratoSOAP(contrato),
    });

    const xml = await response.text();

    if (xml.includes("<faultstring>") || xml.includes("<error>")) {
      const faultMsg = parseXMLValue(xml, "faultstring") || parseXMLValue(xml, "error") || "Error desconocido";
      return { success: false, error: faultMsg };
    }

    // Build address from calle + numero
    const calle = parseXMLValue(xml, "calle") || "";
    const numero = parseXMLValue(xml, "numero") || "";
    const direccion = [calle, numero].filter(Boolean).join(" ");

    return {
      success: true,
      data: {
        numeroContrato: parseXMLValue(xml, "numeroContrato") || parseXMLValue(xml, "contrato") || "",
        titular: parseXMLValue(xml, "nombreTitular") || parseXMLValue(xml, "titular") || "",
        direccion,
        colonia: parseXMLValue(xml, "municipio") || parseXMLValue(xml, "colonia") || "",
        tarifa: parseXMLValue(xml, "descUso") || parseXMLValue(xml, "tarifa") || "",
        estado: (parseXMLValue(xml, "estado") || "activo") as "activo" | "suspendido" | "cortado",
      },
    };
  } catch (error) {
    console.error(`[CEA-API] getContractDetails error:`, error);
    return { success: false, error: error instanceof Error ? error.message : "Error desconocido" };
  }
}
