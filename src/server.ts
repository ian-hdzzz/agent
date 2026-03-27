// ============================================
// CEA Agent Server - Production Ready v2.0
// ============================================

import express, { Request, Response, NextFunction } from "express";
import { config } from "dotenv";
import { runWorkflow, getAgentHealth } from "./agent.js";
import type { ChatRequest, ChatResponse } from "./types.js";

// Load environment variables
config();

// ============================================
// Configuration
// ============================================

const PORT = process.env.PORT || 3000;
const NODE_ENV = process.env.NODE_ENV || "development";

// Validate required env vars
const requiredEnvVars = ["OPENAI_API_KEY"];
for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
        console.error(`❌ Missing required environment variable: ${envVar}`);
        process.exit(1);
    }
}

// ============================================
// Express App Setup
// ============================================

const app = express();

// Middleware
app.use(express.json({ limit: "10mb" }));

// Request logging middleware
app.use((req: Request, res: Response, next: NextFunction) => {
    const requestId = crypto.randomUUID().substring(0, 8);
    (req as any).requestId = requestId;
    (req as any).startTime = Date.now();
    
    console.log(`→ [${requestId}] ${req.method} ${req.path}`);
    
    // Log response when finished
    res.on("finish", () => {
        const duration = Date.now() - (req as any).startTime;
        console.log(`← [${requestId}] ${res.statusCode} (${duration}ms)`);
    });
    
    next();
});

// CORS headers for web clients
app.use((req: Request, res: Response, next: NextFunction) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.header("Access-Control-Allow-Headers", "Content-Type, Authorization");
    
    if (req.method === "OPTIONS") {
        return res.sendStatus(200);
    }
    next();
});

// ============================================
// Health & Status Endpoints
// ============================================

