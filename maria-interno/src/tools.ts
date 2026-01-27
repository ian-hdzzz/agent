// ============================================
// Maria Interno - Native Tools for Claude Agent SDK
// Herramientas para tickets internos de empleados
// ============================================

import { config } from "dotenv";
config();

import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import pg from "pg";
import type {
    CreateInternalTicketInput,
    CreateInternalTicketResult,
    CategoryCode,
    TicketPriority,
} from "./types.js";
import { getCategoryEmoji } from "./skills/base.js";

// ============================================
// Configuration
// ============================================

const PG_CONFIG = {
    host: process.env.PGHOST || 'localhost',
    port: parseInt(process.env.PGPORT || '5432'),
    user: process.env.PGUSER || 'postgres',
    password: process.env.PGPASSWORD || '',
    database: process.env.PGDATABASE || 'agora_production',
    max: parseInt(process.env.PGPOOL_MAX || '10'),
};

const pgPool = new pg.Pool(PG_CONFIG);

// ============================================
// Utility Functions
// ============================================

export function getMexicoDate(): Date {
    return new Date(new Date().toLocaleString("en-US", { timeZone: "America/Mexico_City" }));
}

// ============================================
// PostgreSQL Helpers
// ============================================

async function pgQuery<T = Record<string, unknown>>(query: string, params?: unknown[]): Promise<T[]> {
    const client = await pgPool.connect();
    try {
        const result = await client.query(query, params);
        return result.rows as T[];
    } finally {
        client.release();
    }
}

// ============================================
// Folio Generation for Internal Tickets
// ============================================

async function generateInternalTicketFolio(categoryCode: CategoryCode, subcategoryCode?: string): Promise<string> {
    const now = getMexicoDate();
    const year = now.getFullYear().toString();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const dateStr = `${year}${month}${day}`;

    const folioPrefix = subcategoryCode || categoryCode;
    const prefix = `${folioPrefix}-${dateStr}`;

    try {
        // Query tickets table (same as maria-claude) for folio sequence
        const result = await pgQuery<{ folio: string }>(`
            SELECT folio FROM tickets
            WHERE folio LIKE $1
            ORDER BY folio DESC
            LIMIT 1
        `, [`${prefix}-%`]);

        let nextNumber = 1;

        if (result && result.length > 0) {
            const lastFolio = result[0].folio;
            const match = lastFolio.match(/-(\d{4})$/);
            if (match) {
                nextNumber = parseInt(match[1]) + 1;
            }
        }

        return `${prefix}-${String(nextNumber).padStart(4, '0')}`;
    } catch (error) {
        console.warn(`[generateInternalTicketFolio] DB query failed, using timestamp fallback:`, error);
        const timestamp = now.getTime().toString().slice(-4);
        return `${prefix}-${timestamp}`;
    }
}

// ============================================
// Category/Subcategory ID Lookup Helpers
// Same as maria-claude - uses ticket_categories table
// ============================================

async function getCategoryId(code: string): Promise<number | null> {
    try {
        const result = await pgQuery<{ id: number }>(
            'SELECT id FROM ticket_categories WHERE code = $1 AND account_id = 4',
            [code]
        );
        return result?.[0]?.id || null;
    } catch (error) {
        console.warn(`[getCategoryId] Failed to lookup category ${code}:`, error);
        return null;
    }
}

async function getSubcategoryId(code: string): Promise<number | null> {
    try {
        const result = await pgQuery<{ id: number }>(
            'SELECT id FROM ticket_subcategories WHERE code = $1',
            [code]
        );
        return result?.[0]?.id || null;
    } catch (error) {
        console.warn(`[getSubcategoryId] Failed to lookup subcategory ${code}:`, error);
        return null;
    }
}

// ============================================
// Internal Ticket Creation Helper
// ============================================

