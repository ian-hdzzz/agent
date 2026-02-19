/**
 * Maria Voz - Express server with ElevenLabs webhook
 */

import { config } from "dotenv";
config();

import express, { Request, Response, NextFunction } from "express";
import { executeTool } from "./tools/index.js";
import { VOICE_CONFIG } from "./config/voice-agent.js";
import { closePool } from "./services/database.js";

// Types for ElevenLabs webhook
interface ElevenLabsToolCall {
  tool_name: string;
  parameters: Record<string, unknown>;
  tool_call_id?: string;
}

interface ElevenLabsWebhookRequest {
  type: "tool_call" | "conversation_initiation" | "conversation_end";
  tool_call?: ElevenLabsToolCall;
  conversation_id?: string;
  agent_id?: string;
}

interface ElevenLabsToolResponse {
  tool_call_id?: string;
  result: string;
  action?: string;
  metadata?: Record<string, unknown>;
}

// Create Express app
const app = express();
const PORT = VOICE_CONFIG.webhookPort;

// Middleware
app.use(express.json());

// Request logging middleware
app.use((req: Request, _res: Response, next: NextFunction) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// Webhook authentication middleware
function authenticateWebhook(req: Request, res: Response, next: NextFunction) {
  const secret = VOICE_CONFIG.webhookSecret;

  // Skip auth if no secret configured (development mode)
  if (!secret) {
    console.warn("[auth] No webhook secret configured, skipping authentication");
    next();
    return;
  }

  // Check for secret in header or query
  const providedSecret = req.headers["x-elevenlabs-secret"] || req.query.secret;

  if (providedSecret !== secret) {
    console.warn("[auth] Invalid webhook secret");
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  next();
}

// Health check endpoint
app.get("/health", (_req: Request, res: Response) => {
  res.json({
    status: "healthy",
    service: "maria-voz",
    timestamp: new Date().toISOString(),
  });
});

// Root endpoint
app.get("/", (_req: Request, res: Response) => {
  res.json({
    service: "maria-voz",
    description: "Voice agent webhook for CEA Querétaro",
    endpoints: {
      health: "GET /health",
      webhook: "POST /webhook",
    },
  });
});

// Tool-specific webhook endpoints for ElevenLabs
// ElevenLabs sends parameters directly in the body to each tool's URL
app.post("/webhook/:toolName", authenticateWebhook, async (req: Request, res: Response) => {
  const { toolName } = req.params;
  const parameters = req.body as Record<string, unknown>;

  console.log(`[webhook/${toolName}] Received request:`, JSON.stringify(parameters, null, 2));

  try {
    // Execute the tool with parameters directly from body
    const result = await executeTool(toolName, parameters);

    console.log(`[webhook/${toolName}] Sending response:`, result.response);
    res.status(200).json({ message: result.response });
  } catch (error) {
    console.error(`[webhook/${toolName}] Error:`, error);
    res.status(200).json({ message: "Lo siento, hubo un problema técnico. Por favor intenta de nuevo." });
  }
});

// Legacy webhook endpoint (for backwards compatibility)
app.post("/webhook", authenticateWebhook, async (req: Request, res: Response) => {
  const body = req.body as ElevenLabsWebhookRequest;

  console.log("[webhook] Received request:", JSON.stringify(body, null, 2));

  try {
    // Handle different webhook types
    switch (body.type) {
      case "conversation_initiation":
        console.log(`[webhook] Conversation started: ${body.conversation_id}`);
        res.json({ status: "ok" });
        return;

      case "conversation_end":
        console.log(`[webhook] Conversation ended: ${body.conversation_id}`);
        res.json({ status: "ok" });
        return;

      case "tool_call":
        if (!body.tool_call) {
          console.error("[webhook] Tool call missing tool_call data");
          res.status(400).json({ error: "Missing tool_call data" });
          return;
        }

        const { tool_name, parameters, tool_call_id } = body.tool_call;
        console.log(`[webhook] Tool call: ${tool_name}`, parameters);

        // Execute the tool
        const result = await executeTool(tool_name, parameters);

        // Build response
        const response: ElevenLabsToolResponse = {
          tool_call_id,
          result: result.response,
        };

        // Add action if present (e.g., handoff)
        if (result.action) {
          response.action = result.action;
        }

        // Add metadata if present
        if (result.metadata) {
          response.metadata = result.metadata;
        }

        console.log(`[webhook] Sending response:`, JSON.stringify(response, null, 2));
        res.json(response);
        return;

      default:
        console.warn(`[webhook] Unknown request type: ${body.type}`);
        res.status(400).json({ error: `Unknown request type: ${body.type}` });
        return;
    }
  } catch (error) {
    console.error("[webhook] Error processing request:", error);
    res.status(500).json({
      error: "Internal server error",
      result: "Lo siento, hubo un problema técnico. Por favor intenta de nuevo.",
    });
  }
});

// Error handling middleware
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error("[error]", err);
  res.status(500).json({
    error: "Internal server error",
    message: err.message,
  });
});

// 404 handler
app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: "Not found" });
});

// Graceful shutdown
async function shutdown() {
  console.log("\n[server] Shutting down...");
  await closePool();
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

// Start server
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════╗
║           MARIA VOZ - CEA Querétaro                ║
║         Voice Agent Webhook Server                 ║
╠════════════════════════════════════════════════════╣
║  Status:    Running                                ║
║  Port:      ${String(PORT).padEnd(40)}║
║  Endpoints:                                        ║
║    GET  /health              - Health check        ║
║    POST /webhook/:toolName   - ElevenLabs tools    ║
║                                                    ║
║  Tools:                                            ║
║    /webhook/consultar_saldo                        ║
║    /webhook/consultar_consumo                      ║
║    /webhook/consultar_contrato                     ║
║    /webhook/consultar_tickets                      ║
║    /webhook/crear_reporte                          ║
║    /webhook/transferir_humano                      ║
╚════════════════════════════════════════════════════╝
  `);
});

export default app;
