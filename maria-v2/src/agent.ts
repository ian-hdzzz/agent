// ============================================
// Maria V2 - Main Agent with Improved Architecture
// ============================================

import { query, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
import {
    SKILL_REGISTRY,
    getSkill,
    buildSystemContext,
    GLOBAL_CONVERSATION_RULES
} from "./skills/index.js";
import { allTools } from "./tools.js";
import { classifyIntent } from "./utils/classifier.js";
import { getMemoryStore } from "./utils/memory.js";
import { validateAndCorrect, sanitizeInput } from "./utils/validator.js";
import { metrics, measurePerformance } from "./utils/metrics.js";
import { conversationRateLimiter, budgetLimiter } from "./utils/ratelimit.js";
import { logger, createConversationLogger } from "./utils/logger.js";
import type { WorkflowInput, WorkflowOutput, CategoryCode } from "./types.js";

// ============================================
// Configuration
// ============================================

const MAX_BUDGET_PER_MESSAGE = 0.50; // $0.50 USD per message
const MAX_CONVERSATION_MESSAGES = 50;

// ============================================
// Main Workflow
// ============================================

export async function runWorkflow(input: WorkflowInput): Promise<WorkflowOutput> {
    const startTime = Date.now();
    const conversationId = input.conversationId || crypto.randomUUID();
    const conversationLogger = createConversationLogger(conversationId, input.metadata);

    conversationLogger.info({ 
        message: input.input_as_text.slice(0, 100),
        hasMetadata: !!input.metadata
    }, "Workflow started");

    // Check rate limits
    const rateLimitResult = conversationRateLimiter.isAllowed(conversationId);
    if (!rateLimitResult.allowed) {
        conversationLogger.warn("Rate limit exceeded");
        return {
            output_text: "Has enviado muchos mensajes muy rápido. Por favor espera un momento antes de continuar.",
            error: "Rate limit exceeded",
            toolsUsed: [],
            processingTimeMs: Date.now() - startTime
        };
    }

    // Sanitize input
    const sanitizedInput = sanitizeInput(input.input_as_text);
    if (sanitizedInput.length === 0) {
        return {
            output_text: "No recibí ningún mensaje. ¿En qué puedo ayudarte?",
            toolsUsed: [],
            processingTimeMs: Date.now() - startTime
        };
    }

    // Get or create conversation
    const memory = getMemoryStore();
    const conversation = memory.createConversation(conversationId, {
        name: input.metadata?.name,
        phone: input.metadata?.phone,
        email: input.metadata?.email,
        customAttributes: input.metadata?.custom_attributes as Record<string, unknown>
    });

    // Check conversation limit
    if (conversation.message_count > MAX_CONVERSATION_MESSAGES) {
        return {
            output_text: "Esta conversación ha alcanzado el límite de mensajes. Por favor inicia una nueva conversación.",
            toolsUsed: [],
            processingTimeMs: Date.now() - startTime
        };
    }

    // Extract contract from input or metadata
    let contractNumber = conversation.contract_number;
    const customContrato = input.metadata?.custom_attributes?.contrato;
    if (customContrato) {
        contractNumber = String(customContrato);
    }

    // Set Chatwoot context for handoff tool
    if (input.chatwootAccountId) {
        process.env.CURRENT_CHATWOOT_ACCOUNT_ID = String(input.chatwootAccountId);
    }
    if (input.chatwootConversationId) {
        process.env.CURRENT_CHATWOOT_CONVERSATION_ID = String(input.chatwootConversationId);
    }

    try {
        // Step 1: Classification with LLM
        conversationLogger.debug("Starting classification");
        
        const history = memory.getHistory(conversationId, 5);
        const historyText = history.map(h => `${h.role}: ${h.content.slice(0, 100)}`);
        
        const { result: classification, durationMs: classificationTime } = await measurePerformance(
            "classification",
            () => classifyIntent(sanitizedInput, historyText, true)
        );

        conversationLogger.info({
            category: classification.category,
            confidence: classification.confidence,
            reasoning: classification.reasoning,
            durationMs: classificationTime
        }, "Classification completed");

        // Update contract number if extracted
        if (classification.extractedContract) {
            contractNumber = classification.extractedContract;
        }

        // Step 2: Get the appropriate skill
        const skill = getSkill(classification.category);
        conversationLogger.debug({ skill: skill.code }, "Using skill");

        // Step 3: Build user context
        let userContext = "";
        if (input.metadata?.name) userContext += `Nombre del usuario: ${input.metadata.name}\n`;
        if (input.metadata?.phone) userContext += `Teléfono: ${input.metadata.phone}\n`;
        if (input.metadata?.email) userContext += `Email: ${input.metadata.email}\n`;
        if (contractNumber) userContext += `Número de contrato: ${contractNumber}\n`;

        // Step 4: Build the prompt
        const historyForPrompt = history
            .slice(-5)
            .map(h => `${h.role === "user" ? "Usuario" : "María"}: ${h.content}`)
            .join("\n");

        const fullPrompt = `${GLOBAL_CONVERSATION_RULES}

${skill.systemPrompt}

CONTEXTO ACTUAL:
${buildSystemContext()}
${userContext ? `\nINFORMACIÓN DEL USUARIO:\n${userContext}` : ""}

${historyForPrompt ? `HISTORIAL RECIENTE:\n${historyForPrompt}\n` : ""}

MENSAJE DEL USUARIO:
${sanitizedInput}

RECUERDA: Si usas una herramienta que retorna "formatted_response", envía EXACTAMENTE ese texto como tu respuesta, sin agregar nada antes ni después.`;

        // Step 5: Run the agent
        conversationLogger.debug("Starting Claude query");
        
        let output = "";
        const toolsUsed: string[] = [];
        let totalCost = 0;

        const mcpServerConfig = createSdkMcpServer({
            name: "maria-v2-tools",
            version: "2.0.0",
            tools: allTools
        });

        const { result: agentResult, durationMs: agentTime } = await measurePerformance(
            "agent_query",
            async () => {
                const result = query({
                    prompt: fullPrompt,
                    options: {
                        model: "claude-sonnet-4-5-20250929",
                        maxBudgetUsd: MAX_BUDGET_PER_MESSAGE,
                        permissionMode: "bypassPermissions",
                        allowDangerouslySkipPermissions: true,
                        mcpServers: {
                            "maria-v2-tools": mcpServerConfig
                        },
                        persistSession: false,
                        tools: [],
                        cwd: process.cwd(),
                        stderr: (data: string) => {
                            conversationLogger.debug({ stderr: data.slice(0, 200) }, "Claude stderr");
                        },
                        env: process.env
                    }
                });

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
                        totalCost = message.total_cost_usd;
                    }
                }

                return { output, toolsUsed, totalCost };
            }
        );

        output = agentResult.output;
        toolsUsed.push(...agentResult.toolsUsed);
        totalCost = agentResult.totalCost;

        // Step 6: Validate and correct response
        const validation = validateAndCorrect(output);
        if (validation.wasCorrected) {
            conversationLogger.warn({
                violations: validation.violations,
                original: validation.original.slice(0, 100)
            }, "Response was auto-corrected");
            output = validation.corrected;
        }

        // Step 7: Record metrics
        const processingTime = Date.now() - startTime;
        
        metrics.recordMessage(conversationId, {
            toolsUsed,
            costUsd: totalCost,
            classification: classification.category,
            responseTimeMs: processingTime
        });

        // Step 8: Update memory
        memory.addMessage(conversationId, "user", sanitizedInput);
        memory.addMessage(conversationId, "assistant", output, {
            toolsUsed,
            category: classification.category
        });

        memory.updateConversation(conversationId, {
            contractNumber,
            category: classification.category,
            costIncrement: totalCost
        });

        // Check if handoff was requested
        if (toolsUsed.includes("handoff_to_human")) {
            metrics.recordHandoff(conversationId);
            memory.updateConversation(conversationId, { handoffOccurred: true });
        }

        conversationLogger.info({
            processingTimeMs: processingTime,
            costUsd: totalCost,
            toolsUsed,
            outputLength: output.length
        }, "Workflow completed");

        return {
            output_text: output,
            category: classification.category,
            subcategory: classification.subcategory,
            toolsUsed,
            confidence: classification.confidence,
            processingTimeMs: processingTime,
            costUsd: totalCost
        };

    } catch (error) {
        const processingTime = Date.now() - startTime;
        conversationLogger.error({ error, processingTimeMs: processingTime }, "Workflow error");

        metrics.recordMessage(conversationId, {
            error: error instanceof Error ? error.message : "Unknown error",
            responseTimeMs: processingTime
        });

        return {
            output_text: "Lo siento, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?",
            error: error instanceof Error ? error.message : "Unknown error",
            toolsUsed: [],
            processingTimeMs: processingTime
        };
    }
}

// ============================================
// Health Check
// ============================================

export function getAgentHealth(): {
    status: "healthy" | "degraded" | "unhealthy";
    skills: string[];
    metrics: ReturnType<typeof metrics.getSystemMetrics>;
    checks: Record<string, boolean>;
} {
    const healthStatus = metrics.getHealthStatus();
    const systemMetrics = metrics.getSystemMetrics();

    return {
        status: healthStatus.status,
        skills: Object.values(SKILL_REGISTRY).map(s => `${s.code}: ${s.name}`),
        metrics: systemMetrics,
        checks: healthStatus.checks
    };
}

// ============================================
// Graceful Shutdown
// ============================================

export async function shutdown(): Promise<void> {
    logger.info("Shutting down agent...");
    
    const { closeMemoryStore } = await import("./utils/memory.js");
    closeMemoryStore();
    
    logger.info("Agent shutdown complete");
}