export async function createInternalTicketDirect(input: CreateInternalTicketInput): Promise<CreateInternalTicketResult> {
    console.log(`[create_internal_ticket] Creating ticket:`, input);

    try {
        const priority = input.priority || "medium";
        const status = "open";

        // Look up category and subcategory IDs (same as maria-claude)
        const categoryId = await getCategoryId(input.category_code);
        const subcategoryId = input.subcategory_code ? await getSubcategoryId(input.subcategory_code) : null;

        console.log(`[create_internal_ticket] Category ID: ${categoryId}, Subcategory ID: ${subcategoryId}`);

        // Insert into tickets table with account_id 4 (maria-interno)
        // Folio is auto-generated by database trigger (INT-{display_id})
        const channel = input.channel || 'whatsapp';
        const result = await pgQuery<{ id: number; folio: string }>(`
            INSERT INTO tickets (
                account_id, title, description, status, priority,
                ticket_type, service_type, channel, contract_number,
                client_name, metadata,
                ticket_category_id, ticket_subcategory_id,
                legacy_ticket_type, legacy_service_type,
                created_at, updated_at
            ) VALUES (
                4, $1, $2, $3, $4,
                'GEN', 'general', $5, NULL,
                $6, $7,
                $8, $9,
                $10, $11,
                NOW(), NOW()
            )
            RETURNING id, folio
        `, [
            input.titulo,
            input.descripcion,
            status,
            priority,
            channel,
            input.employee_name || 'Empleado Interno',
            JSON.stringify({
                employee_id: input.employee_id,
                employee_email: input.employee_email,
                area_solicitante: input.area_solicitante,
                ubicacion: input.ubicacion,
                category_code: input.category_code,
                subcategory_code: input.subcategory_code
            }),
            categoryId,
            subcategoryId,
            input.category_code,
            input.subcategory_code || null
        ]);

        const createdTicket = result[0];
        console.log(`[create_internal_ticket] Created ticket with folio: ${createdTicket.folio}`);

        return {
            success: true,
            folio: createdTicket.folio,
            ticketId: String(createdTicket.id),
            message: `Ticket creado exitosamente con folio ${createdTicket.folio}`
        };
    } catch (error) {
        console.error(`[create_internal_ticket] Error:`, error);

        // Fallback folio generation
        const now = getMexicoDate();
        const timestamp = now.getTime().toString().slice(-6);
        const fallbackFolio = `INT-${input.category_code}-${timestamp}`;

        return {
            success: false,
            folio: fallbackFolio,
            error: `Error al crear ticket: ${error instanceof Error ? error.message : 'Error desconocido'}`,
            message: `No se pudo crear el ticket. Error: ${error instanceof Error ? error.message : 'Error desconocido'}`
        };
    }
}

// ============================================
// CLAUDE AGENT SDK TOOLS
// ============================================

/**
 * CREATE INTERNAL TICKET - Creates a new internal support ticket
 */
export const createInternalTicketTool = tool(
    "create_internal_ticket",
    `Crea un ticket interno para empleados de la CEA.

CATEGORÍAS DISPONIBLES:
- TI: Tecnologías de la Información (equipos, software, red, correo, accesos)
- RH: Recursos Humanos (vacaciones, permisos, nómina, constancias)
- MNT: Mantenimiento (electricidad, plomería, clima, cerrajería)
- VEH: Vehículos (solicitud, fallas, combustible, accidentes)
- ALM: Almacén (papelería, tóner, herramientas, EPP)
- ADM: Administrativo (oficios, viáticos, compras, contratos)
- COM: Comunicación Social (diseño, fotografía, redes, eventos)
- JUR: Jurídico (consultas legales, contratos, litigios)
- SEG: Seguridad (accesos, cámaras, incidentes, emergencias)

IMPORTANTE: Siempre incluye el folio en tu respuesta al empleado.`,
    {
        category_code: z.enum(["TI", "RH", "MNT", "VEH", "ALM", "ADM", "COM", "JUR", "SEG"])
            .describe("Código de categoría del ticket"),
        subcategory_code: z.string().optional()
            .describe("Código de subcategoría (ej: TI-EQC, RH-VAC, MNT-ELE)"),
        titulo: z.string().describe("Título breve del ticket"),
        descripcion: z.string().describe("Descripción detallada de la solicitud o problema"),
        employee_name: z.string().optional().describe("Nombre del empleado solicitante"),
        employee_email: z.string().optional().describe("Email del empleado"),
        employee_id: z.string().optional().describe("Número de empleado"),
        area_solicitante: z.string().optional().describe("Área o departamento del solicitante"),
        ubicacion: z.string().optional().describe("Ubicación física (edificio, piso, oficina)"),
        priority: z.enum(["low", "medium", "high", "urgent"]).default("medium")
            .describe("Prioridad del ticket"),
        channel: z.string().optional().describe("Canal de origen (whatsapp, web, api, etc.)")
    },
    async (input) => {
        const ticketInput: CreateInternalTicketInput = {
            category_code: input.category_code,
            subcategory_code: input.subcategory_code as any,
            titulo: input.titulo,
            descripcion: input.descripcion,
            employee_id: input.employee_id,
            employee_name: input.employee_name,
            employee_email: input.employee_email,
            area_solicitante: input.area_solicitante,
            ubicacion: input.ubicacion,
            priority: input.priority as TicketPriority,
            channel: input.channel
        };

        const result = await createInternalTicketDirect(ticketInput);

        const emoji = getCategoryEmoji(input.category_code);
        const formattedResponse = result.success
            ? `${emoji} ¡Ticket creado!\n\nFolio: ${result.folio}\nTipo: ${input.titulo}\n${input.ubicacion ? `Ubicación: ${input.ubicacion}\n` : ''}Estado: Abierto\n\nEl área responsable dará seguimiento a tu solicitud.`
            : `No se pudo crear el ticket. ${result.error}`;

        return { content: [{ type: "text" as const, text: JSON.stringify({
            ...result,
            formatted_response: formattedResponse
        }) }] };
    }
);

