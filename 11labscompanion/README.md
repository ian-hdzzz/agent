# 11LabsCompanion

The ultimate ElevenLabs AI companion agent, built with Claude Agent SDK. Manage voices, agents, tools, knowledge bases, and more using natural language.

## Architecture

11LabsCompanion follows the same architecture as `maria-claude`:

```
11labscompanion/
├── src/
│   ├── index.ts           # Main entry point & exports
│   ├── agent.ts           # Core workflow with skill routing
│   ├── server.ts          # Express HTTP server
│   ├── tools.ts           # Claude Agent SDK tools (ElevenLabs API)
│   ├── types.ts           # TypeScript definitions
│   └── skills/
│       ├── base.ts        # Skill interface & helpers
│       ├── index.ts       # Skill registry & classification
│       ├── voices.ts      # VOI - Voice management
│       ├── agents.ts      # AGT - Agent management
│       ├── tools.ts       # TLS - Tool management
│       ├── knowledge.ts   # KNB - Knowledge base
│       ├── audio.ts       # AUD - Audio generation
│       ├── conversations.ts # CNV - Conversation history
│       └── account.ts     # ACC - Subscription & account
```

## Skills

| Code | Skill | Description | Tools |
|------|-------|-------------|-------|
| VOI | Voices | List, search, and manage voices | list_voices, get_voice, search_voice_library |
| AGT | Agents | Create and configure AI agents | list_agents, get_agent, create_agent, update_agent, delete_agent |
| TLS | Tools | Manage webhook tools | list_tools, create_webhook_tool, delete_tool |
| KNB | Knowledge | RAG document management | list_knowledge_base, create_knowledge_from_text/url, delete |
| AUD | Audio | TTS and audio generation | text_to_speech, list_models |
| CNV | Conversations | View conversation history | list_conversations, get_conversation |
| ACC | Account | Subscription and usage | get_subscription, list_models, list_phone_numbers |

## Installation

```bash
cd 11labscompanion
npm install
```

## Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Add your ElevenLabs API key:

```
ELEVENLABS_API_KEY=your_api_key_here
PORT=3002
```

## Usage

### Command Line

```bash
# Run a single query
npm run dev -- "list my voices"
npm run dev -- "show my agents"
npm run dev -- "check my subscription"
npm run dev -- "create an agent named CustomerSupport"

# Start the HTTP server
npm run server
```

### HTTP Server

```bash
npm run server
```

Endpoints:
- `GET /` - Service info
- `GET /health` - Health check
- `GET /status` - Detailed status
- `GET /skills` - List available skills
- `POST /api/chat` - Send a message to the agent

Example chat request:

```bash
curl -X POST http://localhost:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "list my voices"}'
```

### As a Module

```typescript
import { runWorkflow } from './agent.js';

const result = await runWorkflow({
  input_as_text: "show me my agents",
  conversationId: "optional-session-id"
});

console.log(result.output_text);
console.log(result.toolsUsed);
```

## Example Conversations

**Voice Management:**
```
User: "Show me all my voices"
Agent: Found 5 voices:
• Rachel (premade) - cgSgspJ2msm6clMCkdW9...
• Adam (premade) - pNInz6obpgDQGcFmaJgB...
...

User: "Search the library for Spanish female voices"
Agent: Found 10 voices in library:
• Sofia - Native Spanish speaker, warm and professional...
...
```

**Agent Management:**
```
User: "Create a customer support agent"
Agent: I'll help you create a new agent. What should it say first when a call starts?

User: "Hello, thank you for calling. How can I help you today?"
Agent: Great! What instructions should the agent follow? (system prompt)

User: "You are a helpful customer support agent for Acme Inc..."
Agent: ✓ Agent created successfully!
Name: Customer Support
ID: agent_abc123...
Language: en
LLM: gemini-2.0-flash-001
```

**Subscription Check:**
```
User: "How much of my quota have I used?"
Agent: 📊 Subscription Status

Tier: Creator
Status: active

Character Usage: 45,230 / 100,000 (45%)
Resets: January 15, 2025

Voice Limit: 30
Pro Voices: 3

Instant Cloning: ✓
Pro Cloning: ✓
```

## How It Works

1. **Message Classification**: User input is classified into one of 7 skill categories based on keywords
2. **Skill Selection**: The appropriate skill's system prompt is loaded
3. **Tool Execution**: Claude Agent SDK runs with available tools
4. **Response**: Agent provides formatted response with next steps

## Integration with MCP

When using Claude Code, the ElevenLabs MCP tools are also available:
- `mcp__elevenlabs__*` - Direct ElevenLabs operations
- `mcp__elevenlabs-agents__*` - Agent-specific operations

The 11LabsCompanion can work alongside these for:
- Complex multi-step workflows through the agent
- Direct API access through MCP tools
- Hybrid approaches

## Development

```bash
# Development mode (watch)
npm run dev

# Build
npm run build

# Run built version
npm start

# Type check
npm run typecheck
```

## License

ISC
