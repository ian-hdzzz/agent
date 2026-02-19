# PACO - Pretty Advanced Cognitive Orchestrator

Agent Hub for centralized management, configuration, deployment, monitoring, and observability for AI agents.

## Overview

PACO provides a unified control plane for managing AI agents like maria-claude and maria-voz. It integrates with:

- **Langfuse** - LLM observability, token tracking, cost analytics
- **PostgreSQL** - Central database for agents, tools, users, executions
- **Redis** - Session cache, pub/sub
- **PM2** - Agent process management

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PACO Control Plane                                  │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐        │
│   │Dashboard │ │ Agents   │ │  Tools   │ │Executions│ │ Users │        │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────┘        │
└─────────────────────────────────────────────────────────────────────────┘
            │                    │                     │
            ▼                    ▼                     ▼
┌───────────────────┐  ┌─────────────────────┐  ┌────────────────────────┐
│     Langfuse      │  │    MCP Servers      │  │    Agent Runtime       │
│ - Token tracking  │  │ - cea-tools         │  │ - maria-claude         │
│ - Cost analytics  │  │ - agora-tools       │  │ - maria-voz            │
│ - Traces          │  │ - elevenlabs        │  │ - PM2 managed          │
└───────────────────┘  └─────────────────────┘  └────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+

### 1. Clone and Configure

```bash
cd paco
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start Infrastructure

```bash
docker-compose up -d postgres redis langfuse
```

### 3. Initialize Database

```bash
# Database is auto-initialized via init.sql
# Default admin: admin@paco.local / admin123
```

### 4. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 6. Access PACO

- **PACO Dashboard**: http://localhost:3000
- **PACO API**: http://localhost:8000/docs
- **Langfuse**: http://localhost:3001

## Directory Structure

```
paco/
├── backend/                 # FastAPI Control Plane API
│   ├── app/
│   │   ├── api/            # REST endpoints
│   │   ├── core/           # Config, security, deps
│   │   ├── db/             # Models, session
│   │   └── services/       # PM2, Langfuse clients
│   └── requirements.txt
│
├── frontend/               # Next.js Control Plane UI
│   ├── app/               # Pages
│   ├── components/        # UI components
│   └── lib/               # API client, utils
│
├── mcp-servers/           # Centralized MCP tools
│   ├── cea-tools/         # CEA SOAP API integration
│   └── agora-tools/       # AGORA ticket system
│
├── agents/                # Agent YAML configs
│   ├── maria-claude.yaml
│   └── maria-voz.yaml
│
├── shared/                # Shared modules
│   └── telemetry/         # OpenTelemetry + Langfuse
│
├── db/                    # Database init scripts
│   └── init.sql
│
├── docker-compose.yml
└── .env.example
```

## User Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full access: agents, tools, users, settings |
| **operator** | Start/stop agents, view executions |
| **viewer** | Read-only access to dashboards |

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register
- `GET /api/auth/me` - Current user

### Agents
- `GET /api/agents` - List agents
- `GET /api/agents/{id}` - Get agent
- `POST /api/agents/{id}/start` - Start agent
- `POST /api/agents/{id}/stop` - Stop agent
- `GET /api/agents/sync/yaml` - Sync from YAML

### Tools
- `GET /api/tools` - List tools
- `GET /api/tools/servers` - List MCP servers
- `POST /api/tools/servers/{id}/sync` - Sync tools

### Executions
- `GET /api/executions` - List executions
- `GET /api/executions/metrics/summary` - Token metrics

### Proxy (Langfuse)
- `GET /api/proxy/langfuse/traces` - List traces
- `GET /api/proxy/langfuse/traces/{id}` - Get trace

## MCP Servers

### CEA Tools (`cea-tools`)

Tools for CEA Queretaro SOAP API:

- `get_deuda` - Get debt/balance
- `get_consumo` - Get consumption history
- `get_contract_details` - Get contract info
- `get_recibo_link` - Get receipt download link

### AGORA Tools (`agora-tools`)

Tools for AGORA ticket system:

- `create_ticket` - Create support ticket
- `get_client_tickets` - Get customer tickets
- `update_ticket` - Update ticket status
- `search_customer_by_contract` - Search customer

## Adding Telemetry to Agents

```typescript
import { initTelemetry, createTrace, trackGeneration } from '@paco/telemetry';

// At startup
await initTelemetry({
  serviceName: 'my-agent',
  serviceVersion: '1.0.0',
  langfuse: { enabled: true },
  otel: { enabled: true }
});

// In your agent logic
const trace = createTrace({
  name: 'agent-execution',
  userId: 'user-123',
  sessionId: 'session-abc'
});

// Track LLM calls
trackGeneration(trace, {
  name: 'claude-response',
  model: 'claude-sonnet-4-20250514',
  inputTokens: 1000,
  outputTokens: 500
});
```

## Environment Variables

See `.env.example` for all configuration options.

Key variables:

```bash
# Database
POSTGRES_USER=paco
POSTGRES_PASSWORD=your-password
POSTGRES_DB=paco

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx

# PACO
PACO_SECRET_KEY=your-secret-key
```

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### MCP Servers

```bash
cd mcp-servers/cea-tools
npm install
npm run dev
```

## License

MIT
