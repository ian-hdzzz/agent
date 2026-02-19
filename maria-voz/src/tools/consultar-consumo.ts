/**
 * Consultar Consumo Tool - Voice formatted consumption query
 */

import { getConsumo } from "../services/cea-api.js";
import { numberToSpanishWords, formatConsumptionForVoice } from "../utils/number-to-words.js";

interface ConsultarConsumoInput {
  contrato: string;
  year?: number;
}

interface ConsultarConsumoResult {
  success: boolean;
  response: string;
  data?: {
    consumos: Array<{ periodo: string; consumoM3: number }>;
    promedioMensual: number;
    tendencia: string;
  };
  // Dynamic variables for ElevenLabs SIP transfer headers
  intent?: string;
  transfer_notes?: string;
  contrato?: string;
}

/**
 * Query consumption history and return voice-formatted response
 */
export async function consultarConsumo(input: ConsultarConsumoInput): Promise<ConsultarConsumoResult> {
  // Normalize contract number - remove spaces, hyphens, and non-digits
  const contrato = (input.contrato || "").replace(/[^0-9]/g, "");
  const year = input.year;
  console.log(`[consultar_consumo] Querying consumption for contract: ${contrato} (original: ${input.contrato}), year: ${year || "recent"}`);

  const result = await getConsumo(contrato, year);

  if (!result.success || !result.data) {
    return {
      success: false,
      response: "No encontré historial de consumo para este contrato. ¿Puedes verificar el número?",
    };
  }

  const { consumos, promedioMensual, tendencia } = result.data;

  // Build voice-friendly response
  let response = "";

  if (consumos.length === 0) {
    response = "No hay registros de consumo disponibles para este período.";
  } else {
    // Get last 3 months for summary
    const recentConsumos = consumos.slice(0, 3);

    if (recentConsumos.length >= 3) {
      const consumoValues = recentConsumos.map((c) => numberToSpanishWords(Math.round(c.consumoM3)));
      response = `En los últimos tres meses consumiste ${consumoValues.join(", ")} metros cúbicos.`;
    } else if (recentConsumos.length > 0) {
      const lastConsumo = recentConsumos[0];
      response = `Tu último consumo registrado fue de ${formatConsumptionForVoice(lastConsumo.consumoM3)}.`;
    }

    // Add average
    response += ` Tu promedio es de ${numberToSpanishWords(promedioMensual)} metros cúbicos mensuales.`;

    // Add trend if notable
    if (tendencia === "aumentando") {
      response += " Noto que tu consumo ha aumentado últimamente.";
    } else if (tendencia === "disminuyendo") {
      response += " Tu consumo ha disminuido, muy bien.";
    }
  }

  // Build transfer notes with consumption summary
  const recentValues = consumos.slice(0, 3).map((c) => `${Math.round(c.consumoM3)}m³`).join(", ");
  const transferNotes = `Consultó consumo: últimos 3 meses: ${recentValues}, promedio: ${promedioMensual}m³/mes, tendencia: ${tendencia}`;

  return {
    success: true,
    response,
    data: {
      consumos: consumos.slice(0, 6).map((c) => ({
        periodo: c.periodo,
        consumoM3: c.consumoM3,
      })),
      promedioMensual,
      tendencia,
    },
    // Dynamic variables for ElevenLabs SIP transfer
    intent: "consulta_consumo",
    transfer_notes: transferNotes,
    contrato,
  };
}

export default consultarConsumo;
