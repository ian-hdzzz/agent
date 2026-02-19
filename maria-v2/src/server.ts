// ============================================
// Maria V2 - Express Server
// ============================================

import { config } from "dotenv";
config();

import express from "express";
import rateLimit from "express-rate-limit";
import { runWorkflow, getAgentHealth, shutdown } from "./agent.js";
import { metrics } from "./utils/metrics.js";
import { getCache } from "./utils/cache.js";
import { logger } from "./utils/logger.js";
import type { WorkflowInput, ChatwootWebhookPayload } from "./types.js";

const app = express();

// ============================================
// Middleware
// ============================================

app.use(express.json({ limit: "1mb" }));

// Request logging
app.use((req, res, next) => {
    const start = Date.now();
    res.on("finish", () => {
        logger.info({
            method: req.method,
            path: req.path,
            status: res.statusCode,
            durationMs: Date.now() - start,
            ip: req.ip
        }, "Request completed");
    });
    next();
});

// Rate limiting
const apiLimiter = rateLimit({
    windowMs: 60 * 1000, // 1 minute
    max: 100, // 100 requests per minute
    message: { error: "Too many requests, please try again later" },
    standardHeaders: true,
    legacyHeaders: false
});

app.use("/api/", apiLimiter);

// ============================================
// Routes
// ============================================

/**
 * Health check endpoint
 */
app.get("/health", (req, res) => {
    const health = getAgentHealth();
    res.status(health.status === "healthy" ? 200 : health.status === "degraded" ? 200 : 503).json({
        status: health.status,
        timestamp: new Date().toISOString(),
        version: "2.0.0",
        sdk: "claude-agent-sdk"
    });
});

/**
 * Detailed status endpoint
 */
app.get("/status", (req, res) => {
    const health = getAgentHealth();
    const cacheStats = getCache().getStats();
    
    res.json({
        ...health,
        cache: cacheStats,
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        environment: process.env.NODE_ENV || "development"
    });
});

/**
 * Metrics endpoint (Prometheus format)
 */
app.get("/metrics", (req, res) => {
    const systemMetrics = metrics.getSystemMetrics();
    
    // Simple text format for metrics
    const output = [
        `# HELP maria_conversations_total Total number of conversations`,
        `# TYPE maria_conversations_total counter`,
        `maria_conversations_total ${systemMetrics.totalConversations}`,
        ``,
        `# HELP maria_requests_total Total number of requests`,
        `# TYPE maria_requests_total counter`,
        `maria_requests_total ${systemMetrics.totalRequests}`,
        ``,
        `# HELP maria_errors_total Total number of errors`,
        `# TYPE maria_errors_total counter`,
        `maria_errors_total ${systemMetrics.totalErrors}`,
        ``,
        `# HELP maria_error_rate Error rate percentage`,
        `# TYPE maria_error_rate gauge`,
        `maria_error_rate ${systemMetrics.errorRate}`,
        ``,
        `# HELP maria_cost_usd_total Total cost in USD`,
        `# TYPE maria_cost_usd_total counter`,
        `maria_cost_usd_total ${systemMetrics.totalCostUsd.toFixed(4)}`,
        ``,
        `# HELP maria_average_response_time_ms Average response time in milliseconds`,
        `# TYPE maria_average_response_time_ms gauge`,
        `maria_average_response_time_ms ${systemMetrics.averageResponseTimeMs}`,
        ``,
        `# HELP maria_classification_total Total by classification category`,
        `# TYPE maria_classification_total counter`,
        ...Object.entries(systemMetrics.classificationDistribution).map(
            ([category, count]) => `maria_classification_total{category="${category}"} ${count}`
        ),
        ``,
        `# HELP maria_tool_usage_total Total tool usage`,
        `# TYPE maria_tool_usage_total counter`,
        ...Object.entries(systemMetrics.toolUsage).map(
            ([tool, count]) => `maria_tool_usage_total{tool="${tool}"} ${count}`
        )
    ].join("\n");

    res.set("Content-Type", "text/plain");
    res.send(output);
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

        const sessionId = conversationId || crypto.randomUUID();

        const input: WorkflowInput = {
            input_as_text: message,
            conversationId: sessionId,
            metadata
        };

        const result = await runWorkflow(input);

        res.json({
            success: !result.error,
            response: result.output_text,
            category: result.category,
            subcategory: result.subcategory,
            toolsUsed: result.toolsUsed,
            confidence: result.confidence,
            processingTimeMs: result.processingTimeMs,
            costUsd: result.costUsd,
            conversationId: sessionId
        });
    } catch (error) {
        logger.error({ error }, "Error in /api/chat");
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
            success: !result.error,
            response: result.output_text,
            category: result.category,
            toolsUsed: result.toolsUsed
        });
    } catch (error) {
        logger.error({ error }, "Error in /webhook");
        res.status(500).json({
            success: false,
            error: error instanceof Error ? error.message : "Internal server error"
        });
    }
});

