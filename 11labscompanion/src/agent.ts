/**
 * 11LabsCompanion - Main Agent with Skill Routing
 * Claude Agent SDK powered ElevenLabs management
 */

import { query, createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
import {
  SKILL_REGISTRY,
  getSkill,
  getSkillDescriptions,
  buildSystemContext,
  classifyInput
} from "./skills/index.js";
import { allTools } from "./tools.js";
import type { SkillCode, WorkflowInput, WorkflowOutput } from "./types.js";

// ============================================
// Conversation Store
// ============================================

interface ConversationEntry {
  history: Array<{ role: "user" | "assistant"; content: string }>;
  lastAccess: Date;
  currentSkill?: SkillCode;
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
// Global Conversation Rules
// ============================================

const GLOBAL_RULES = `
You are 11LabsCompanion, the ultimate AI assistant for managing ElevenLabs.

PERSONALITY:
- Helpful, knowledgeable, and efficient
- Expert in ElevenLabs platform and voice AI
- Proactive in offering next steps and suggestions

RESPONSE STYLE:
- Be concise but informative
- Format responses for readability
- Use bullet points for lists
- Show relevant IDs and names
- Offer next steps when appropriate

IMPORTANT RULES:

1. FORMATTED RESPONSES:
   - When tools return "formatted_response", use it directly
   - Add brief context if needed, but don't duplicate info

2. CONFIRMATIONS:
   - Always confirm before DELETE operations
   - Show what will be changed before updates
   - Acknowledge successful operations clearly

3. ERROR HANDLING:
   - If a tool fails, explain what went wrong
   - Suggest alternatives or troubleshooting steps
   - Offer to try again if appropriate

4. COST AWARENESS:
   - Remind users about API credit usage for TTS
   - Suggest efficient approaches
   - Warn before operations that cost credits

5. HELPFUL GUIDANCE:
   - Explain options when users are unsure
   - Suggest best practices
   - Offer to help with related tasks

AVAILABLE CAPABILITIES:
${getSkillDescriptions()}

When asked about what you can do, explain your capabilities clearly.
`;

// ============================================
// Main Workflow
// ============================================

export async function runWorkflow(input: WorkflowInput): Promise<WorkflowOutput> {
  const startTime = Date.now();
  const conversationId = input.conversationId || crypto.randomUUID();

  console.log(`\n========== 11LABS COMPANION WORKFLOW ==========`);
  console.log(`ConversationId: ${conversationId}`);
  console.log(`Input: "${input.input_as_text}"`);

  const conversation = getConversation(conversationId);

  try {
    // Step 1: Classify the intent
    const skill = classifyInput(input.input_as_text);
    console.log(`[Workflow] Classified as: ${skill}`);

    // Get the skill configuration
    const skillConfig = getSkill(skill);
    console.log(`[Workflow] Using skill: ${skillConfig.name}`);

    // Step 2: Build conversation history
    const historyText = conversation.history
      .slice(-10)
      .map(msg => `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`)
      .join('\n');

    // Step 3: Build the full prompt
    const fullPrompt = `${GLOBAL_RULES}

CURRENT SKILL: ${skillConfig.name}
${skillConfig.systemPrompt}

CONTEXT:
${buildSystemContext()}
${input.metadata?.name ? `User: ${input.metadata.name}` : ''}

${historyText ? `CONVERSATION HISTORY:\n${historyText}\n` : ''}

USER MESSAGE:
${input.input_as_text}`;

    let output = "";
    const toolsUsed: string[] = [];

    // Create MCP server with our tools
    const mcpServerConfig = createSdkMcpServer({
      name: "elevenlabs-companion-tools",
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
          "elevenlabs-companion-tools": mcpServerConfig
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

    // Step 4: Update conversation history
    conversation.history.push({ role: "user", content: input.input_as_text });
    conversation.history.push({ role: "assistant", content: output });
    conversation.currentSkill = skill;

    // Limit history length
    if (conversation.history.length > 20) {
      conversation.history = conversation.history.slice(-20);
    }

    const processingTime = Date.now() - startTime;
    console.log(`[Workflow] Complete in ${processingTime}ms`);
    console.log(`[Workflow] Tools used: ${toolsUsed.join(', ') || 'none'}`);
    console.log(`========== WORKFLOW END ==========\n`);

    return {
      output_text: output,
      skill,
      toolsUsed
    };

  } catch (error) {
    console.error(`[Workflow] Error:`, error);

    return {
      output_text: "I encountered an error processing your request. Please try again or check your ElevenLabs API key.",
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
