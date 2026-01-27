// ============================================
// Maria Interno - Main Agent with Skill Routing
// Sistema de Tickets Internos para Empleados
// ============================================

import { query, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
import {
    SKILL_REGISTRY,
    getSkill,
    getSkillDescriptions,
    buildSystemContext
} from "./skills/index.js";
import { allTools } from "./tools.js";
import type { CategoryCode, InternalWorkflowInput, InternalWorkflowOutput } from "./types.js";

// ============================================
// Conversation Store
// ============================================

interface ConversationEntry {
    history: Array<{ role: "user" | "assistant"; content: string }>;
    lastAccess: Date;
    employeeId?: string;
    employeeName?: string;
    employeeEmail?: string;
    employeePhone?: string;
    area?: string;
    category?: CategoryCode;
}

const conversationStore = new Map<string, ConversationEntry>();

// Cleanup old conversations (1 hour expiry)
setInterval(() => {
    const now = Date.now();
    for (const [id, entry] of conversationStore.entries()) {
        if (now - entry.lastAccess.getTime() > 3600000) {
            conversationStore.delete(id);
        }
    }
}, 300000);

function getConversation(id: string): ConversationEntry {
    const existing = conversationStore.get(id);
    if (existing) {
        existing.lastAccess = new Date();
        return existing;
    }

    const newEntry: ConversationEntry = {
        history: [],
        lastAccess: new Date()
    };
    conversationStore.set(id, newEntry);
    return newEntry;
}

// ============================================
// Classification Keywords
// ============================================

const CATEGORY_KEYWORDS: Record<CategoryCode, string[]> = {
    TI: [
        "computadora", "laptop", "pc", "monitor", "teclado", "mouse", "impresora",
        "software", "programa", "instalar", "internet", "red", "wifi", "conexión",
        "correo", "email", "outlook", "contraseña", "password", "acceso", "usuario",
        "sistema", "aplicación", "error", "falla", "lento", "no funciona", "no enciende",
        "teléfono ip", "extensión", "vpn", "remoto", "virus", "hackeo", "seguridad informática"
    ],
    RH: [
        "vacaciones", "permiso", "incapacidad", "nómina", "pago", "sueldo", "salario",
        "constancia", "carta laboral", "credencial", "gafete", "capacitación", "curso",
        "evaluación", "desempeño", "alta", "baja", "renuncia", "contratación",
        "cambio de área", "ascenso", "promoción", "checada", "asistencia", "retardo",
        "préstamo", "adelanto", "imss", "seguro", "uniforme", "ropa de trabajo"
    ],
    MNT: [
        "luz", "electricidad", "apagón", "contacto", "lámpara", "foco",
        "fuga", "agua", "baño", "lavabo", "wc", "drenaje", "tubería",
        "clima", "aire acondicionado", "calefacción", "ventilador",
        "puerta", "chapa", "llave", "cerradura", "candado",
        "pintura", "pared", "limpieza", "fumigación", "plaga",
        "silla", "escritorio", "mueble", "gotera", "techo", "filtración",
        "jardín", "pasto", "árbol", "estacionamiento", "bache"
    ],
    VEH: [
        "vehículo", "camioneta", "carro", "auto", "coche", "unidad",
        "gasolina", "combustible", "vale", "diesel",
        "llanta", "ponchadura", "falla mecánica", "motor", "frenos",
        "accidente", "choque", "siniestro", "golpe",
        "gps", "rastreo", "ubicación",
        "verificación", "tarjeta de circulación", "placas",
        "multa", "infracción"
    ],
    ALM: [
        "papelería", "hojas", "papel", "folder", "carpeta", "pluma", "lápiz",
        "tóner", "cartucho", "tinta",
        "limpieza", "jabón", "papel higiénico", "químico",
        "herramienta", "desarmador", "pinza", "martillo",
        "casco", "chaleco", "guantes", "epp", "equipo de seguridad",
        "mueble", "mobiliario", "archivero",
        "material", "cemento", "tubería", "conexión",
        "devolución", "regreso de material"
    ],
    ADM: [
        "oficio", "memorándum", "memo", "documento",
        "firma", "autorización", "visto bueno",
        "archivo", "expediente", "copias certificadas",
        "viáticos", "comisión", "viaje",
        "caja chica", "reembolso", "gasto",
        "factura", "facturación",
        "compra", "requisición", "cotización",
        "contrato", "convenio", "acuerdo",
        "seguro", "póliza"
    ],
    COM: [
        "diseño", "cartel", "poster", "lona", "banner", "infografía",
        "fotografía", "foto", "video", "grabación", "cobertura",
        "redes sociales", "facebook", "twitter", "instagram", "publicación",
        "boletín", "prensa", "comunicado",
        "evento", "conferencia", "inauguración",
        "página web", "portal", "sitio web",
        "circular", "aviso", "comunicación interna"
    ],
    JUR: [
        "legal", "abogado", "jurídico", "ley",
        "contrato", "convenio", "cláusula", "revisión legal",
        "demanda", "litigio", "juicio", "tribunal",
        "notificación", "requerimiento", "citatorio",
        "poder", "notarial", "poder notarial",
        "queja", "denuncia"
    ],
    SEG: [
        "seguridad", "vigilancia", "guardia",
        "gafete", "acceso", "visitante", "registro",
        "cámara", "cctv", "grabación", "monitoreo",
        "robo", "hurto", "vandalismo", "amenaza", "extorsión",
        "rondín", "custodia", "resguardo",
        "emergencia", "incendio", "sismo", "evacuación",
        "investigación", "incidente"
    ]
};

// ============================================
// Classification Logic
// ============================================

function classifyMessage(message: string): CategoryCode {
    const messageLower = message.toLowerCase();

    // Count keyword matches for each category
    const scores: Record<CategoryCode, number> = {
        TI: 0, RH: 0, MNT: 0, VEH: 0, ALM: 0, ADM: 0, COM: 0, JUR: 0, SEG: 0
    };

    for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
        for (const keyword of keywords) {
            if (messageLower.includes(keyword)) {
                scores[category as CategoryCode] += 1;
            }
        }
    }

    // Find category with highest score
    let maxScore = 0;
    let bestCategory: CategoryCode = "TI"; // Default to TI

    for (const [category, score] of Object.entries(scores)) {
        if (score > maxScore) {
            maxScore = score;
            bestCategory = category as CategoryCode;
        }
    }

    return bestCategory;
}

