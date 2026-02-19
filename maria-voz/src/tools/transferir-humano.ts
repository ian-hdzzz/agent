/**
 * Transferir a Humano Tool - Handoff to human agent
 */

import { VOICE_CONFIG } from "../config/voice-agent.js";

interface TransferirHumanoInput {
  motivo: string;
}

interface TransferirHumanoResult {
  success: boolean;
  response: string;
  action: "handoff";
  metadata: {
    reason: string;
    fallback_number: string;
  };
  // Dynamic variables for ElevenLabs SIP transfer headers
  intent?: string;
  transfer_notes?: string;
}

/**
 * Prepare handoff to human agent
 * Note: The actual handoff is triggered by ElevenLabs based on the action type
 */
export async function transferirHumano(input: TransferirHumanoInput): Promise<TransferirHumanoResult> {
  const { motivo } = input;
  console.log(`[transferir_humano] Initiating handoff. Reason: ${motivo}`);

  // Return response that triggers ElevenLabs handoff
  return {
    success: true,
    response: "Entendido, te comunico con un asesor. Un momento por favor.",
    action: "handoff",
    metadata: {
      reason: motivo,
      fallback_number: VOICE_CONFIG.whatsappNumber,
    },
    // Dynamic variables for ElevenLabs SIP transfer
    intent: "transferencia_humano",
    transfer_notes: `Transferido a humano: ${motivo}`,
  };
}

export default transferirHumano;