/**
 * Chatwoot/Agora webhook endpoint
 */
app.post("/chatwoot", async (req, res) => {
    const payload = req.body as ChatwootWebhookPayload;

    // Return 200 immediately to avoid Chatwoot timeout
    res.status(200).json({ received: true });

    // Validate webhook
    const validation = shouldProcessWebhook(payload);
    if (!validation.shouldProcess) {
        logger.debug({ reason: validation.reason }, "Skipping webhook");
        return;
    }

    logger.info({
        event: payload.event,
        messageId: payload.id,
        from: payload.sender?.name,
        conversationId: payload.conversation?.id
    }, "Processing Chatwoot webhook");

    try {
        const context = buildChatwootContext(payload);
        const { text, hasMedia } = extractMessageContent(payload);

        if (!text?.trim() && !hasMedia) {
            logger.debug("Empty message, skipping");
            return;
        }

        const input: WorkflowInput = {
            input_as_text: text || "[Media attachment received]",
            conversationId: context.conversationId,
            metadata: {
                name: context.senderName,
                phone: context.senderPhone,
                email: context.senderEmail,
                custom_attributes: context.customAttributes
            },
            chatwootAccountId: context.accountId,
            chatwootConversationId: context.chatwootConversationId
        };

        const result = await runWorkflow(input);

        // Send response back to Chatwoot
        await sendToChatwoot(
            context.accountId,
            context.chatwootConversationId,
            result.output_text
        );

    } catch (error) {
        logger.error({ error, messageId: payload.id }, "Error processing Chatwoot webhook");
    }
});

/**
 * Test endpoint for classification
 */
app.post("/api/classify", async (req, res) => {
    try {
        const { message, useLLM = true } = req.body;
        
        if (!message) {
            res.status(400).json({ error: "Missing 'message' field" });
            return;
        }

        const { classifyIntent } = await import("./utils/classifier.js");
        const result = await classifyIntent(message, [], useLLM);

        res.json({
            success: true,
            classification: result
        });
    } catch (error) {
        logger.error({ error }, "Error in /api/classify");
        res.status(500).json({ error: "Classification failed" });
    }
});

/**
 * Cache management endpoints
 */
app.get("/api/cache/stats", (req, res) => {
    res.json(getCache().getStats());
});

app.post("/api/cache/flush", (req, res) => {
    getCache().flush();
    res.json({ success: true, message: "Cache flushed" });
});

// ============================================
// Chatwoot Helpers
// ============================================