/**
 * GET EMPLOYEE TICKETS - Retrieves tickets for an employee
 */
export const getEmployeeTicketsTool = tool(
    "get_employee_tickets",
    `Obtiene los tickets de un empleado por su email o número de empleado.

RETORNA lista de tickets con:
- folio: Número de ticket
- status: Estado (open, in_progress, resolved, etc.)
- titulo: Título del ticket
- category_code: Categoría
- created_at: Fecha de creación`,
    {
        employee_email: z.string().optional().describe("Email del empleado"),
        employee_id: z.string().optional().describe("Número de empleado")
    },
    async ({ employee_email, employee_id }) => {
        console.log(`[get_employee_tickets] Fetching tickets for employee: ${employee_email || employee_id}`);

        if (!employee_email && !employee_id) {
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: "Se requiere email o número de empleado"
                    })
                }]
            };
        }

        try {
            let query = `
                SELECT folio, status, title, category_code, subcategory_code,
                       priority, created_at, description, ubicacion
                FROM internal_tickets
                WHERE `;

            const params: string[] = [];

            if (employee_email) {
                query += `employee_email = $1`;
                params.push(employee_email);
            } else {
                query += `employee_id = $1`;
                params.push(employee_id!);
            }

            query += ` ORDER BY created_at DESC LIMIT 10`;

            const tickets = await pgQuery<{
                folio: string;
                status: string;
                title: string;
                category_code: string;
                subcategory_code: string;
                priority: string;
                created_at: Date;
                description: string;
                ubicacion: string;
            }>(query, params);

            if (!tickets || tickets.length === 0) {
                return {
                    content: [{
                        type: "text" as const,
                        text: JSON.stringify({
                            success: true,
                            tickets: [],
                            formatted_response: "No se encontraron tickets registrados."
                        })
                    }]
                };
            }

            const statusLabels: Record<string, string> = {
                open: "Abierto",
                in_progress: "En proceso",
                resolved: "Resuelto",
                closed: "Cerrado",
                waiting_employee: "Esperando información",
                waiting_internal: "En espera interna",
                escalated: "Escalado"
            };

            const ticketList = tickets.map((t) => {
                const emoji = getCategoryEmoji(t.category_code as CategoryCode);
                return `${emoji} ${t.folio}\n   ${t.title}\n   Estado: ${statusLabels[t.status] || t.status}\n   Prioridad: ${t.priority}`;
            }).join('\n\n');

            const formattedResponse = `📋 Tus tickets recientes:\n\n${ticketList}`;

            const result = {
                success: true,
                tickets: tickets.map((t) => ({
                    folio: t.folio,
                    status: t.status,
                    titulo: t.title,
                    category_code: t.category_code,
                    subcategory_code: t.subcategory_code,
                    priority: t.priority,
                    created_at: t.created_at,
                    ubicacion: t.ubicacion
                })),
                count: tickets.length,
                formatted_response: formattedResponse
            };

            return { content: [{ type: "text" as const, text: JSON.stringify(result) }] };
        } catch (error) {
            console.error(`[get_employee_tickets] Error:`, error);
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: `No se pudieron consultar los tickets: ${error instanceof Error ? error.message : 'Error desconocido'}`
                    })
                }]
            };
        }
    }
);

/**
 * GET TICKET STATUS - Get status of a specific ticket
 */
