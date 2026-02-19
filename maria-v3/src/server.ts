// ============================================
// Maria V3 - Express Server with All Endpoints
// ============================================

import express, { Request, Response, NextFunction } from "express";
import { runWorkflow, getAgentHealth, shutdown } from "./agent.js";
import {
    shouldProcessWebhook,
    extractMessageContent,
    processAttachments,
    buildChatwootContext,
    sendToChatwoot,
    getChatwootStatus
} from "./chatwoot.js";
import { classifyIntent, classifyWithFallback } from "./utils/classifier.js";
import { getCache } from "./utils/cache.js";
import { getMemoryStore } from "./utils/memory.js";
import { metrics } from "./utils/metrics.js";
import { apiRateLimiter, createRateLimitMiddleware } from "./utils/ratelimit.js";
import { logger } from "./utils/logger.js";
import { config, validateConfig } from "./config/index.js";
import type { ChatwootWebhookPayload, WorkflowInput } from "./types.js";

// ============================================
// Express App Setup
// ============================================

const app = express();

// Middleware
app.use(express.json({ limit: "1mb" }));

// Request logging
app.use((req: Request, res: Response, next: NextFunction) => {
    const start = Date.now();
    res.on("finish", () => {
        const duration = Date.now() - start;
        logger.info({
            method: req.method,
            path: req.path,
            status: res.statusCode,
            durationMs: duration
        }, "Request completed");
    });
    next();
});

// Rate limiting for API endpoints
app.use("/api", createRateLimitMiddleware(apiRateLimiter));

// ============================================
// Health & Status Endpoints
// ============================================

app.get("/health", (_req: Request, res: Response) => {
    const health = getAgentHealth();
    const statusCode = health.status === "healthy" ? 200 : health.status === "degraded" ? 200 : 503;

    res.status(statusCode).json({
        status: health.status,
        version: "3.0.0",
        timestamp: new Date().toISOString(),
        checks: health.checks
    });
});

app.get("/status", (_req: Request, res: Response) => {
    const health = getAgentHealth();
    const memory = getMemoryStore();
    const cache = getCache();

    res.json({
        status: health.status,
        version: "3.0.0",
        timestamp: new Date().toISOString(),
        skills: health.skills,
        metrics: health.metrics,
        cache: cache.getStats(),
        memory: memory.getStats(),
        chatwoot: getChatwootStatus(),
        uptime: process.uptime()
    });
});

app.get("/metrics", (_req: Request, res: Response) => {
    res.set("Content-Type", "text/plain");
    res.send(metrics.getPrometheusMetrics());
});

// ============================================
// Main Chat Endpoint
// ============================================

app.post("/api/chat", async (req: Request, res: Response) => {
    try {
        const {
            message,
            conversationId,
            metadata,
            chatwootAccountId,
            chatwootConversationId,
            chatwootContactId
        } = req.body;

        if (!message || typeof message !== "string") {
            res.status(400).json({ error: "Message is required" });
            return;
        }

        const input: WorkflowInput = {
            input_as_text: message,
            conversationId,
            metadata,
            chatwootAccountId,
            chatwootConversationId,
            chatwootContactId
        };

        const result = await runWorkflow(input);

        res.json({
            success: !result.error,
            response: result.output_text,
            category: result.category,
            subcategory: result.subcategory,
            toolsUsed: result.toolsUsed,
            processingTimeMs: result.processingTimeMs,
            costUsd: result.costUsd
        });
    } catch (error) {
        logger.error({ error }, "Chat endpoint error");
        res.status(500).json({
            error: "Internal server error",
            message: error instanceof Error ? error.message : "Unknown error"
        });
    }
});

// ============================================
// Classification Endpoint (for testing)
// ============================================

app.post("/api/classify", async (req: Request, res: Response) => {
    try {
        const { message, history, useLLM } = req.body;

        if (!message || typeof message !== "string") {
            res.status(400).json({ error: "Message is required" });
            return;
        }

        const result = useLLM === false
            ? classifyWithFallback(message)
            : await classifyIntent(message, history || [], true);

        res.json({
            success: true,
            classification: result
        });
    } catch (error) {
        logger.error({ error }, "Classification endpoint error");
        res.status(500).json({
            error: "Classification failed",
            message: error instanceof Error ? error.message : "Unknown error"
        });
    }
});