// ============================================
// Global Conversation Rules
// ============================================

const GLOBAL_CONVERSATION_RULES = `
⚠️ REGLAS DE CONVERSACIÓN:

1. CREA EL TICKET INMEDIATAMENTE:
   - Cuando el empleado describe un problema, CREA EL TICKET DE INMEDIATO
   - NO hagas preguntas innecesarias
   - Usa la información que ya tienes (nombre del sender, descripción del problema)

2. RESPUESTAS COMO HUMANO:
   - UNA sola oración corta y natural
   - NO uses frases como "Dame un momento", "Voy a levantar", "Claro!"
   - Después de crear ticket, responde SOLO: "Ya levanté tu ticket {FOLIO}, alguien de {EQUIPO} te contactará para resolverlo"
   - Ejemplo bueno: "Ya levanté tu ticket INT-TI-399000, alguien de TI te contactará para resolverlo"
   - Ejemplo malo: "¡Claro! Voy a levantar tu ticket. Dame un momento 💻 Listo! Tu ticket..."

3. NO PREGUNTES:
   - NO preguntes área/departamento
   - NO preguntes ubicación
   - NO preguntes email
   - NO preguntes detalles adicionales

4. SALUDO:
   - Si tienes el nombre del empleado, saluda personalizado: "¡Hola {NOMBRE}! Soy María 👋 ¿En qué te puedo ayudar hoy?"
   - Si NO tienes el nombre: "¡Hola! Soy María 👋 ¿En qué te puedo ayudar hoy?"
   - NUNCA te presentes como "asistente de TI" o cualquier otro departamento
   - Siempre eres "María"

5. EMERGENCIAS:
   - Para emergencias (incendio, accidente) → 911 primero, luego ticket

FLUJO:
1. Empleado describe problema → CREA TICKET INMEDIATAMENTE (sin decir nada antes)
2. Responde UNA oración: "Ya levanté tu ticket {FOLIO}, alguien de {EQUIPO} te contactará para resolverlo"
`;

// ============================================
// Main Workflow
// ============================================