// Basic health check (for load balancers)
app.get("/health", (req: Request, res: Response) => {
    res.json({
        status: "ok",
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

// Detailed status (for monitoring)
app.get("/status", (req: Request, res: Response) => {
    const agentHealth = getAgentHealth();
    
    res.json({
        status: "ok",
        version: "2.0.0",
        environment: NODE_ENV,
        timestamp: new Date().toISOString(),
        uptime: Math.floor(process.uptime()),
        memory: {
            heapUsed: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
            heapTotal: Math.round(process.memoryUsage().heapTotal / 1024 / 1024)
        },
        agents: agentHealth
    });
});

// ============================================
// Main Chat Handler
// ============================================

async function handleChat(req: Request, res: Response): Promise<void> {
    const requestId = (req as any).requestId || crypto.randomUUID().substring(0, 8);
    
    try {
        // Extract request data (conversationId is the Chatwoot conversation ID)
        let { message, conversationId, contactId, metadata } = req.body as ChatRequest;

        // Sanitize message input - handle arrays or stringified arrays
        if (Array.isArray(message)) {
            message = message[0] || "";
        } else if (typeof message === "string" && message.startsWith("[") && message.endsWith("]")) {
            try {
                const parsed = JSON.parse(message);
                if (Array.isArray(parsed)) {
                    message = parsed[0] || "";
                }
            } catch {
                // If JSON parse fails, use as-is
            }
        }

        // Validate request
        if (!message || typeof message !== "string") {
            res.status(400).json({
                error: "Missing or invalid 'message' field",
                response: "",
                conversationId: conversationId || crypto.randomUUID()
            } as ChatResponse);
            return;
        }
        
        if (message.length > 10000) {
            res.status(400).json({
                error: "Message too long (max 10000 characters)",
                response: "",
                conversationId: conversationId || crypto.randomUUID()
            } as ChatResponse);
            return;
        }
        
        console.log(`[${requestId}] Processing: "${message.substring(0, 100)}${message.length > 100 ? '...' : ''}"`);
        
        // Run the agent workflow
        // conversationId from Chatwoot is numeric - we use it as both the conversation tracker and Chatwoot link
        const result = await runWorkflow({
            input_as_text: message,
            conversationId: conversationId,
            contactId: contactId,
            metadata: metadata
        });
        
        // Build response
        const response: ChatResponse = {
            response: result.output_text || "Lo siento, no pude procesar tu mensaje.",
            classification: result.classification,
            conversationId: conversationId || crypto.randomUUID(),
            metadata: {
                toolsUsed: result.toolsUsed,
                processingTimeMs: Date.now() - (req as any).startTime
            }
        };
        
        // Include ticket folio if created
        if (result.ticketFolio) {
            response.ticketFolio = result.ticketFolio;
        }
        
        console.log(`[${requestId}] Classification: ${result.classification}`);
        console.log(`[${requestId}] Response length: ${response.response.length} chars`);
        
        res.json(response);
        
    } catch (error) {
        console.error(`[${requestId}] Error:`, error);
        
        const errorMessage = error instanceof Error ? error.message : "Internal server error";
        
        res.status(500).json({
            error: NODE_ENV === "development" ? errorMessage : "Internal server error",
            response: "Lo siento, hubo un error procesando tu mensaje. Por favor intenta de nuevo.",
            conversationId: (req.body as ChatRequest)?.conversationId || crypto.randomUUID()
        } as ChatResponse);
    }
}

// ============================================
// Evolution API Webhook Handler
// ============================================

async function handleEvolutionWebhook(req: Request, res: Response): Promise<void> {
    const requestId = (req as any).requestId || crypto.randomUUID().substring(0, 8);
    const body = req.body;

    // Only process incoming messages
    if (body.event !== "messages.upsert") {
        res.status(200).json({ status: "ignored", reason: "not a message event" });
        return;
    }

    const data = body.data;

    // Ignore messages sent by us
    if (data?.key?.fromMe) {
        res.status(200).json({ status: "ignored", reason: "fromMe" });
        return;
    }

    // Extract message text
    const messageText =
        data?.message?.conversation ||
        data?.message?.extendedTextMessage?.text ||
        data?.message?.imageMessage?.caption ||
        "";

    if (!messageText) {
        res.status(200).json({ status: "ignored", reason: "no text content" });
        return;
    }

    const remoteJid = data?.key?.remoteJid as string;
    const instance = body.instance as string;

    console.log(`[${requestId}] Evolution webhook from ${remoteJid}: "${messageText.substring(0, 80)}"`);

    // Respond 200 immediately so Evolution doesn't retry
    res.status(200).json({ status: "received" });

    try {
        const result = await runWorkflow({
            input_as_text: messageText,
            conversationId: remoteJid,
            contactId: data?.key?.participant || remoteJid,
            metadata: { source: "evolution", instance, pushName: data?.pushName }
        });

        const replyText = result.output_text || "Lo siento, no pude procesar tu mensaje.";

        // Send reply back via Evolution API
        const evolutionUrl = process.env.EVOLUTION_API_URL;
        const evolutionApiKey = process.env.EVOLUTION_API_KEY;

        if (!evolutionUrl || !evolutionApiKey) {
            console.error(`[${requestId}] Missing EVOLUTION_API_URL or EVOLUTION_API_KEY env vars`);
            return;
        }

        const sendUrl = `${evolutionUrl}/message/sendText/${instance}`;
        const sendResponse = await fetch(sendUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "apikey": evolutionApiKey
            },
            body: JSON.stringify({
                number: remoteJid,
                text: replyText
            })
        });

        if (!sendResponse.ok) {
            console.error(`[${requestId}] Failed to send reply: ${sendResponse.status}`);
        } else {
            console.log(`[${requestId}] Reply sent to ${remoteJid}`);
        }

    } catch (error) {
        console.error(`[${requestId}] Evolution handler error:`, error);
    }
}

// ============================================
// API Routes
// ============================================

// Main chat endpoint
app.post("/api/chat", handleChat);

// Evolution API webhook
app.post("/webhook/evolution", handleEvolutionWebhook);

// Webhook alias (for n8n integration)
app.post("/webhook", handleChat);

// Legacy endpoint support
app.post("/chat", handleChat);

// ============================================
// Error Handling
// ============================================

// 404 handler
app.use((req: Request, res: Response) => {
    res.status(404).json({
        error: "Not found",
        message: `Route ${req.method} ${req.path} not found`,
        availableEndpoints: [
            "GET /health - Health check",
            "GET /status - Detailed status",
            "POST /api/chat - Main chat endpoint",
            "POST /webhook - Webhook endpoint (n8n)"
        ]
    });
});

// Global error handler
app.use((error: Error, req: Request, res: Response, next: NextFunction) => {
    console.error("Unhandled error:", error);
    
    res.status(500).json({
        error: NODE_ENV === "development" ? error.message : "Internal server error",
        response: "Lo siento, ocurrió un error inesperado.",
        conversationId: crypto.randomUUID()
    });
});

// ============================================
// Server Startup
// ============================================

const server = app.listen(PORT, () => {
    console.log(`
╔════════════════════════════════════════════════════════╗
║                CEA Agent Server v2.0                   ║
╠════════════════════════════════════════════════════════╣
║  🚀 Running on port ${PORT}                               ║
║  📍 Health: http://localhost:${PORT}/health               ║
║  📊 Status: http://localhost:${PORT}/status               ║
║  💬 Chat:   http://localhost:${PORT}/api/chat             ║
║  🔗 Webhook: http://localhost:${PORT}/webhook             ║
╠════════════════════════════════════════════════════════╣
║  Environment: ${NODE_ENV.padEnd(39)}║
╚════════════════════════════════════════════════════════╝
    `);
});

// Graceful shutdown
process.on("SIGTERM", () => {
    console.log("\n🛑 SIGTERM received, shutting down gracefully...");
    server.close(() => {
        console.log("✅ Server closed");
        process.exit(0);
    });
});

process.on("SIGINT", () => {
    console.log("\n🛑 SIGINT received, shutting down gracefully...");
    server.close(() => {
        console.log("✅ Server closed");
        process.exit(0);
    });
});

export default app;