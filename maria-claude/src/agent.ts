// ============================================
// Maria Claude - Main Agent with Skill Routing
// ============================================

import { query, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
import {
    SKILL_REGISTRY,
    getSkill,
    getSkillDescriptions,
    buildSystemContext
} from "./skills/index.js";
import { allTools } from "./tools.js";
import type { CategoryCode, WorkflowInput, WorkflowOutput } from "./types.js";

// ============================================
// Conversation Store
// ============================================

interface ConversationEntry {
    history: Array<{ role: "user" | "assistant"; content: string }>;
    lastAccess: Date;
    contractNumber?: string;
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
// Classification Prompt
// ============================================

const CLASSIFICATION_PROMPT = `Eres el clasificador de intenciones para CEA Querétaro. Tu trabajo es categorizar cada mensaje del usuario en una de las siguientes categorías AGORA:

${getSkillDescriptions()}

REGLAS DE CLASIFICACIÓN:

1. CON (Consultas):
   - "Hola", saludos simples
   - "¿Cuánto debo?" → CON (consulta de saldo)
   - "¿Cuál es el horario?" → CON
   - "¿Cuál es el estado de mi ticket?" → CON

2. FAC (Facturación):
   - "Quiero mi recibo por correo" → FAC
   - "No entiendo mi recibo" → FAC
   - "Quiero aclarar un cobro" → FAC
   - "Necesito carta de no adeudo" → FAC

3. CTR (Contratos):
   - "Quiero un contrato nuevo" → CTR
   - "Cambio de nombre/titular" → CTR
   - "Quiero dar de baja" → CTR
   - "Cambio de tarifa" → CTR

4. CVN (Convenios):
   - "Quiero un plan de pago" → CVN
   - "No puedo pagar todo" → CVN
   - "Soy pensionado" → CVN
   - "Programa de tercera edad" → CVN

5. REP (Reportes de Servicio):
   - "Hay una fuga" → REP
   - "No tengo agua" → REP
   - "El agua sale turbia" → REP
   - "El drenaje está tapado" → REP
   - Cualquier emergencia → REP

6. SRV (Servicios Técnicos):
   - "Mi medidor está mal" → SRV
   - "Quiero reportar mi lectura" → SRV
   - "Me robaron el medidor" → SRV
   - "Necesito reconexión" → SRV

Si detectas un número de contrato (6+ dígitos), menciónalo.

Responde SOLO con el código de categoría (CON, FAC, CTR, CVN, REP, SRV) y si encontraste un contrato.`;

// ============================================
// Global Conversation Rules
// These apply to ALL skills
// ============================================

const GLOBAL_CONVERSATION_RULES = `
⚠️ REGLAS OBLIGATORIAS DE CONVERSACIÓN - DEBES SEGUIR ESTAS REGLAS SIEMPRE:

1. RESPUESTAS CORTAS (OBLIGATORIO):
   - Máximo 2-3 oraciones por mensaje
   - Estilo WhatsApp, no corporativo
   - NO uses emojis al final de los mensajes

2. UNA PREGUNTA POR MENSAJE (OBLIGATORIO):
   - PROHIBIDO: "¿Tu saldo, consumo o algo más?" (son 3 opciones)
   - PROHIBIDO: "¿Qué necesitas revisar específicamente?"
   - CORRECTO: Pregunta UNA cosa específica
   - Si no sabes qué necesita, pregunta: "¿Qué necesitas saber de tu contrato?"

3. NO USES HERRAMIENTAS PREMATURAMENTE:
   - Si el usuario dice "quiero revisar mi contrato", pregunta QUÉ necesita revisar
   - NO llames a get_contract_details inmediatamente
   - Primero entiende qué información específica necesita

4. NUNCA MENCIONES CÓDIGOS:
   - PROHIBIDO: FAC-004, CON-002, CTR-001, REP-FG-001, etc.
   - El usuario NO entiende estos códigos
   - Solo menciona el FOLIO después de crear el ticket

5. CUANDO UNA HERRAMIENTA FALLA:
   - Si no puedes obtener los datos, dilo claramente
   - Ejemplo: "No pude consultar los detalles en este momento. ¿Qué información específica necesitas?"
   - NO inventes datos ni digas solo "activo" sin más información

6. SALUDO SIMPLE:
   - Si tienes el nombre del usuario, saluda personalizado: "¡Hola {NOMBRE}! Bienvenido a la CEA, soy María, ¿en qué te puedo ayudar hoy?"
   - Si NO tienes el nombre: "¡Hola! Bienvenido a la CEA, soy María, ¿en qué te puedo ayudar hoy?"
   - NADA MÁS

7. MOSTRAR DATOS COMPLETOS:
   - Si consultas datos exitosamente, muéstralos TODOS de una vez
   - NO preguntes "¿qué quieres saber?" después de consultar
   - Ejemplo: "Tu contrato 523160: Titular Juan Pérez, Calle Principal 123, Tarifa doméstica, Estado activo"

8. RESPUESTAS FORMATEADAS (CRÍTICO):
   - Cuando un tool retorna "formatted_response", envíalo EXACTAMENTE como está
   - NO agregues texto ANTES ("Claro...", "Aquí está...", "Listo...", "Déjame...")
   - NO agregues texto DESPUÉS
   - NO agregues emojis
   - El formatted_response ES tu respuesta completa, NADA MÁS

9. ENCABEZADO DE RESPUESTA (OBLIGATORIO):
   - PROHIBIDO: "Voy a consultar...", "Déjame revisar...", "Un momento..."
   - CORRECTO: Empieza SIEMPRE con "¡Claro, aquí está!" seguido de línea en blanco
   - Luego muestra el formatted_response tal cual
   - NUNCA agregues texto descriptivo que repita lo que ya dice el formatted_response

10. TRANSFERENCIA A HUMANO:
   - Si el usuario dice "quiero hablar con una persona", "agente humano", "hablar con alguien", etc.
   - Usa la herramienta handoff_to_human con el motivo de la transferencia

=====================================
⚠️ REGLAS CRÍTICAS ADICIONALES
=====================================

11. USUARIOS NO PUEDEN CERRAR TICKETS:
    - Si el usuario pide cerrar un ticket, NO uses update_ticket para cerrarlo
    - Responde: "Para cerrar tu ticket necesito comunicarte con un asesor 👤"
    - Usa handoff_to_human en su lugar

12. PAGOS - NO PIDAS CONTRATO:
    - Si el usuario pregunta "quiero pagar" o "cómo puedo pagar"
    - NO pidas número de contrato
    - Solo muestra las opciones de pago directamente

13. EVIDENCIA FOTOGRÁFICA:
    - Para REPORTES (fugas, drenaje, calidad): SIEMPRE pide foto de evidencia
    - Para LECTURAS de medidor: SIEMPRE pide foto del medidor
    - Para REVISAR RECIBO: pide imagen o PDF del recibo
    - Si ya enviaron una foto, NO la pidas de nuevo

14. ACLARACIONES Y AJUSTES:
    - Para aclaraciones: pregunta si tiene contrato, pero si dice que NO, avanza sin él
    - El contrato es ÚTIL pero NO obligatorio para aclaraciones
    - Usa handoff_to_human para transferir a asesor
    - NO intentes resolver aclaraciones, siempre transfiere a asesor

15. SEGUIMIENTO NATURAL (OBLIGATORIO):
    - Después de mostrar información de saldo/deuda, pregunta: "¿Quieres hacer un pago o tienes dudas sobre tu saldo?"
    - Después de mostrar datos de contrato, pregunta: "¿Necesitas realizar algún trámite o tienes alguna duda?"
    - Después de crear un ticket, pregunta: "¿Hay algo más en que pueda ayudarte?"
    - Incluye la pregunta en el MISMO mensaje, separada por una línea en blanco
`;

// ============================================
// Main Workflow
// ============================================

export async function runWorkflow(input: WorkflowInput): Promise<WorkflowOutput> {
    const startTime = Date.now();
    const conversationId = input.conversationId || crypto.randomUUID();

    console.log(`\n========== WORKFLOW START ==========`);
    console.log(`ConversationId: ${conversationId}`);
    console.log(`Input: "${input.input_as_text}"`);

    // Set Chatwoot context for handoff tool
    if (input.chatwootAccountId) {
        process.env.CURRENT_CHATWOOT_ACCOUNT_ID = String(input.chatwootAccountId);
    }
    if (input.chatwootConversationId) {
        process.env.CURRENT_CHATWOOT_CONVERSATION_ID = String(input.chatwootConversationId);
    }

    const conversation = getConversation(conversationId);
    const contextualInput = `${buildSystemContext()}\n${input.input_as_text}`;

    try {
        // Step 1: Classification
        console.log(`[Workflow] Running classification...`);

        let category: CategoryCode = "CON"; // Default
        let extractedContract: string | undefined;

        // Simple classification based on keywords
        const inputLower = input.input_as_text.toLowerCase();

        if (inputLower.includes("fuga") || inputLower.includes("no hay agua") ||
            inputLower.includes("agua turbia") || inputLower.includes("drenaje") ||
            inputLower.includes("no tengo agua") || inputLower.includes("inundación")) {
            category = "REP";
        } else if (inputLower.includes("recibo") || inputLower.includes("factura") ||
                   inputLower.includes("aclaración") || inputLower.includes("ajuste") ||
                   inputLower.includes("cobro") || inputLower.includes("pagar") ||
                   inputLower.includes("pago")) {
            category = "FAC";
        } else if (inputLower.includes("contrato") || inputLower.includes("titular") ||
                   inputLower.includes("baja") || inputLower.includes("alta") ||
                   inputLower.includes("cambio de nombre")) {
            category = "CTR";
        } else if (inputLower.includes("convenio") || inputLower.includes("plan de pago") ||
                   inputLower.includes("pensionado") || inputLower.includes("tercera edad") ||
                   inputLower.includes("no puedo pagar")) {
            category = "CVN";
        } else if (inputLower.includes("medidor") || inputLower.includes("lectura") ||
                   inputLower.includes("reconexión") || inputLower.includes("instalación")) {
            category = "SRV";
        } else if (inputLower.includes("saldo") || inputLower.includes("cuánto debo") ||
                   inputLower.includes("deuda") || inputLower.includes("adeudo")) {
            category = "CON";
        }

        // Extract contract number if present
        const contractMatch = input.input_as_text.match(/\b(\d{6,10})\b/);
        if (contractMatch) {
            extractedContract = contractMatch[1];
            conversation.contractNumber = extractedContract;
        }

        console.log(`[Workflow] Classification: ${category}`);
        if (extractedContract) {
            console.log(`[Workflow] Extracted contract: ${extractedContract}`);
        }

        // Step 2: Get the appropriate skill
        const skill = getSkill(category);
        console.log(`[Workflow] Using skill: ${skill.name}`);

        // Step 3: Build conversation history
        const historyText = conversation.history
            .slice(-10) // Last 10 messages
            .map(msg => `${msg.role === 'user' ? 'Usuario' : 'María'}: ${msg.content}`)
            .join('\n');

        // Step 3.5: Build user context from metadata
        let userContext = '';
        if (input.metadata?.name) userContext += `Nombre del usuario: ${input.metadata.name}\n`;
        if (input.metadata?.phone) userContext += `Teléfono: ${input.metadata.phone}\n`;
        if (input.metadata?.email) userContext += `Email: ${input.metadata.email}\n`;

        // Extract contract from custom_attributes if available
        const customContrato = input.metadata?.custom_attributes?.contrato;
        if (customContrato) {
            conversation.contractNumber = String(customContrato);
        }
        if (conversation.contractNumber) userContext += `Número de contrato: ${conversation.contractNumber}\n`;

        // Step 4: Run the agent with the skill
        // IMPORTANT: Global rules go FIRST to have priority over skill-specific instructions
        const fullPrompt = `${GLOBAL_CONVERSATION_RULES}

${skill.systemPrompt}

CONTEXTO ACTUAL:
${buildSystemContext()}
${userContext ? `\nINFORMACIÓN DEL USUARIO:\n${userContext}` : ''}

${historyText ? `HISTORIAL DE CONVERSACIÓN:\n${historyText}\n` : ''}

MENSAJE DEL USUARIO:
${input.input_as_text}`;

        let output = "";
        const toolsUsed: string[] = [];

        // Create MCP server with our tools
        const mcpServerConfig = createSdkMcpServer({
            name: "maria-cea-tools",
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
                    "maria-cea-tools": mcpServerConfig
                },
                // Server environment settings
                persistSession: false,
                tools: [],  // Disable built-in Claude Code tools, only use MCP tools
                cwd: process.cwd(),
                stderr: (data: string) => {
                    console.error(`[Claude Code STDERR]: ${data}`);
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
                // Result is already captured from assistant messages
            }
        }

        // Step 5: Update conversation history
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
        console.log(`========== WORKFLOW END ==========\n`);

        return {
            output_text: output,
            category,
            toolsUsed
        };

    } catch (error) {
        console.error(`[Workflow] Error:`, error);

        return {
            output_text: "Lo siento, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?",
            error: error instanceof Error ? error.message : "Unknown error",
            toolsUsed: []
        };
    }
}

// ============================================
// Health Check
// ============================================

export function getAgentHealth(): { status: string; skills: string[]; conversationCount: number } {
    return {
        status: "healthy",
        skills: Object.values(SKILL_REGISTRY).map(s => `${s.code}: ${s.name}`),
        conversationCount: conversationStore.size
    };
}
