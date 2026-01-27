// ============================================
// Maria Claude - Express Server
// ============================================

import { config } from "dotenv";
config();

import express from "express";
import { runWorkflow, getAgentHealth } from "./agent.js";
import {
    sendToChatwoot,
    shouldProcessWebhook,
    extractMessageContent,
    processAttachments,
    buildChatwootContext,
    getChatwootStatus
} from "./chatwoot.js";
import type { WorkflowInput, ChatwootWebhookPayload } from "./types.js";

const app = express();
app.use(express.json());

const PORT = parseInt(process.env.PORT || "3000");

// ============================================
// Middleware
// ============================================

app.use((req, res, next) => {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
    next();
});

// ============================================
// Routes
// ============================================

/**
 * Health check endpoint
 */
app.get("/health", (req, res) => {
    res.json({
        status: "ok",
        timestamp: new Date().toISOString(),
        version: "1.0.0",
        sdk: "claude-agent-sdk"
    });
});

/**
 * Detailed status endpoint
 */
app.get("/status", (req, res) => {
    const health = getAgentHealth();
    const chatwoot = getChatwootStatus();
    res.json({
        ...health,
        chatwoot,
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

/**
 * Main chat endpoint
 */
app.post("/api/chat", async (req, res) => {
    try {
        const { message, conversationId, metadata } = req.body;

        if (!message || typeof message !== "string") {
            res.status(400).json({
                error: "Missing or invalid 'message' field"
            });
            return;
        }

        // Generate or use existing conversationId
        const sessionId = conversationId || crypto.randomUUID();

        const input: WorkflowInput = {
            input_as_text: message,
            conversationId: sessionId,
            metadata
        };

        const result = await runWorkflow(input);

        res.json({
            success: true,
            response: result.output_text,
            category: result.category,
            toolsUsed: result.toolsUsed,
            conversationId: sessionId
        });
    } catch (error) {
        console.error("[/api/chat] Error:", error);
        res.status(500).json({
            success: false,
            error: error instanceof Error ? error.message : "Internal server error"
        });
    }
});

/**
 * Webhook endpoint for n8n/WhatsApp integration
 */
app.post("/webhook", async (req, res) => {
    try {
        const body = req.body;

        // Extract message from various webhook formats
        let message: string | undefined;
        let conversationId: string | undefined;
        let metadata: Record<string, string> | undefined;

        // n8n format
        if (body.message) {
            message = body.message;
            conversationId = body.conversationId || body.phone;
            metadata = {
                phone: body.phone,
                name: body.name
            };
        }
        // WhatsApp Cloud API format
        else if (body.entry?.[0]?.changes?.[0]?.value?.messages?.[0]) {
            const waMessage = body.entry[0].changes[0].value.messages[0];
            message = waMessage.text?.body;
            conversationId = waMessage.from;
            metadata = { phone: waMessage.from };
        }
        // Generic format
        else if (body.text) {
            message = body.text;
            conversationId = body.from || body.sender;
        }

        if (!message) {
            res.status(400).json({ error: "No message found in request" });
            return;
        }

        const input: WorkflowInput = {
            input_as_text: message,
            conversationId,
            metadata
        };

        const result = await runWorkflow(input);

        res.json({
            success: true,
            response: result.output_text,
            category: result.category
        });
    } catch (error) {
        console.error("[/webhook] Error:", error);
        res.status(500).json({
            success: false,
            error: error instanceof Error ? error.message : "Internal server error"
        });
    }
});

/**
 * Chatwoot/Agora webhook endpoint
 * Direct integration without n8n
 */
app.post("/chatwoot", async (req, res) => {
    const payload = req.body as ChatwootWebhookPayload;

    // Return 200 immediately to avoid Chatwoot timeout
    res.status(200).json({ received: true });

    // Validate webhook
    const validation = shouldProcessWebhook(payload);
    if (!validation.shouldProcess) {
        console.log(`[Chatwoot] Skipping: ${validation.reason}`);
        return;
    }

    console.log(`\n========== CHATWOOT WEBHOOK ==========`);
    console.log(`Event: ${payload.event}`);
    console.log(`Message ID: ${payload.id}`);
    console.log(`From: ${payload.sender?.name} (${payload.sender?.phone_number || "no phone"})`);
    console.log(`Conversation: ${payload.conversation?.id}`);
    console.log(`Content: "${payload.content?.substring(0, 100) || "(empty)"}"`);

    try {
        // Extract context
        const context = buildChatwootContext(payload);
        console.log(`[Chatwoot] Sender info: name=${context.senderName}, email=${context.senderEmail}, phone=${context.senderPhone}`);
        const { text, attachments, hasMedia } = extractMessageContent(payload);

        // Build message text
        let messageText = text;

        // Process attachments if any
        if (hasMedia) {
            const attachmentText = await processAttachments(attachments);
            messageText = messageText
                ? `${messageText}\n\n${attachmentText}`
                : attachmentText;
            console.log(`[Chatwoot] Attachments: ${attachments.length}`);
        }

        // Handle empty messages
        if (!messageText.trim()) {
            console.log(`[Chatwoot] Empty message, skipping`);
            return;
        }

        // Process with Maria workflow
        const input: WorkflowInput = {
            input_as_text: messageText,
            conversationId: context.conversationId,
            metadata: {
                name: context.senderName,
                phone: context.senderPhone,
                email: context.senderEmail,
                custom_attributes: context.customAttributes
            },
            // Pass Chatwoot context for handoff
            chatwootAccountId: context.accountId,
            chatwootConversationId: context.chatwootConversationId
        };

        console.log(`[Chatwoot] Processing with Maria...`);
        const result = await runWorkflow(input);

        // Send response back to Chatwoot
        console.log(`[Chatwoot] Sending response back...`);
        const sendResult = await sendToChatwoot(
            context.accountId,
            context.chatwootConversationId,
            result.output_text
        );

        if (sendResult.success) {
            console.log(`[Chatwoot] Response sent successfully`);
        } else {
            console.error(`[Chatwoot] Failed to send response: ${sendResult.error}`);
        }

        console.log(`========== CHATWOOT COMPLETE ==========\n`);

    } catch (error) {
        console.error("[Chatwoot] Processing error:", error);

        // Try to send error message to user
        try {
            const context = buildChatwootContext(payload);
            await sendToChatwoot(
                context.accountId,
                context.chatwootConversationId,
                "Lo siento, tuve un problema procesando tu mensaje. Por favor intenta de nuevo en unos momentos."
            );
        } catch (sendError) {
            console.error("[Chatwoot] Failed to send error message:", sendError);
        }
    }
});

// ============================================
// Start Server
// ============================================

app.listen(PORT, () => {
    const chatwootStatus = getChatwootStatus();
    console.log(`
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   Maria Claude - CEA Agent Server                          ║
║   Powered by Claude Agent SDK                              ║
║                                                            ║
║   Server running on port ${PORT}                              ║
║                                                            ║
║   Endpoints:                                               ║
║   • GET  /health     - Health check                        ║
║   • GET  /status     - Detailed status                     ║
║   • POST /api/chat   - Main chat endpoint                  ║
║   • POST /webhook    - n8n/WhatsApp webhook                ║
║   • POST /chatwoot   - Chatwoot/Agora direct webhook       ║
║                                                            ║
║   Chatwoot: ${chatwootStatus.configured ? "Configured" : "Not configured"}                                 ║
║                                                            ║
║   Skills loaded:                                           ║
║   • CON - Consultas                                        ║
║   • FAC - Facturacion                                      ║
║   • CTR - Contratos                                        ║
║   • CVN - Convenios                                        ║
║   • REP - Reportes de Servicio                             ║
║   • SRV - Servicios Tecnicos                               ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
`);
});

export default app;