export const getTicketStatusTool = tool(
    "get_ticket_status",
    "Obtiene el estado detallado de un ticket por su folio.",
    {
        folio: z.string().describe("Folio del ticket (ej: INT-TI-EQC-20240115-0001)")
    },
    async ({ folio }) => {
        console.log(`[get_ticket_status] Fetching status for: ${folio}`);

        try {
            const tickets = await pgQuery<{
                folio: string;
                status: string;
                title: string;
                description: string;
                category_code: string;
                subcategory_code: string;
                priority: string;
                created_at: Date;
                updated_at: Date;
                resolved_at: Date | null;
                resolution_notes: string | null;
                assigned_to: string | null;
                ubicacion: string;
            }>(`
                SELECT folio, status, title, description, category_code, subcategory_code,
                       priority, created_at, updated_at, resolved_at, resolution_notes,
                       assigned_to, ubicacion
                FROM internal_tickets
                WHERE folio = $1
            `, [folio]);

            if (!tickets || tickets.length === 0) {
                return {
                    content: [{
                        type: "text" as const,
                        text: JSON.stringify({
                            success: false,
                            error: "Ticket no encontrado",
                            formatted_response: `No encontré un ticket con folio ${folio}. ¿Puedes verificar el número?`
                        })
                    }]
                };
            }

            const ticket = tickets[0];
            const emoji = getCategoryEmoji(ticket.category_code as CategoryCode);

            const statusLabels: Record<string, string> = {
                open: "Abierto",
                in_progress: "En proceso",
                resolved: "Resuelto",
                closed: "Cerrado",
                waiting_employee: "Esperando tu información",
                waiting_internal: "En espera interna",
                escalated: "Escalado a supervisor"
            };

            let formattedResponse = `${emoji} Ticket: ${ticket.folio}\n\n`;
            formattedResponse += `📝 ${ticket.title}\n`;
            formattedResponse += `📊 Estado: ${statusLabels[ticket.status] || ticket.status}\n`;
            formattedResponse += `⚡ Prioridad: ${ticket.priority}\n`;

            if (ticket.assigned_to) {
                formattedResponse += `👤 Asignado a: ${ticket.assigned_to}\n`;
            }

            if (ticket.ubicacion) {
                formattedResponse += `📍 Ubicación: ${ticket.ubicacion}\n`;
            }

            if (ticket.resolution_notes) {
                formattedResponse += `\n💬 Notas: ${ticket.resolution_notes}`;
            }

            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: true,
                        ticket: {
                            folio: ticket.folio,
                            status: ticket.status,
                            title: ticket.title,
                            description: ticket.description,
                            category_code: ticket.category_code,
                            subcategory_code: ticket.subcategory_code,
                            priority: ticket.priority,
                            created_at: ticket.created_at,
                            updated_at: ticket.updated_at,
                            resolved_at: ticket.resolved_at,
                            resolution_notes: ticket.resolution_notes,
                            assigned_to: ticket.assigned_to
                        },
                        formatted_response: formattedResponse
                    })
                }]
            };
        } catch (error) {
            console.error(`[get_ticket_status] Error:`, error);
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: error instanceof Error ? error.message : 'Error desconocido'
                    })
                }]
            };
        }
    }
);

/**
 * UPDATE TICKET - Updates an internal ticket
 */
export const updateTicketTool = tool(
    "update_ticket",
    `Actualiza el estado o agrega notas a un ticket interno existente.

ESTADOS PERMITIDOS:
- in_progress: En proceso
- waiting_employee: Esperando información del empleado
- waiting_internal: En espera interna
- escalated: Escalado

⚠️ Los empleados NO pueden cerrar/resolver tickets directamente.`,
    {
        folio: z.string().describe("Folio del ticket a actualizar"),
        status: z.enum(["open", "in_progress", "waiting_employee", "waiting_internal", "escalated"]).optional()
            .describe("Nuevo estado del ticket"),
        notes: z.string().optional().describe("Notas adicionales o información del empleado")
    },
    async ({ folio, status, notes }) => {
        console.log(`[update_ticket] Updating ticket: ${folio}`);

        try {
            const setClauses: string[] = ['updated_at = NOW()'];
            const params: unknown[] = [];
            let paramIndex = 1;

            if (status) {
                setClauses.push(`status = $${paramIndex++}`);
                params.push(status);
            }
            if (notes) {
                // Append to existing notes
                setClauses.push(`resolution_notes = COALESCE(resolution_notes, '') || E'\\n' || $${paramIndex++}`);
                params.push(`[${getMexicoDate().toISOString()}] ${notes}`);
            }

            params.push(folio);

            await pgQuery(`
                UPDATE internal_tickets
                SET ${setClauses.join(', ')}
                WHERE folio = $${paramIndex}
            `, params);

            const statusLabels: Record<string, string> = {
                in_progress: "en proceso",
                waiting_employee: "esperando tu información",
                waiting_internal: "en espera interna",
                escalated: "escalado"
            };

            let message = `Ticket ${folio} actualizado.`;
            if (status) {
                message = `Ticket ${folio} ahora está ${statusLabels[status] || status}.`;
            }
            if (notes) {
                message += ` Se agregó tu información.`;
            }

            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: true,
                        folio,
                        formatted_response: message
                    })
                }]
            };
        } catch (error) {
            console.error(`[update_ticket] Error:`, error);
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: error instanceof Error ? error.message : 'Error desconocido'
                    })
                }]
            };
        }
    }
);