function shouldProcessWebhook(payload: ChatwootWebhookPayload): {
    shouldProcess: boolean;
    reason?: string;
} {
    if (payload.event !== "message_created") {
        return { shouldProcess: false, reason: `Event type: ${payload.event}` };
    }

    if (payload.message_type !== "incoming") {
        return { shouldProcess: false, reason: `Message type: ${payload.message_type}` };
    }

    const senderType = payload.sender?.type;
    if (senderType === "user" || senderType === "agent_bot") {
        return { shouldProcess: false, reason: `Sender type: ${senderType}` };
    }

    const conversationStatus = payload.conversation?.status;
    if (conversationStatus === "open") {
        return { shouldProcess: false, reason: "Conversation open (human handling)" };
    }

    return { shouldProcess: true };
}

function extractMessageContent(payload: ChatwootWebhookPayload): {
    text: string;
    hasMedia: boolean;
} {
    return {
        text: payload.content || "",
        hasMedia: (payload.attachments || []).length > 0
    };
}

function buildChatwootContext(payload: ChatwootWebhookPayload) {
    return {
        conversationId: `chatwoot-${payload.conversation.id}`,
        accountId: payload.account.id,
        chatwootConversationId: payload.conversation.id,
        senderName: payload.sender?.name || "Usuario",
        senderPhone: payload.sender?.phone_number,
        senderEmail: payload.sender?.email || undefined,
        customAttributes: payload.sender?.custom_attributes
    };
}

async function sendToChatwoot(
    accountId: number,
    conversationId: number,
    message: string
): Promise<{ success: boolean; error?: string }> {
    const CHATWOOT_BASE_URL = process.env.CHATWOOT_BASE_URL || "";
    const CHATWOOT_API_TOKEN = process.env.CHATWOOT_API_TOKEN || "";

    if (!CHATWOOT_BASE_URL || !CHATWOOT_API_TOKEN) {
        logger.error("Chatwoot not configured");
        return { success: false, error: "Chatwoot not configured" };
    }

    const url = `${CHATWOOT_BASE_URL}/api/v1/accounts/${accountId}/conversations/${conversationId}/messages`;

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "api_access_token": CHATWOOT_API_TOKEN
            },
            body: JSON.stringify({
                content: message,
                message_type: "outgoing",
                private: false
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API error ${response.status}: ${errorText}`);
        }

        return { success: true };
    } catch (error) {
        logger.error({ error, accountId, conversationId }, "Failed to send to Chatwoot");
        return { success: false, error: String(error) };
    }
}

// ============================================
// Error Handling
// ============================================

app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
    logger.error({ error: err, path: req.path }, "Unhandled error");
    res.status(500).json({ error: "Internal server error" });
});

// ============================================
// Graceful Shutdown
// ============================================

process.on("SIGTERM", async () => {
    logger.info("SIGTERM received, shutting down gracefully");
    await shutdown();
    process.exit(0);
});

process.on("SIGINT", async () => {
    logger.info("SIGINT received, shutting down gracefully");
    await shutdown();
    process.exit(0);
});

// ============================================
// Start Server
// ============================================

const PORT = parseInt(process.env.PORT || "3000");

app.listen(PORT, () => {
    logger.info(`
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   Maria V2 - CEA Agent Server                              ║
║   Powered by Claude Agent SDK                              ║
║                                                            ║
║   Server running on port ${PORT}                              ║
║                                                            ║
║   Endpoints:                                               ║
║   • GET  /health          - Health check                   ║
║   • GET  /status          - Detailed status                ║
║   • GET  /metrics         - Prometheus metrics             ║
║   • POST /api/chat        - Main chat endpoint             ║
║   • POST /api/classify    - Test classification            ║
║   • POST /webhook         - n8n/WhatsApp webhook           ║
║   • POST /chatwoot        - Chatwoot/Agora webhook         ║
║   • GET  /api/cache/stats - Cache statistics               ║
║   • POST /api/cache/flush - Clear cache                    ║
║                                                            ║
║   Features:                                                ║
║   • LLM-based classification                               ║
║   • Persistent SQLite memory                               ║
║   • Response caching                                       ║
║   • Rate limiting                                          ║
║   • Metrics & observability                                ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
`);
});

export default app;
