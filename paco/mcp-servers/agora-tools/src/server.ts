/**
 * AGORA Tools MCP Server
 *
 * Provides tools for interacting with the AGORA Ticket System:
 * - create_ticket: Create a new support ticket
 * - get_client_tickets: Get tickets for a contract
 * - update_ticket: Update ticket status
 * - search_customer: Search for customer by contract
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { SSEServerTransport } from "@modelcontextprotocol/sdk/server/sse.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import express from "express";
import pg from "pg";
import { ProxyConfigManager } from "../../shared/proxy-config.js";

// Configuration
const PG_CONFIG = {
  host: process.env.PGHOST || "localhost",
  port: parseInt(process.env.PGPORT || "5432"),
  user: process.env.PGUSER || "postgres",
  password: process.env.PGPASSWORD || "",
  database: process.env.PGDATABASE || "agora_production",
  max: parseInt(process.env.PGPOOL_MAX || "10"),
};

const pgPool = new pg.Pool(PG_CONFIG);

// Dynamic proxy config (for future external integrations)
const proxyManager = new ProxyConfigManager("agora-tools");

// Helper to get Mexico timezone date
function getMexicoDate(): Date {
  return new Date(
    new Date().toLocaleString("en-US", { timeZone: "America/Mexico_City" })
  );
}

// Database query helper
async function pgQuery<T = Record<string, unknown>>(
  query: string,
  params?: unknown[]
): Promise<T[]> {
  const client = await pgPool.connect();
  try {
    const result = await client.query(query, params);
    return result.rows as T[];
  } finally {
    client.release();
  }
}

// Category ID lookup
async function getCategoryId(code: string): Promise<number | null> {
  try {
    const result = await pgQuery<{ id: number }>(
      "SELECT id FROM ticket_categories WHERE code = $1 AND account_id = 2",
      [code]
    );
    return result?.[0]?.id || null;
  } catch {
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
  } catch {
    return null;
  }
}

// Types
type CategoryCode = "CON" | "FAC" | "CTR" | "CVN" | "REP" | "SRV";
type TicketPriority = "low" | "medium" | "high" | "urgent";
type TicketStatus =
  | "open"
  | "in_progress"
  | "waiting_client"
  | "waiting_internal"
  | "escalated"
  | "resolved"
  | "closed"
  | "cancelled";

interface CreateTicketInput {
  category_code: CategoryCode;
  subcategory_code?: string;
  titulo: string;
  descripcion: string;
  contract_number?: string;
  email?: string;
  ubicacion?: string;
  priority?: TicketPriority;
}

// Create MCP Server
const server = new Server(
  {
    name: "agora-tools",
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
        name: "create_ticket",
        description: `Crea un ticket en el sistema AGORA CEA y retorna el folio generado.

CATEGORIAS:
- CON: Consultas generales
- FAC: Facturación (recibos, aclaraciones)
- CTR: Contratos (altas, bajas, cambios)
- CVN: Convenios de pago
- REP: Reportes de servicio (fugas, drenaje)
- SRV: Servicios técnicos (medidores)`,
        inputSchema: {
          type: "object",
          properties: {
            category_code: {
              type: "string",
              enum: ["CON", "FAC", "CTR", "CVN", "REP", "SRV"],
              description: "Código de categoría AGORA",
            },
            subcategory_code: {
              type: "string",
              description: "Código de subcategoría (opcional)",
            },
            titulo: {
              type: "string",
              description: "Título breve del ticket",
            },
            descripcion: {
              type: "string",
              description: "Descripción detallada del problema",
            },
            contract_number: {
              type: "string",
              description:
                "Número de contrato (no requerido para fugas en vía pública)",
            },
            email: {
              type: "string",
              description: "Email del cliente (opcional)",
            },
            ubicacion: {
              type: "string",
              description: "Ubicación (requerido para reportes REP)",
            },
            priority: {
              type: "string",
              enum: ["low", "medium", "high", "urgent"],
              default: "medium",
              description: "Prioridad del ticket",
            },
          },
          required: ["category_code", "titulo", "descripcion"],
        },
      },
      {
        name: "get_client_tickets",
        description:
          "Obtiene los tickets de un cliente por número de contrato.",
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
      {
        name: "update_ticket",
        description: `Actualiza el estado de un ticket existente.

RESTRICCION: Los usuarios NO pueden cerrar tickets (resolved/closed).
Solo agentes humanos pueden cerrar tickets.`,
        inputSchema: {
          type: "object",
          properties: {
            folio: {
              type: "string",
              description: "Folio del ticket a actualizar",
            },
            status: {
              type: "string",
              enum: [
                "open",
                "in_progress",
                "waiting_client",
                "waiting_internal",
                "escalated",
              ],
              description: "Nuevo estado del ticket",
            },
            priority: {
              type: "string",
              enum: ["low", "medium", "high", "urgent"],
              description: "Nueva prioridad (opcional)",
            },
            notes: {
              type: "string",
              description: "Notas adicionales (opcional)",
            },
          },
          required: ["folio"],
        },
      },
      {
        name: "search_customer_by_contract",
        description:
          "Busca un cliente por su número de contrato en la base de datos.",
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
      case "create_ticket": {
        const input = args as unknown as CreateTicketInput;
        const priority = input.priority || "medium";
        const status = "open";

        const categoryId = await getCategoryId(input.category_code);
        const subcategoryId = input.subcategory_code
          ? await getSubcategoryId(input.subcategory_code)
          : null;

        const result = await pgQuery<{ id: number; folio: string }>(
          `
            INSERT INTO tickets (
                account_id, title, description, status, priority,
                ticket_type, service_type, channel, contract_number,
                client_name, metadata,
                ticket_category_id, ticket_subcategory_id,
                legacy_ticket_type, legacy_service_type,
                created_at, updated_at
            ) VALUES (
                2, $1, $2, $3, $4,
                'GEN', 'general', 'api', $5,
                $6, $7,
                $8, $9,
                $10, $11,
                NOW(), NOW()
            )
            RETURNING id, folio
          `,
          [
            input.titulo,
            input.descripcion,
            status,
            priority,
            input.contract_number || null,
            input.contract_number ? null : "Cliente API",
            JSON.stringify({
              email: input.email || null,
              ubicacion: input.ubicacion || null,
              category_code: input.category_code,
              subcategory_code: input.subcategory_code,
            }),
            categoryId,
            subcategoryId,
            input.category_code,
            input.subcategory_code || null,
          ]
        );

        const createdTicket = result[0];

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                folio: createdTicket.folio,
                ticketId: String(createdTicket.id),
                message: `Ticket creado con folio ${createdTicket.folio}`,
              }),
            },
          ],
        };
      }

      case "get_client_tickets": {
        const { contract_number } = args as { contract_number: string };

        const tickets = await pgQuery<{
          folio: string;
          status: string;
          title: string;
          service_type: string;
          created_at: Date;
          description: string;
        }>(
          `
            SELECT folio, status, title, service_type, created_at, description
            FROM tickets
            WHERE contract_number = $1
            ORDER BY created_at DESC
            LIMIT 10
          `,
          [contract_number]
        );

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                tickets: tickets.map((t) => ({
                  folio: t.folio,
                  status: t.status,
                  titulo: t.title,
                  service_type: t.service_type,
                  created_at: t.created_at,
                  descripcion: t.description?.substring(0, 100),
                })),
                count: tickets.length,
              }),
            },
          ],
        };
      }

      case "update_ticket": {
        const { folio, status, priority, notes } = args as {
          folio: string;
          status?: TicketStatus;
          priority?: TicketPriority;
          notes?: string;
        };

        // Block closing tickets through API
        if (
          status === "resolved" ||
          status === "closed" ||
          status === "cancelled"
        ) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: false,
                  blocked: true,
                  error:
                    "Tickets can only be closed by human agents",
                }),
              },
            ],
          };
        }

        const setClauses: string[] = ["updated_at = NOW()"];
        const params: unknown[] = [];
        let paramIndex = 1;

        if (status) {
          setClauses.push(`status = $${paramIndex++}`);
          params.push(status);
        }
        if (priority) {
          setClauses.push(`priority = $${paramIndex++}`);
          params.push(priority);
        }
        if (notes) {
          setClauses.push(`resolution_notes = $${paramIndex++}`);
          params.push(notes);
        }

        params.push(folio);

        await pgQuery(
          `
            UPDATE tickets
            SET ${setClauses.join(", ")}
            WHERE folio = $${paramIndex}
          `,
          params
        );

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                folio,
                message: `Ticket ${folio} actualizado`,
              }),
            },
          ],
        };
      }

      case "search_customer_by_contract": {
        const { contract_number } = args as { contract_number: string };

        const contacts = await pgQuery<{
          id: number;
          name: string;
          email: string | null;
          phone_number: string | null;
          identifier: string | null;
          custom_attributes: Record<string, unknown> | null;
        }>(
          `
            SELECT id, name, email, phone_number, identifier, custom_attributes
            FROM contacts
            WHERE identifier = $1
               OR custom_attributes->>'contract_number' = $1
            LIMIT 1
          `,
          [contract_number]
        );

        if (!contacts || contacts.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: true,
                  found: false,
                  message: "Cliente no encontrado",
                }),
              },
            ],
          };
        }

        const contact = contacts[0];
        const customAttrs = (contact.custom_attributes ||
          {}) as Record<string, unknown>;

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                found: true,
                customer: {
                  id: contact.id,
                  nombre: contact.name || "Sin nombre",
                  contrato:
                    contact.identifier ||
                    customAttrs.contract_number ||
                    contract_number,
                  email: contact.email || customAttrs.email || null,
                  whatsapp:
                    contact.phone_number || customAttrs.whatsapp || null,
                },
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
    console.error(`[${name}] Error:`, error);
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
  // Initialize proxy config from backend (with fallback to env var)
  await proxyManager.initialize();

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
    res.json({ status: "ok", name: "agora-tools", version: "1.0.0" });
  });

  // Proxy config reload endpoint
  app.post("/reload-config", async (_req, res) => {
    try {
      await proxyManager.reload();
      res.json({ status: "ok", message: "Config reloaded" });
    } catch (error) {
      res.status(500).json({
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      });
    }
  });

  // Proxy status endpoint (for debugging)
  app.get("/proxy-status", (_req, res) => {
    res.json(proxyManager.getStatus());
  });

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`AGORA Tools MCP Server running on http://0.0.0.0:${PORT}`);
  });
}

main().catch(console.error);