/**
 * SEARCH EMPLOYEE - Search for an employee in the system
 */
export const searchEmployeeTool = tool(
    "search_employee",
    "Busca información de un empleado por nombre, email o número de empleado.",
    {
        query: z.string().describe("Nombre, email o número de empleado a buscar")
    },
    async ({ query }) => {
        console.log(`[search_employee] Searching for: ${query}`);

        try {
            const employees = await pgQuery<{
                id: string;
                numero_empleado: string;
                nombre: string;
                email: string;
                area: string;
                puesto: string;
                extension: string | null;
                ubicacion: string | null;
            }>(`
                SELECT id, numero_empleado, nombre, email, area, puesto, extension, ubicacion
                FROM employees
                WHERE numero_empleado = $1
                   OR email ILIKE $1
                   OR nombre ILIKE '%' || $1 || '%'
                LIMIT 5
            `, [query]);

            if (!employees || employees.length === 0) {
                return {
                    content: [{
                        type: "text" as const,
                        text: JSON.stringify({
                            success: true,
                            found: false,
                            message: "No se encontró ningún empleado con esa información."
                        })
                    }]
                };
            }

            const result = {
                success: true,
                found: true,
                employees: employees.map(e => ({
                    numero_empleado: e.numero_empleado,
                    nombre: e.nombre,
                    email: e.email,
                    area: e.area,
                    puesto: e.puesto,
                    extension: e.extension,
                    ubicacion: e.ubicacion
                })),
                count: employees.length
            };

            return { content: [{ type: "text" as const, text: JSON.stringify(result) }] };
        } catch (error) {
            console.error(`[search_employee] Error:`, error);
            return {
                content: [{
                    type: "text" as const,
                    text: JSON.stringify({
                        success: false,
                        error: error instanceof Error ? error.message : 'Error desconocido'
                    })
                }]
            };
        }
    }
);

/**
 * HANDOFF TO HUMAN - Transfer conversation to human agent
 */
export const handoffToHumanTool = tool(
    "handoff_to_human",
    `Transfiere la conversación a un agente humano del área correspondiente.

USA ESTA HERRAMIENTA CUANDO:
- El empleado solicite hablar con una persona
- No puedas resolver la solicitud
- El empleado esté frustrado
- Sea un caso especial que requiera atención personal`,
    {
        reason: z.string().describe("Motivo de la transferencia"),
        area: z.enum(["TI", "RH", "MNT", "VEH", "ALM", "ADM", "COM", "JUR", "SEG"]).optional()
            .describe("Área a la que se transfiere")
    },
    async ({ reason, area }) => {
        console.log(`[handoff_to_human] Transfer requested. Reason: ${reason}, Area: ${area || 'general'}`);

        const areaContacts: Record<string, string> = {
            TI: "Soporte TI - Ext. 1234",
            RH: "Recursos Humanos - Ext. 1111",
            MNT: "Servicios Generales - Ext. 2345",
            VEH: "Transporte - Ext. 3456",
            ALM: "Almacén - Ext. 4567",
            ADM: "Administración - Ext. 5678",
            COM: "Comunicación - Ext. 6789",
            JUR: "Jurídico - Ext. 7890",
            SEG: "Seguridad - Ext. 8901"
        };

        const contact = area ? areaContacts[area] : "Mesa de ayuda - Ext. 1000";

        return {
            content: [{
                type: "text" as const,
                text: JSON.stringify({
                    success: true,
                    formatted_response: `Te comunico con un agente del área correspondiente.\n\n📞 ${contact}\n\nTambién puedes contactarlos directamente si lo prefieres.`
                })
            }]
        };
    }
);

// ============================================
// Export all tools
// ============================================

export const allTools = [
    createInternalTicketTool,
    getEmployeeTicketsTool,
    getTicketStatusTool,
    updateTicketTool,
    searchEmployeeTool,
    handoffToHumanTool
];
