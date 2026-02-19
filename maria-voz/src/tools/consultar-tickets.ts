/**
 * Consultar Tickets Tool - Voice formatted ticket query
 */

import { getTicketsByContract, type Ticket } from "../services/database.js";
import { formatFolioForVoice, formatDateForVoice } from "../utils/number-to-words.js";
import { STATUS_VOICE } from "../config/voice-agent.js";

interface ConsultarTicketsInput {
  contrato: string;
}

interface ConsultarTicketsResult {
  success: boolean;
  response: string;
  data?: {
    tickets: Array<{
      folio: string;
      titulo: string;
      estado: string;
      fecha: string;
    }>;
  };
  // Dynamic variables for ElevenLabs SIP transfer headers
  intent?: string;
  transfer_notes?: string;
  contrato?: string;
}

/**
 * Query tickets and return voice-formatted response
 */
export async function consultarTickets(input: ConsultarTicketsInput): Promise<ConsultarTicketsResult> {
  // Normalize contract number - remove spaces, hyphens, and non-digits
  const contrato = (input.contrato || "").replace(/[^0-9]/g, "");
  console.log(`[consultar_tickets] Querying tickets for contract: ${contrato} (original: ${input.contrato})`);

  try {
    const tickets = await getTicketsByContract(contrato);

    if (!tickets || tickets.length === 0) {
      return {
        success: true,
        response: "No tienes reportes activos en este momento.",
        data: { tickets: [] },
        // Dynamic variables for ElevenLabs SIP transfer
        intent: "consulta_tickets",
        transfer_notes: "Consultó tickets: sin reportes",
        contrato,
      };
    }

    // Filter to open/in-progress tickets only
    const activeTickets = tickets.filter(
      (t) => t.status === "open" || t.status === "in_progress" || t.status === "escalated" || t.status === "waiting_client"
    );

    if (activeTickets.length === 0) {
      return {
        success: true,
        response: "No tienes reportes activos. Tus reportes anteriores ya fueron resueltos.",
        data: { tickets: [] },
        // Dynamic variables for ElevenLabs SIP transfer
        intent: "consulta_tickets",
        transfer_notes: "Consultó tickets: sin reportes activos",
        contrato,
      };
    }

    // Build voice-friendly response
    let response = "";

    if (activeTickets.length === 1) {
      const ticket = activeTickets[0];
      const estadoVoz = STATUS_VOICE[ticket.status] || ticket.status;
      const folioVoz = formatFolioForVoice(ticket.folio);
      const fechaVoz = formatDateForVoice(new Date(ticket.created_at));

      response = `Tienes un reporte de ${ticket.title.toLowerCase()} con folio ${folioVoz}, en estado ${estadoVoz} desde el ${fechaVoz}.`;
    } else {
      response = `Tienes ${activeTickets.length} reportes activos. `;

      // Describe first 2 tickets
      const toDescribe = activeTickets.slice(0, 2);
      for (let i = 0; i < toDescribe.length; i++) {
        const ticket = toDescribe[i];
        const estadoVoz = STATUS_VOICE[ticket.status] || ticket.status;
        const folioVoz = formatFolioForVoice(ticket.folio);

        if (i === 0) {
          response += `El primero es de ${ticket.title.toLowerCase()}, folio ${folioVoz}, estado ${estadoVoz}.`;
        } else {
          response += ` El segundo es de ${ticket.title.toLowerCase()}, folio ${folioVoz}, estado ${estadoVoz}.`;
        }
      }

      if (activeTickets.length > 2) {
        response += ` Y ${activeTickets.length - 2} más.`;
      }
    }

    // Build transfer notes with ticket summary
    const ticketSummary = activeTickets
      .slice(0, 3)
      .map((t) => `${t.folio}: ${t.title} (${STATUS_VOICE[t.status] || t.status})`)
      .join("; ");

    return {
      success: true,
      response,
      data: {
        tickets: activeTickets.map((t) => ({
          folio: t.folio,
          titulo: t.title,
          estado: STATUS_VOICE[t.status] || t.status,
          fecha: new Date(t.created_at).toISOString().split("T")[0],
        })),
      },
      // Dynamic variables for ElevenLabs SIP transfer
      intent: "consulta_tickets",
      transfer_notes: `Consultó tickets: ${activeTickets.length} activos - ${ticketSummary}`,
      contrato,
    };
  } catch (error) {
    console.error(`[consultar_tickets] Error:`, error);
    return {
      success: false,
      response: "No pude consultar tus reportes en este momento. Por favor intenta de nuevo.",
    };
  }
}

export default consultarTickets;
