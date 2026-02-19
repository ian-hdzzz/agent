/**
 * Consultar Saldo Tool - Voice formatted balance query
 */

import { getDeuda } from "../services/cea-api.js";
import { formatCurrencyForVoice, spellDigits } from "../utils/number-to-words.js";

interface ConsultarSaldoInput {
  contrato: string;
}

interface ConsultarSaldoResult {
  success: boolean;
  response: string;
  data?: {
    totalDeuda: number;
    vencido: number;
    porVencer: number;
  };
  // Dynamic variables for ElevenLabs SIP transfer headers
  intent?: string;
  transfer_notes?: string;
  contrato?: string;
}

/**
 * Query balance and return voice-formatted response
 */
export async function consultarSaldo(input: ConsultarSaldoInput): Promise<ConsultarSaldoResult> {
  // Normalize contract number - remove spaces, hyphens, and non-digits
  const contrato = (input.contrato || "").replace(/[^0-9]/g, "");
  console.log(`[consultar_saldo] Querying balance for contract: ${contrato} (original: ${input.contrato})`);

  const result = await getDeuda(contrato);

  if (!result.success || !result.data) {
    return {
      success: false,
      response: `No encontré información para el contrato ${spellDigits(contrato)}. ¿Puedes verificar el número?`,
    };
  }

  const { totalDeuda, vencido, porVencer } = result.data;

  // Build voice-friendly response
  let response = "";

  if (totalDeuda === 0) {
    response = "Tu cuenta está al corriente. No tienes ningún saldo pendiente.";
  } else {
    response = `Tu saldo total es de ${formatCurrencyForVoice(totalDeuda)}.`;

    if (vencido > 0) {
      response += ` Tienes ${formatCurrencyForVoice(vencido)} vencidos.`;
    }

    if (porVencer > 0 && vencido > 0) {
      response += ` Y ${formatCurrencyForVoice(porVencer)} por vencer.`;
    }

    response += " ¿Te gustaría conocer las opciones de pago?";
  }

  return {
    success: true,
    response,
    data: { totalDeuda, vencido, porVencer },
    // Dynamic variables for ElevenLabs SIP transfer
    intent: "consulta_saldo",
    transfer_notes: `Consultó saldo: $${totalDeuda} (vencido: $${vencido}, por vencer: $${porVencer})`,
    contrato,
  };
}

export default consultarSaldo;