export async function runInternalWorkflow(input: InternalWorkflowInput): Promise<InternalWorkflowOutput> {
    const startTime = Date.now();
    const conversationId = input.conversationId || crypto.randomUUID();

    console.log(`\n========== INTERNAL WORKFLOW START ==========`);
    console.log(`ConversationId: ${conversationId}`);
    console.log(`Input: "${input.input_as_text}"`);

    const conversation = getConversation(conversationId);

    // Store employee info if provided
    if (input.metadata?.employee_id) conversation.employeeId = input.metadata.employee_id;
    if (input.metadata?.employee_name) conversation.employeeName = input.metadata.employee_name;
    if (input.metadata?.employee_email) conversation.employeeEmail = input.metadata.employee_email;
    if (input.metadata?.employee_phone) conversation.employeePhone = input.metadata.employee_phone;
    if (input.metadata?.area) conversation.area = input.metadata.area;

    try {
        // Step 1: Classification
        console.log(`[Workflow] Running classification...`);
        const category = classifyMessage(input.input_as_text);
        console.log(`[Workflow] Classification: ${category}`);

        // Step 2: Get the appropriate skill
        const skill = getSkill(category);
        console.log(`[Workflow] Using skill: ${skill.name} (enabled: ${skill.enabled})`);

        // Step 3: Build conversation history
        const historyText = conversation.history
            .slice(-10) // Last 10 messages
            .map(msg => `${msg.role === 'user' ? 'Empleado' : 'Asistente'}: ${msg.content}`)
            .join('\n');

        // Step 4: Build employee context
        let employeeContext = '';
        if (conversation.employeeName) employeeContext += `Nombre: ${conversation.employeeName}\n`;
        if (conversation.employeeId) employeeContext += `Número de empleado: ${conversation.employeeId}\n`;
        if (conversation.employeeEmail) employeeContext += `Email: ${conversation.employeeEmail}\n`;
        if (conversation.employeePhone) employeeContext += `Teléfono: ${conversation.employeePhone}\n`;
        if (conversation.area) employeeContext += `Área: ${conversation.area}\n`;

        // Get channel from metadata
        const channel = input.metadata?.channel || 'whatsapp';
        employeeContext += `Canal: ${channel}\n`;

        // Step 5: Run the agent with the skill
        const fullPrompt = `${GLOBAL_CONVERSATION_RULES}

${skill.systemPrompt}

CONTEXTO ACTUAL:
${buildSystemContext()}
${employeeContext ? `\nINFORMACIÓN DEL EMPLEADO:\n${employeeContext}` : ''}

${historyText ? `HISTORIAL DE CONVERSACIÓN:\n${historyText}\n` : ''}

MENSAJE DEL EMPLEADO:
${input.input_as_text}`;

        let output = "";
        const toolsUsed: string[] = [];

        // Create MCP server with our tools
        const mcpServerConfig = createSdkMcpServer({
            name: "maria-interno-tools",
            version: "1.0.0",
            tools: allTools
        });

        // Run query with Claude Agent SDK
        console.log(`[Workflow] Starting Claude query...`);
        const result = query({
            prompt: fullPrompt,
            options: {
                model: "claude-sonnet-4-5-20250929",
                maxBudgetUsd: 0.50,
                permissionMode: "bypassPermissions",
                allowDangerouslySkipPermissions: true,
                mcpServers: {
                    "maria-interno-tools": mcpServerConfig
                },
                persistSession: false,
                tools: [],
                cwd: process.cwd(),
                stderr: (data: string) => {
                    console.error(`[Claude STDERR]: ${data}`);
                },
                env: process.env
            }
        });

        // Collect the response
        for await (const message of result) {
            if (message.type === "assistant") {
                const content = message.message.content;
                if (Array.isArray(content)) {
                    for (const block of content) {
                        if (block.type === "text") {
                            output += block.text;
                        } else if (block.type === "tool_use") {
                            toolsUsed.push(block.name);
                        }
                    }
                } else if (typeof content === "string") {
                    output += content;
                }
            } else if (message.type === "result") {
                console.log(`[Workflow] Completed. Cost: $${message.total_cost_usd}`);
            }
        }

        // Step 6: Update conversation history
        conversation.history.push({ role: "user", content: input.input_as_text });
        conversation.history.push({ role: "assistant", content: output });
        conversation.category = category;

        // Limit history length
        if (conversation.history.length > 20) {
            conversation.history = conversation.history.slice(-20);
        }

        const processingTime = Date.now() - startTime;
        console.log(`[Workflow] Complete in ${processingTime}ms`);
        console.log(`[Workflow] Output: "${output.substring(0, 100)}..."`);
        console.log(`========== INTERNAL WORKFLOW END ==========\n`);

        return {
            output_text: output,
            category,
            toolsUsed
        };

    } catch (error) {
        console.error(`[Workflow] Error:`, error);

        return {
            output_text: "Lo siento, tuve un problema procesando tu solicitud. ¿Podrías intentar de nuevo?",
            error: error instanceof Error ? error.message : "Unknown error",
            toolsUsed: []
        };
    }
}

// ============================================
// Health Check
// ============================================

export function getAgentHealth(): {
    status: string;
    skills: Array<{ code: string; name: string; enabled: boolean }>;
    conversationCount: number;
} {
    return {
        status: "healthy",
        skills: Object.values(SKILL_REGISTRY).map(s => ({
            code: s.code,
            name: s.name,
            enabled: s.enabled
        })),
        conversationCount: conversationStore.size
    };
}
