/**
 * Tool registry for maria-voz
 */

import { consultarSaldo } from "./consultar-saldo.js";
import { consultarConsumo } from "./consultar-consumo.js";
import { consultarContrato } from "./consultar-contrato.js";
import { consultarTickets } from "./consultar-tickets.js";
import { crearReporte } from "./crear-reporte.js";
import { transferirHumano } from "./transferir-humano.js";

// Tool type definition
export interface ToolResult {
  success: boolean;
  response: string;
  data?: unknown;
  action?: string;
  metadata?: Record<string, unknown>;
  // Dynamic variables for ElevenLabs SIP transfer headers
  // These are accumulated during the conversation and passed to AGORA on transfer
  intent?: string;
  transfer_notes?: string;
  contrato?: string;
  customer_name?: string;
}

// Tool function type - uses any for flexibility with webhook inputs
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type ToolFunction = (input: any) => Promise<ToolResult>;

// Tool registry
export const TOOLS: Record<string, ToolFunction> = {
  consultar_saldo: consultarSaldo,
  consultar_consumo: consultarConsumo,
  consultar_contrato: consultarContrato,
  consultar_tickets: consultarTickets,
  crear_reporte: crearReporte,
  transferir_humano: transferirHumano,
};

/**
 * Execute a tool by name
 */
export async function executeTool(toolName: string, input: Record<string, unknown>): Promise<ToolResult> {
  const tool = TOOLS[toolName];

  if (!tool) {
    console.warn(`[tools] Unknown tool: ${toolName}`);
    return {
      success: false,
      response: "No entendí qué quieres hacer. ¿Puedes explicarlo de otra manera?",
    };
  }

  try {
    console.log(`[tools] Executing tool: ${toolName} with input:`, JSON.stringify(input));
    const result = await tool(input);
    console.log(`[tools] Tool ${toolName} result:`, JSON.stringify(result));
    return result;
  } catch (error) {
    console.error(`[tools] Error executing ${toolName}:`, error);
    return {
      success: false,
      response: "Hubo un problema al procesar tu solicitud. Por favor intenta de nuevo.",
    };
  }
}

// Re-export individual tools
export { consultarSaldo } from "./consultar-saldo.js";
export { consultarConsumo } from "./consultar-consumo.js";
export { consultarContrato } from "./consultar-contrato.js";
export { consultarTickets } from "./consultar-tickets.js";
export { crearReporte } from "./crear-reporte.js";
export { transferirHumano } from "./transferir-humano.js";
