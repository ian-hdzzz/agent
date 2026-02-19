/**
 * 11LabsCompanion - Express Server
 * HTTP API for the ElevenLabs companion agent
 */

import { config } from "dotenv";
config();

import express from "express";
import { runWorkflow, getAgentHealth } from "./agent.js";
import type { WorkflowInput } from "./types.js";

const app = express();
app.use(express.json());

const PORT = parseInt(process.env.PORT || "3002");

// ============================================
// Health Check
// ============================================

app.get("/health", (req, res) => {
  const health = getAgentHealth();
  res.json(health);
});

app.get("/", (req, res) => {
  res.json({
    name: "11LabsCompanion",
    version: "1.0.0",
    description: "The ultimate ElevenLabs AI companion agent",
    endpoints: {
      health: "GET /health",
      chat: "POST /api/chat",
      status: "GET /status"
    }
  });
});

// ============================================
// Status Endpoint
// ============================================

app.get("/status", (req, res) => {
  const health = getAgentHealth();
  res.json({
    status: "online",
    agent: "11LabsCompanion",
    ...health,
    apiKey: process.env.ELEVENLABS_API_KEY ? "configured" : "missing"
  });
});

// ============================================
// Chat Endpoint
// ============================================

app.post("/api/chat", async (req, res) => {
  const startTime = Date.now();

  try {
    const { message, conversationId, metadata } = req.body;

    if (!message) {
      return res.status(400).json({
        success: false,
        error: "Message is required"
      });
    }

    console.log(`[Server] Chat request: "${message.substring(0, 50)}..."`);

    const input: WorkflowInput = {
      input_as_text: message,
      conversationId,
      metadata
    };

    const result = await runWorkflow(input);

    const processingTime = Date.now() - startTime;

    res.json({
      success: true,
      response: result.output_text,
      skill: result.skill,
      toolsUsed: result.toolsUsed,
      conversationId: conversationId || "new",
      processingTime
    });

  } catch (error) {
    console.error("[Server] Chat error:", error);
    res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : "Unknown error"
    });
  }
});

// ============================================
// Skills Info Endpoint
// ============================================

app.get("/skills", (req, res) => {
  const health = getAgentHealth();
  res.json({
    skills: health.skills,
    count: health.skills.length
  });
});

// ============================================
// Start Server
// ============================================

app.listen(PORT, () => {
  console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║     11LabsCompanion Server Started                        ║
║                                                           ║
║     Port: ${PORT}                                            ║
║     Health: http://localhost:${PORT}/health                  ║
║     Chat: POST http://localhost:${PORT}/api/chat             ║
║                                                           ║
║     API Key: ${process.env.ELEVENLABS_API_KEY ? '✓ Configured' : '✗ Missing'}                              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
  `);
});

export default app;
