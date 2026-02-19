/**
 * ElevenLabs Voice Agent Configuration
 */

export const VOICE_CONFIG = {
  // ElevenLabs agent created via MCP
  agentId: process.env.ELEVENLABS_AGENT_ID || "agent_1001kgg9vtwae00sftnnzw75swrf",

  // Cristina Campos - Mexican, conversational voice
  voiceId: "CaJslL1xziwefCeTNzHv",
  voiceName: "Cristina Campos",

  // Language
  language: "es",

  // WhatsApp redirect for photos and complex cases
  whatsappNumber: process.env.WHATSAPP_NUMBER || "442-238-8200",

  // Webhook server
  webhookPort: parseInt(process.env.PORT || "3001"),
  webhookSecret: process.env.ELEVENLABS_WEBHOOK_SECRET || "",

  // CEA office hours (for reference in prompts)
  officeHours: {
    weekdays: "8:00 AM - 3:00 PM",
    saturday: "9:00 AM - 1:00 PM",
    sunday: "Cerrado",
  },

  // Payment info (for voice responses)
  paymentOptions: [
    "En línea en la página ceaqro punto gob punto mx",
    "En cualquier tienda de conveniencia como Oxxo o Seven Eleven",
    "En las oficinas de CEA",
    "En bancos autorizados como Banorte, BBVA o Santander",
  ],

  // Tool definitions for ElevenLabs agent
  tools: [
    {
      name: "consultar_saldo",
      description: "Consulta el saldo y adeudo de un contrato de agua",
      parameters: {
        type: "object",
        properties: {
          contrato: {
            type: "string",
            description: "Número de contrato CEA (6 dígitos)",
          },
        },
        required: ["contrato"],
      },
    },
    {
      name: "consultar_consumo",
      description: "Consulta el historial de consumo de agua",
      parameters: {
        type: "object",
        properties: {
          contrato: {
            type: "string",
            description: "Número de contrato CEA",
          },
          year: {
            type: "number",
            description: "Año específico para consultar (opcional)",
          },
        },
        required: ["contrato"],
      },
    },
    {
      name: "consultar_contrato",
      description: "Consulta los detalles de un contrato",
      parameters: {
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
      name: "consultar_tickets",
      description: "Consulta los reportes activos de un contrato",
      parameters: {
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
      name: "crear_reporte",
      description: "Crea un reporte de fuga, drenaje u otro problema",
      parameters: {
        type: "object",
        properties: {
          tipo: {
            type: "string",
            enum: ["fuga_via_publica", "fuga_medidor", "drenaje", "sin_agua", "calidad_agua", "otro"],
            description: "Tipo de reporte",
          },
          ubicacion: {
            type: "string",
            description: "Ubicación del problema (calle, colonia)",
          },
          descripcion: {
            type: "string",
            description: "Descripción breve del problema",
          },
          contrato: {
            type: "string",
            description: "Número de contrato (opcional para fugas en vía pública)",
          },
        },
        required: ["tipo", "ubicacion", "descripcion"],
      },
    },
    {
      name: "transferir_humano",
      description: "Transfiere la llamada a un agente humano",
      parameters: {
        type: "object",
        properties: {
          motivo: {
            type: "string",
            description: "Motivo de la transferencia",
          },
        },
        required: ["motivo"],
      },
    },
  ],
};

// Report type mappings for voice
export const REPORT_TYPE_VOICE: Record<string, string> = {
  fuga_via_publica: "fuga de agua en vía pública",
  fuga_medidor: "fuga en medidor",
  drenaje: "problema de drenaje",
  sin_agua: "falta de agua",
  calidad_agua: "problema de calidad de agua",
  otro: "otro problema",
};

// Status mappings for voice
export const STATUS_VOICE: Record<string, string> = {
  open: "abierto",
  in_progress: "en proceso",
  waiting_client: "esperando información",
  escalated: "escalado a supervisor",
  resolved: "resuelto",
  closed: "cerrado",
  activo: "activo",
  suspendido: "suspendido",
  cortado: "cortado",
};