// ============================================
// Cache Management Endpoints
// ============================================

app.get("/api/cache/stats", (_req: Request, res: Response) => {
    const cache = getCache();
    res.json(cache.getStats());
});

app.post("/api/cache/flush", (_req: Request, res: Response) => {
    const cache = getCache();
    cache.flush();
    res.json({ success: true, message: "Cache flushed" });
});

// ============================================
// n8n/WhatsApp Webhook
// ============================================

app.post("/webhook", async (req: Request, res: Response) => {
    try {
        const { message, phone, name, conversationId, metadata } = req.body;

        if (!message) {
            res.status(400).json({ error: "Message is required" });
            return;
        }

        const input: WorkflowInput = {
            input_as_text: message,
            conversationId: conversationId || `webhook-${phone || Date.now()}`,
            metadata: {
                phone,
                name,
                ...metadata
            }
        };

        const result = await runWorkflow(input);

        res.json({
            success: !result.error,
            response: result.output_text,
            category: result.category
        });
    } catch (error) {
        logger.error({ error }, "Webhook error");
        res.status(500).json({ error: "Internal server error" });
    }
});

// ============================================
// Chatwoot/Agora Webhook
// ============================================

app.post("/chatwoot", async (req: Request, res: Response) => {
    try {
        const payload = req.body as ChatwootWebhookPayload;

        // Validate webhook
        const validation = shouldProcessWebhook(payload);
        if (!validation.shouldProcess) {
            logger.debug({ reason: validation.reason }, "Skipping webhook");
            res.status(200).json({ processed: false, reason: validation.reason });
            return;
        }

        // Extract message content
        const { text, attachments, hasMedia } = extractMessageContent(payload);

        // Process media attachments
        let fullMessage = text;
        if (hasMedia) {
            const attachmentText = await processAttachments(attachments);
            fullMessage = [text, attachmentText].filter(Boolean).join("\n\n");
        }

        // Build context
        const context = buildChatwootContext(payload);

        // Run workflow
        const input: WorkflowInput = {
            input_as_text: fullMessage,
            conversationId: context.conversationId,
            metadata: {
                name: context.senderName,
                phone: context.senderPhone,
                email: context.senderEmail,
                custom_attributes: context.customAttributes
            },
            chatwootAccountId: context.accountId,
            chatwootConversationId: context.chatwootConversationId,
            chatwootContactId: context.chatwootContactId
        };

        const result = await runWorkflow(input);

        // Send response back to Chatwoot
        const sendResult = await sendToChatwoot(
            context.accountId,
            context.chatwootConversationId,
            result.output_text
        );

        res.json({
            processed: true,
            sent: sendResult.success,
            category: result.category,
            processingTimeMs: result.processingTimeMs
        });
    } catch (error) {
        logger.error({ error }, "Chatwoot webhook error");
        res.status(500).json({ error: "Internal server error" });
    }
});

// ============================================
// Error Handler
// ============================================

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
    logger.error({ error: err }, "Unhandled error");
    res.status(500).json({
        error: "Internal server error",
        message: config.nodeEnv === "development" ? err.message : undefined
    });
});

// ============================================
// Server Startup
// ============================================

export function startServer(): void {
    // Validate configuration
    const configValidation = validateConfig();
    if (!configValidation.valid) {
        logger.error({ missing: configValidation.missing }, "Missing required configuration");
        process.exit(1);
    }

    const port = config.port;

    const server = app.listen(port, () => {
        logger.info({
            port,
            nodeEnv: config.nodeEnv,
            chatwootConfigured: getChatwootStatus().configured
        }, "Maria V3 server started");
    });

    // Graceful shutdown
    const gracefulShutdown = async (signal: string) => {
        logger.info({ signal }, "Received shutdown signal");

        server.close(async () => {
            logger.info("HTTP server closed");
            await shutdown();
            process.exit(0);
        });

        // Force shutdown after 30 seconds
        setTimeout(() => {
            logger.error("Forced shutdown after timeout");
            process.exit(1);
        }, 30000);
    };

    process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
    process.on("SIGINT", () => gracefulShutdown("SIGINT"));
}

export { app };
