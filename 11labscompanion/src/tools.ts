/**
 * 11LabsCompanion - Native Tools for Claude Agent SDK
 * All ElevenLabs API operations as Claude tools
 */

import { config } from "dotenv";
config();

import { tool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import type { Voice, Agent, Tool, KnowledgeBaseDocument, Subscription, Model, Conversation, PhoneNumber } from "./types.js";

// ============================================================
// Configuration
// ============================================================

const ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1";

function getHeaders(): Record<string, string> {
  const apiKey = process.env.ELEVENLABS_API_KEY;
  if (!apiKey) {
    throw new Error("ELEVENLABS_API_KEY environment variable is required");
  }
  return {
    "xi-api-key": apiKey,
    "Content-Type": "application/json",
  };
}

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${ELEVENLABS_API_BASE}${endpoint}`;
  console.log(`[ElevenLabs API] ${options.method || 'GET'} ${endpoint}`);

  const response = await fetch(url, {
    ...options,
    headers: { ...getHeaders(), ...options.headers as Record<string, string> },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`ElevenLabs API error: ${response.status} - ${error}`);
  }

  return response.json() as Promise<T>;
}

// ============================================================
// VOICE TOOLS
// ============================================================

export const listVoicesTool = tool(
  "list_voices",
  `Lists all voices in your ElevenLabs library.

Returns: Array of voices with voice_id, name, category, labels, and settings.
Use when: User asks to see their voices, wants to find a voice, or needs voice IDs.`,
  {},
  async () => {
    try {
      const response = await apiRequest<{ voices: Voice[] }>("/voices");
      const voices = response.voices;

      const formatted = voices.map(v =>
        `• ${v.name} (${v.voice_id.substring(0, 20)}...) - ${v.category || 'custom'}`
      ).join('\n');

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            count: voices.length,
            formatted_response: `Found ${voices.length} voices:\n\n${formatted}`,
            voices: voices.map(v => ({
              voice_id: v.voice_id,
              name: v.name,
              category: v.category,
              labels: v.labels
            }))
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const getVoiceTool = tool(
  "get_voice",
  `Gets detailed information about a specific voice.

Returns: Full voice details including settings, samples, and labels.
Use when: User wants details about a specific voice or needs to check voice settings.`,
  {
    voice_id: z.string().describe("The voice ID to get details for")
  },
  async ({ voice_id }) => {
    try {
      const voice = await apiRequest<Voice>(`/voices/${voice_id}`);

      const labels = voice.labels
        ? Object.entries(voice.labels).map(([k, v]) => `${k}: ${v}`).join(', ')
        : 'None';

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `Voice: ${voice.name}\nID: ${voice.voice_id}\nCategory: ${voice.category || 'custom'}\nLabels: ${labels}\nDescription: ${voice.description || 'None'}`,
            voice
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const searchVoiceLibraryTool = tool(
  "search_voice_library",
  `Searches the public ElevenLabs voice library for voices.

Returns: Array of public voices matching the search criteria.
Use when: User wants to find new voices, browse the library, or search for specific voice types.`,
  {
    search: z.string().optional().describe("Search query (name, description, etc.)"),
    page: z.number().optional().describe("Page number (0-indexed)"),
    page_size: z.number().optional().describe("Results per page (max 100)")
  },
  async ({ search, page = 0, page_size = 10 }) => {
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: page_size.toString(),
      });
      if (search) params.set("search", search);

      const response = await apiRequest<{ voices: Voice[] }>(`/shared-voices?${params}`);
      const voices = response.voices;

      const formatted = voices.map(v =>
        `• ${v.name} - ${v.description?.substring(0, 50) || 'No description'}...`
      ).join('\n');

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            count: voices.length,
            formatted_response: `Found ${voices.length} voices in library:\n\n${formatted}`,
            voices: voices.map(v => ({
              voice_id: v.voice_id,
              name: v.name,
              description: v.description,
              labels: v.labels
            }))
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

// ============================================================
// AGENT TOOLS
// ============================================================

export const listAgentsTool = tool(
  "list_agents",
  `Lists all conversational AI agents in your account.

Returns: Array of agents with agent_id, name, language, and configuration.
Use when: User wants to see their agents or find an agent ID.`,
  {},
  async () => {
    try {
      const response = await apiRequest<{ agents: Agent[] }>("/convai/agents");
      const agents = response.agents;

      const formatted = agents.map(a => {
        const lang = a.conversation_config?.agent?.language || 'en';
        const llm = a.conversation_config?.agent?.prompt?.llm || 'default';
        return `• ${a.name} (${a.agent_id.substring(0, 20)}...) - ${lang}, ${llm}`;
      }).join('\n');

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            count: agents.length,
            formatted_response: `Found ${agents.length} agents:\n\n${formatted}`,
            agents: agents.map(a => ({
              agent_id: a.agent_id,
              name: a.name,
              language: a.conversation_config?.agent?.language,
              llm: a.conversation_config?.agent?.prompt?.llm,
              tags: a.tags
            }))
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const getAgentTool = tool(
  "get_agent",
  `Gets detailed configuration of a specific agent.

Returns: Full agent configuration including prompt, voice, tools, and settings.
Use when: User wants to see agent details or needs to check configuration.`,
  {
    agent_id: z.string().describe("The agent ID to get details for")
  },
  async ({ agent_id }) => {
    try {
      const agent = await apiRequest<Agent>(`/convai/agents/${agent_id}`);
      const config = agent.conversation_config;

      const toolCount = config?.agent?.prompt?.tools?.length || 0;
      const kbCount = config?.agent?.prompt?.knowledge_base?.length || 0;

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `Agent: ${agent.name}\nID: ${agent.agent_id}\nLanguage: ${config?.agent?.language || 'en'}\nLLM: ${config?.agent?.prompt?.llm || 'default'}\nVoice ID: ${config?.tts?.voice_id || 'default'}\nTools: ${toolCount}\nKnowledge Base Docs: ${kbCount}\nFirst Message: ${config?.agent?.first_message?.substring(0, 100) || 'None'}...`,
            agent
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const createAgentTool = tool(
  "create_agent",
  `Creates a new conversational AI agent.

PARAMETERS:
- name: Agent name (required)
- first_message: What the agent says first (required)
- system_prompt: Instructions for the agent (required)
- language: Language code (default: en)
- llm: LLM model (default: gemini-2.0-flash-001)
- voice_id: Voice ID to use (optional)
- max_duration_seconds: Max call duration (default: 300)

Returns: Created agent with agent_id.
Use when: User wants to create a new voice agent.`,
  {
    name: z.string().describe("Name for the agent"),
    first_message: z.string().describe("First message the agent says"),
    system_prompt: z.string().describe("System prompt / instructions"),
    language: z.string().optional().describe("Language code (en, es, etc.)"),
    llm: z.string().optional().describe("LLM model to use"),
    voice_id: z.string().optional().describe("Voice ID to use"),
    max_duration_seconds: z.number().optional().describe("Max conversation duration")
  },
  async ({ name, first_message, system_prompt, language = "en", llm = "gemini-2.0-flash-001", voice_id, max_duration_seconds = 300 }) => {
    try {
      const agentConfig = {
        name,
        conversation_config: {
          agent: {
            prompt: {
              prompt: system_prompt,
              llm,
              temperature: 0.5
            },
            first_message,
            language
          },
          tts: voice_id ? { voice_id } : undefined,
          conversation: {
            max_duration_seconds
          }
        }
      };

      const agent = await apiRequest<Agent>("/convai/agents", {
        method: "POST",
        body: JSON.stringify(agentConfig)
      });

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Agent created successfully!\n\nName: ${agent.name}\nID: ${agent.agent_id}\nLanguage: ${language}\nLLM: ${llm}`,
            agent
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const updateAgentTool = tool(
  "update_agent",
  `Updates an existing agent's configuration.

Use when: User wants to modify agent settings, change voice, update prompt, etc.`,
  {
    agent_id: z.string().describe("Agent ID to update"),
    name: z.string().optional().describe("New name"),
    first_message: z.string().optional().describe("New first message"),
    system_prompt: z.string().optional().describe("New system prompt"),
    voice_id: z.string().optional().describe("New voice ID"),
    tags: z.array(z.string()).optional().describe("New tags")
  },
  async ({ agent_id, name, first_message, system_prompt, voice_id, tags }) => {
    try {
      const updates: Record<string, unknown> = {};

      if (name) updates.name = name;
      if (tags) updates.tags = tags;

      if (first_message || system_prompt || voice_id) {
        updates.conversation_config = {};
        if (first_message || system_prompt) {
          (updates.conversation_config as Record<string, unknown>).agent = {};
          if (first_message) {
            ((updates.conversation_config as Record<string, unknown>).agent as Record<string, unknown>).first_message = first_message;
          }
          if (system_prompt) {
            ((updates.conversation_config as Record<string, unknown>).agent as Record<string, unknown>).prompt = { prompt: system_prompt };
          }
        }
        if (voice_id) {
          (updates.conversation_config as Record<string, unknown>).tts = { voice_id };
        }
      }

      const agent = await apiRequest<Agent>(`/convai/agents/${agent_id}`, {
        method: "PATCH",
        body: JSON.stringify(updates)
      });

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Agent ${agent.name} updated successfully!`,
            agent
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const deleteAgentTool = tool(
  "delete_agent",
  `Deletes an agent permanently.

⚠️ WARNING: This action cannot be undone!
Use when: User explicitly confirms they want to delete an agent.`,
  {
    agent_id: z.string().describe("Agent ID to delete")
  },
  async ({ agent_id }) => {
    try {
      await apiRequest(`/convai/agents/${agent_id}`, { method: "DELETE" });

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Agent ${agent_id} deleted successfully.`
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

// ============================================================
// TOOL MANAGEMENT TOOLS
// ============================================================

export const listToolsTool = tool(
  "list_tools",
  `Lists all tools (webhooks/client tools) in your account.

Returns: Array of tools with tool_id, name, type, and description.
Use when: User wants to see available tools or find a tool ID.`,
  {},
  async () => {
    try {
      const response = await apiRequest<{ tools: Tool[] }>("/convai/tools");
      const tools = response.tools;

      const formatted = tools.map(t =>
        `• ${t.name} (${t.type}) - ${t.description?.substring(0, 50) || 'No description'}...`
      ).join('\n');

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            count: tools.length,
            formatted_response: `Found ${tools.length} tools:\n\n${formatted}`,
            tools
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const createWebhookToolTool = tool(
  "create_webhook_tool",
  `Creates a new webhook tool for agents.

PARAMETERS:
- name: Tool name (required)
- description: What the tool does (required)
- url: Webhook URL (required)
- method: HTTP method (default: POST)
- parameters: Array of parameter definitions

Returns: Created tool with tool_id.
Use when: User wants to add a new webhook integration to their agents.`,
  {
    name: z.string().describe("Tool name"),
    description: z.string().describe("Tool description"),
    url: z.string().describe("Webhook URL"),
    method: z.string().optional().describe("HTTP method"),
    parameters: z.array(z.object({
      name: z.string(),
      type: z.string(),
      description: z.string(),
      required: z.boolean().optional()
    })).optional().describe("Tool parameters")
  },
  async ({ name, description, url, method = "POST", parameters }) => {
    try {
      const toolConfig = {
        type: "webhook",
        name,
        description,
        api_schema: { url, method },
        parameters
      };

      const createdTool = await apiRequest<Tool>("/convai/tools", {
        method: "POST",
        body: JSON.stringify(toolConfig)
      });

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Webhook tool created!\n\nName: ${createdTool.name}\nID: ${createdTool.tool_id}\nURL: ${url}`,
            tool: createdTool
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const deleteToolTool = tool(
  "delete_tool",
  `Deletes a tool permanently.

Use when: User wants to remove a tool.`,
  {
    tool_id: z.string().describe("Tool ID to delete")
  },
  async ({ tool_id }) => {
    try {
      await apiRequest(`/convai/tools/${tool_id}`, { method: "DELETE" });

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Tool ${tool_id} deleted.`
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

// ============================================================
// KNOWLEDGE BASE TOOLS
// ============================================================

export const listKnowledgeBaseTool = tool(
  "list_knowledge_base",
  `Lists all knowledge base documents.

Returns: Array of documents with document_id, name, type, and status.
Use when: User wants to see their RAG documents or find a document ID.`,
  {},
  async () => {
    try {
      const response = await apiRequest<{ documents: KnowledgeBaseDocument[] }>("/convai/knowledge-base");
      const docs = response.documents;

      const formatted = docs.map(d => {
        const status = d.status === 'ready' ? '✓' : d.status === 'failed' ? '✗' : '⏳';
        return `${status} ${d.name} (${d.type || 'unknown'}) - ${d.status}`;
      }).join('\n');

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            count: docs.length,
            formatted_response: `Found ${docs.length} knowledge base documents:\n\n${formatted}`,
            documents: docs
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const createKnowledgeFromTextTool = tool(
  "create_knowledge_from_text",
  `Creates a knowledge base document from text content.

Returns: Created document with document_id.
Use when: User wants to add text content to knowledge base.`,
  {
    name: z.string().describe("Document name"),
    text: z.string().describe("Text content"),
    description: z.string().optional().describe("Document description")
  },
  async ({ name, text, description }) => {
    try {
      const doc = await apiRequest<KnowledgeBaseDocument>("/convai/knowledge-base/text", {
        method: "POST",
        body: JSON.stringify({ name, text, description })
      });

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Knowledge base document created!\n\nName: ${doc.name}\nID: ${doc.document_id}\nStatus: ${doc.status}\n\nNote: Processing may take a few minutes.`,
            document: doc
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const createKnowledgeFromUrlTool = tool(
  "create_knowledge_from_url",
  `Creates a knowledge base document by scraping a URL.

Returns: Created document with document_id.
Use when: User wants to import web content to knowledge base.`,
  {
    name: z.string().describe("Document name"),
    url: z.string().describe("URL to scrape"),
    description: z.string().optional().describe("Document description")
  },
  async ({ name, url, description }) => {
    try {
      const doc = await apiRequest<KnowledgeBaseDocument>("/convai/knowledge-base/url", {
        method: "POST",
        body: JSON.stringify({ name, url, description })
      });

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Knowledge base document created from URL!\n\nName: ${doc.name}\nID: ${doc.document_id}\nSource: ${url}\nStatus: ${doc.status}`,
            document: doc
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const deleteKnowledgeDocTool = tool(
  "delete_knowledge_document",
  `Deletes a knowledge base document.

Use when: User wants to remove a document from knowledge base.`,
  {
    document_id: z.string().describe("Document ID to delete")
  },
  async ({ document_id }) => {
    try {
      await apiRequest(`/convai/knowledge-base/${document_id}`, { method: "DELETE" });

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Document ${document_id} deleted.`
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

// ============================================================
// CONVERSATION TOOLS
// ============================================================

export const listConversationsTool = tool(
  "list_conversations",
  `Lists recent agent conversations.

Returns: Array of conversations with metadata.
Use when: User wants to see conversation history or find a conversation.`,
  {
    agent_id: z.string().optional().describe("Filter by agent ID"),
    page_size: z.number().optional().describe("Number of results")
  },
  async ({ agent_id, page_size = 30 }) => {
    try {
      const params = new URLSearchParams({ page_size: page_size.toString() });
      if (agent_id) params.set("agent_id", agent_id);

      const response = await apiRequest<{ conversations: Conversation[] }>(`/convai/conversations?${params}`);
      const convs = response.conversations;

      const formatted = convs.map(c =>
        `• ${c.conversation_id.substring(0, 20)}... | ${c.status || 'unknown'} | ${c.duration_seconds || 0}s`
      ).join('\n');

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            count: convs.length,
            formatted_response: `Found ${convs.length} conversations:\n\n${formatted}`,
            conversations: convs
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const getConversationTool = tool(
  "get_conversation",
  `Gets a conversation with full transcript.

Returns: Conversation details including transcript.
Use when: User wants to see what was said in a conversation.`,
  {
    conversation_id: z.string().describe("Conversation ID")
  },
  async ({ conversation_id }) => {
    try {
      const conv = await apiRequest<Conversation>(`/convai/conversations/${conversation_id}`);

      let transcriptText = "No transcript available";
      if (conv.transcript && conv.transcript.length > 0) {
        transcriptText = conv.transcript.map(t =>
          `[${t.role.toUpperCase()}]: ${t.message}`
        ).join('\n');
      }

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `Conversation: ${conv.conversation_id}\nStatus: ${conv.status || 'unknown'}\nDuration: ${conv.duration_seconds || 0}s\n\n--- Transcript ---\n${transcriptText}`,
            conversation: conv
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

// ============================================================
// ACCOUNT & SUBSCRIPTION TOOLS
// ============================================================

export const getSubscriptionTool = tool(
  "get_subscription",
  `Gets your ElevenLabs subscription status and usage.

Returns: Tier, character usage, limits, and capabilities.
Use when: User asks about their plan, usage, or limits.`,
  {},
  async () => {
    try {
      const sub = await apiRequest<Subscription>("/user/subscription");

      const usagePercent = Math.round((sub.character_count / sub.character_limit) * 100);
      const resetDate = new Date(sub.next_character_count_reset_unix * 1000).toLocaleDateString();

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `📊 Subscription Status\n\nTier: ${sub.tier}\nStatus: ${sub.status}\n\nCharacter Usage: ${sub.character_count.toLocaleString()} / ${sub.character_limit.toLocaleString()} (${usagePercent}%)\nResets: ${resetDate}\n\nVoice Limit: ${sub.voice_limit}\nPro Voices: ${sub.professional_voice_limit}\n\nInstant Cloning: ${sub.can_use_instant_voice_cloning ? '✓' : '✗'}\nPro Cloning: ${sub.can_use_professional_voice_cloning ? '✓' : '✗'}`,
            subscription: sub
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const listModelsTool = tool(
  "list_models",
  `Lists all available ElevenLabs models.

Returns: Array of models with capabilities.
Use when: User wants to know available TTS models or their features.`,
  {},
  async () => {
    try {
      const models = await apiRequest<Model[]>("/models");

      const formatted = models.map(m =>
        `• ${m.name} (${m.model_id})\n  TTS: ${m.can_do_text_to_speech ? '✓' : '✗'} | Voice Conv: ${m.can_do_voice_conversion ? '✓' : '✗'} | Languages: ${m.languages?.length || 0}`
      ).join('\n\n');

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            count: models.length,
            formatted_response: `Available Models:\n\n${formatted}`,
            models
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

export const listPhoneNumbersTool = tool(
  "list_phone_numbers",
  `Lists phone numbers assigned to your account.

Returns: Array of phone numbers with assigned agents.
Use when: User wants to see their Twilio/phone integrations.`,
  {},
  async () => {
    try {
      const response = await apiRequest<{ phone_numbers: PhoneNumber[] }>("/convai/phone-numbers");
      const phones = response.phone_numbers;

      if (phones.length === 0) {
        return {
          content: [{
            type: "text" as const,
            text: JSON.stringify({
              success: true,
              count: 0,
              formatted_response: "No phone numbers configured.",
              phone_numbers: []
            })
          }]
        };
      }

      const formatted = phones.map(p =>
        `• ${p.phone_number} (${p.label || 'no label'})\n  Agent: ${p.assigned_agent_id || 'none'} | Provider: ${p.provider || 'unknown'}`
      ).join('\n\n');

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            count: phones.length,
            formatted_response: `Phone Numbers:\n\n${formatted}`,
            phone_numbers: phones
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

// ============================================================
// AUDIO GENERATION TOOLS
// ============================================================

export const textToSpeechTool = tool(
  "text_to_speech",
  `Converts text to speech audio using ElevenLabs.

⚠️ COST WARNING: This uses API credits!

Returns: Audio file path or confirmation.
Use when: User explicitly asks to generate audio from text.`,
  {
    text: z.string().describe("Text to convert to speech"),
    voice_id: z.string().optional().describe("Voice ID to use"),
    model_id: z.string().optional().describe("Model ID to use")
  },
  async ({ text, voice_id = "EXAVITQu4vr4xnSDxMaL", model_id = "eleven_multilingual_v2" }) => {
    try {
      // Note: In a full implementation, this would save the audio file
      // For now, we'll just acknowledge the request
      const charCount = text.length;

      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: true,
            formatted_response: `✓ Text-to-Speech request prepared\n\nText: "${text.substring(0, 50)}..."\nCharacters: ${charCount}\nVoice: ${voice_id}\nModel: ${model_id}\n\n⚠️ To generate audio, use the MCP tool mcp__elevenlabs__text_to_speech directly.`,
            request: { text, voice_id, model_id, char_count: charCount }
          })
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : "Unknown error"
          })
        }]
      };
    }
  }
);

// ============================================================
// EXPORT ALL TOOLS
// ============================================================

export const allTools = [
  // Voice Tools
  listVoicesTool,
  getVoiceTool,
  searchVoiceLibraryTool,

  // Agent Tools
  listAgentsTool,
  getAgentTool,
  createAgentTool,
  updateAgentTool,
  deleteAgentTool,

  // Tool Management
  listToolsTool,
  createWebhookToolTool,
  deleteToolTool,

  // Knowledge Base
  listKnowledgeBaseTool,
  createKnowledgeFromTextTool,
  createKnowledgeFromUrlTool,
  deleteKnowledgeDocTool,

  // Conversations
  listConversationsTool,
  getConversationTool,

  // Account
  getSubscriptionTool,
  listModelsTool,
  listPhoneNumbersTool,

  // Audio
  textToSpeechTool
];
