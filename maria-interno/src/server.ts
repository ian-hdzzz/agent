// ============================================
// Maria Interno - Express Server
// API para tickets internos de empleados
// ============================================

import express from "express";
import { config } from "dotenv";
import { runInternalWorkflow, getAgentHealth } from "./agent.js";
import type { InternalWorkflowInput, ChatwootWebhookPayload } from "./types.js";

config();

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;

// ============================================
// Health Check Endpoint
// ============================================

app.get("/health", (_req, res) => {
    const health = getAgentHealth();
    res.json({
        status: health.status,
        service: "maria-interno",
        version: "1.0.0",
        skills: health.skills,
        activeConversations: health.conversationCount,
        timestamp: new Date().toISOString()
    });
});

// ============================================
// Direct API Endpoint
// ============================================

app.post("/api/message", async (req, res) => {
    const startTime = Date.now();

    try {
        const {
            message,
            conversationId,
            employee_id,
            employee_name,
            employee_email,
            area
        } = req.body;

        if (!message) {
            return res.status(400).json({
                success: false,
                error: "El campo 'message' es requerido"
            });
        }

        console.log(`[API] Received message: "${message.substring(0, 50)}..."`);

        const input: InternalWorkflowInput = {
            input_as_text: message,
            conversationId,
            metadata: {
                employee_id,
                employee_name,
                employee_email,
                area
            }
        };

        const result = await runInternalWorkflow(input);

        const responseTime = Date.now() - startTime;
        console.log(`[API] Response in ${responseTime}ms`);

        return res.json({
            success: true,
            response: result.output_text,
            category: result.category,
            tools_used: result.toolsUsed,
            response_time_ms: responseTime
        });

    } catch (error) {
        console.error(`[API] Error:`, error);
        return res.status(500).json({
            success: false,
            error: error instanceof Error ? error.message : "Error interno del servidor"
        });
    }
});

// ============================================
// Chatwoot Webhook Endpoint
// ============================================

app.post("/webhook/chatwoot", async (req, res) => {
    const startTime = Date.now();

    try {
        const payload = req.body as ChatwootWebhookPayload;

        // Only process incoming messages
        if (payload.event !== "message_created" || payload.message_type !== "incoming") {
            return res.status(200).json({ status: "ignored", reason: "not an incoming message" });
        }

        // Skip if no content
        if (!payload.content) {
            return res.status(200).json({ status: "ignored", reason: "empty message" });
        }

        // Skip bot messages
        if (payload.sender.type === "agent_bot") {
            return res.status(200).json({ status: "ignored", reason: "bot message" });
        }

        console.log(`[Chatwoot] Received message from ${payload.sender.name}: "${payload.content.substring(0, 50)}..."`);
        console.log(`[Chatwoot] Sender info: name=${payload.sender.name}, email=${payload.sender.email}, phone=${payload.sender.phone_number}`);

        // Extract employee info from sender
        const input: InternalWorkflowInput = {
            input_as_text: payload.content,
            conversationId: `chatwoot-${payload.conversation.id}`,
            metadata: {
                employee_name: payload.sender.name,
                employee_email: payload.sender.email || undefined,
                employee_phone: payload.sender.phone_number,
                custom_attributes: payload.sender.custom_attributes,
                channel: payload.conversation.channel
            },
            chatwootAccountId: payload.account.id,
            chatwootConversationId: payload.conversation.id
        };

        const result = await runInternalWorkflow(input);

        // Send response back to Chatwoot
        const chatwootApiKey = process.env.CHATWOOT_API_KEY;
        const chatwootBaseUrl = process.env.CHATWOOT_BASE_URL || "https://app.chatwoot.com";

        if (chatwootApiKey) {
            try {
                await fetch(
                    `${chatwootBaseUrl}/api/v1/accounts/${payload.account.id}/conversations/${payload.conversation.id}/messages`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "api_access_token": chatwootApiKey
                        },
                        body: JSON.stringify({
                            content: result.output_text,
                            message_type: "outgoing",
                            private: false
                        })
                    }
                );
                console.log(`[Chatwoot] Response sent successfully`);
            } catch (sendError) {
                console.error(`[Chatwoot] Failed to send response:`, sendError);
            }
        }

        const responseTime = Date.now() - startTime;

        return res.json({
            status: "processed",
            category: result.category,
            response_time_ms: responseTime
        });

    } catch (error) {
        console.error(`[Chatwoot] Webhook error:`, error);
        return res.status(500).json({
            status: "error",
            error: error instanceof Error ? error.message : "Unknown error"
        });
    }
});

// ============================================
// Categories Info Endpoint
// ============================================

app.get("/api/categories", (_req, res) => {
    const { getCategorySummary } = require("./skills/index.js");
    res.json({
        categories: getCategorySummary(),
        total: getCategorySummary().length
    });
});

// ============================================
// Start Server
// ============================================

app.listen(PORT, () => {
    console.log(`
╔═══════════════════════════════════════════════════════╗
║         MARIA INTERNO - Tickets Internos CEA          ║
╠═══════════════════════════════════════════════════════╣
║  Server running on port ${PORT}                          ║
║                                                       ║
║  Endpoints:                                           ║
║  - GET  /health              Health check             ║
║  - POST /api/message         Direct API               ║
║  - POST /webhook/chatwoot    Chatwoot webhook         ║
║  - GET  /api/categories      List categories          ║
║                                                       ║
║  Categories:                                          ║
║  💻 TI  - Tecnologías de Información                  ║
║  👥 RH  - Recursos Humanos                            ║
║  🔧 MNT - Mantenimiento                               ║
║  🚗 VEH - Vehículos                                   ║
║  📦 ALM - Almacén                                     ║
║  📋 ADM - Administrativo                              ║
║  📢 COM - Comunicación                                ║
║  ⚖️  JUR - Jurídico                                    ║
║  🔒 SEG - Seguridad                                   ║
╚═══════════════════════════════════════════════════════╝
    `);
});

export { app };
