/**
 * Consultar Contrato Tool - Voice formatted contract details
 */

import { getContractDetails } from "../services/cea-api.js";
import { spellDigits } from "../utils/number-to-words.js";
import { STATUS_VOICE } from "../config/voice-agent.js";

interface ConsultarContratoInput {
  contrato: string;
}

interface ConsultarContratoResult {
  success: boolean;
  response: string;
  data?: {
    titular: string;
    direccion: string;
    estado: string;
  };
  // Dynamic variables for ElevenLabs SIP transfer headers
  intent?: string;
  transfer_notes?: string;
  contrato?: string;
  customer_name?: string;
}

/**
 * Query contract details and return voice-formatted response
 */
export async function consultarContrato(input: ConsultarContratoInput): Promise<ConsultarContratoResult> {
  // Normalize contract number - remove spaces, hyphens, and non-digits
  const contrato = (input.contrato || "").replace(/[^0-9]/g, "");
  console.log(`[consultar_contrato] Querying contract: ${contrato} (original: ${input.contrato})`);

  const result = await getContractDetails(contrato);

  if (!result.success || !result.data) {
    return {
      success: false,
      response: `No encontré información para el contrato ${spellDigits(contrato)}. ¿Puedes verificar el número?`,
    };
  }

  const { titular, direccion, colonia, estado } = result.data;
  const estadoVoz = STATUS_VOICE[estado] || estado;

  // Build voice-friendly response
  let response = `Tu contrato está ${estadoVoz} a nombre de ${titular}.`;

  if (direccion) {
    response += ` La dirección registrada es ${direccion}`;
    if (colonia) {
      response += `, en ${colonia}`;
    }
    response += ".";
  }

  const fullDireccion = direccion + (colonia ? `, ${colonia}` : "");

  return {
    success: true,
    response,
    data: {
      titular,
      direccion: fullDireccion,
      estado: estadoVoz,
    },
    // Dynamic variables for ElevenLabs SIP transfer
    intent: "consulta_contrato",
    transfer_notes: `Consultó contrato: ${titular}, ${fullDireccion}, estado: ${estadoVoz}`,
    contrato,
    customer_name: titular,
  };
}

export default consultarContrato;
