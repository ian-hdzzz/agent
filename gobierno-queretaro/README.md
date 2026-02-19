# Gobierno Querétaro - Multi-Agent Orchestration System

A **LangGraph + Docker Microservices** architecture for the Querétaro Government Portal, featuring 13 specialized AI agents for different government services.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCKER COMPOSE NETWORK                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │            ORCHESTRATOR (LangGraph)                      │   │
│  │   - Intent Classification (13 categories)                │   │
│  │   - Routes to specialist agents                          │   │
│  │   - Port: 8000                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│      ┌───────────┬───────────┼───────────┬───────────┐         │
│      ▼           ▼           ▼           ▼           ▼         │
│  ┌───────┐  ┌───────┐   ┌───────┐  ┌───────┐   ┌───────┐      │
│  │ Water │  │Trans- │   │Educa- │  │Women  │   │ +9    │      │
│  │  CEA  │  │ port  │   │ tion  │  │  IQM  │   │ more  │      │
│  │ :8001 │  │ :8002 │   │ :8003 │  │ :8006 │   │ agents│      │
│  └───────┘  └───────┘   └───────┘  └───────┘   └───────┘      │
│                                                                 │
│  ┌───────────────────────────────────────────────────────┐     │
│  │              SHARED SERVICES                           │     │
│  │  - PostgreSQL (state, tickets)                        │     │
│  │  - Redis (caching, pub/sub events)                    │     │
│  └───────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Anthropic API Key

### Setup

1. **Clone and configure**:
   ```bash
   cd gobierno-queretaro
   cp .env.example .env
   # Edit .env and set ANTHROPIC_API_KEY
   ```

2. **Deploy**:
   ```bash
   ./scripts/deploy.sh
   ```

3. **Test**:
   ```bash
   curl http://localhost:8000/health

   # Route a message
   curl -X POST http://localhost:8000/route \
     -H "Content-Type: application/json" \
     -d '{"message": "Quiero consultar mi saldo de agua"}'
   ```

## Services

| Port | Service | Category | Description |
|------|---------|----------|-------------|
| 8000 | Orchestrator | - | Intent classification & routing |
| 8001 | Water CEA | CEA | Water services, leaks, balance |
| 8002 | Transport AMEQ | TRA | Bus routes, schedules |
| 8003 | Education USEBEQ | EDU | Schools, enrollment, scholarships |
| 8004 | Vehicles | VEH | Plates, fines, licenses |
| 8005 | Psychology SEJUVE | PSI | Mental health, appointments |
| 8006 | Women IQM | IQM | Women's services, violence support |
| 8007 | Culture | CUL | Events, museums, workshops |
| 8008 | Registry RPP | RPP | Documents, certificates |
| 8009 | Labor CCLQ | LAB | Labor conciliation |
| 8010 | Housing IVEQ | VIV | Housing programs, credits |
| 8011 | APPQRO | APP | App support |
| 8012 | Social SEDESOQ | SOC | Social programs, benefits |
| 8013 | Citizen Attention | ATC | General inquiries, complaints |

## API Endpoints

### Orchestrator (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/route` | POST | Route message to appropriate agent |
| `/classify` | POST | Classify intent only (no routing) |
| `/agents` | GET | List all registered agents |
| `/categories` | GET | List all categories with keywords |

### Agent Endpoints (Ports 8001-8013)

Each agent exposes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/query` | POST | Send message to agent |
| `/info` | GET | Agent configuration |

### Example Requests

**Route a message**:
```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hay una fuga de agua en la calle",
    "conversation_id": "conv-123",
    "contact_id": "user-456"
  }'
```

**Classify only**:
```bash
curl -X POST http://localhost:8000/classify \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quiero inscribir a mi hijo en la escuela"
  }'
```

**Direct agent query**:
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Cuánto debo del agua? Mi contrato es 123456"
  }'
```

## Project Structure

```
gobierno-queretaro/
├── docker-compose.yml      # All services configuration
├── .env.example           # Environment template
├── orchestrator/          # Tier 0: Router
│   ├── Dockerfile
│   ├── main.py           # FastAPI server
│   ├── classifier.py     # 13-category classifier
│   ├── router.py         # LangGraph routing
│   └── config.py
├── agents/
│   ├── _template/        # Template for new agents
│   ├── water-cea/        # Water services
│   ├── transport-ameq/   # Transport
│   ├── education-usebeq/ # Education
│   ├── vehicles/         # Vehicle registration
│   ├── psychology-sejuve/# Mental health
│   ├── women-iqm/        # Women's services
│   ├── culture/          # Cultural events
│   ├── registry-rpp/     # Public registry
│   ├── labor-cclq/       # Labor conciliation
│   ├── housing-iveq/     # Housing
│   ├── appqro/           # App support
│   ├── social-sedesoq/   # Social programs
│   └── citizen-attention/# General attention
├── shared/
│   ├── db/
│   │   ├── init.sql      # Database schema
│   │   └── models.py     # Pydantic models
│   ├── events/
│   │   └── pubsub.py     # Redis pub/sub
│   └── utils/
│       └── claude.py     # Claude API wrapper
└── scripts/
    ├── create-agent.sh   # Scaffold new agent
    └── deploy.sh         # Deployment script
```

## Creating a New Agent

Use the scaffold script:

```bash
./scripts/create-agent.sh <agent-id> <agent-name> <category-code>

# Example:
./scripts/create-agent.sh tourism-sectur "Agente de Turismo" TUR
```

Then customize:
1. `agents/<agent-id>/config.py` - Settings
2. `agents/<agent-id>/prompts.py` - System prompts
3. `agents/<agent-id>/tools.py` - Domain tools
4. `agents/<agent-id>/agent.py` - Task handlers

## Development

### Run locally (without Docker)

```bash
# Install dependencies
cd orchestrator
pip install -r requirements.txt

# Run orchestrator
uvicorn orchestrator.main:app --reload --port 8000

# In another terminal, run an agent
cd agents/water-cea
pip install -r ../requirements.txt
uvicorn agent.main:app --reload --port 8001
```

### Useful Docker Commands

```bash
# View logs
docker-compose logs -f orchestrator
docker-compose logs -f agent-water-cea

# Rebuild single service
docker-compose up -d --build agent-water-cea

# Stop all
docker-compose down

# Clean rebuild
docker-compose down -v
docker-compose up -d --build
```

## Classification Keywords

The orchestrator uses keyword matching + LLM for classification:

| Category | Keywords |
|----------|----------|
| CEA | agua, fuga, deuda de agua, consumo, medidor |
| TRA | autobús, ruta, transporte, horario, parada |
| EDU | escuela, inscripción, beca, constancia |
| VEH | placa, multa, licencia, vehículo, tenencia |
| PSI | psicólogo, salud mental, ansiedad, terapia |
| IQM | violencia, mujer, género, acoso, maltrato |
| CUL | cultura, museo, teatro, evento, taller |
| RPP | acta, certificado, registro, documento |
| LAB | trabajo, despido, demanda laboral, finiquito |
| VIV | vivienda, casa, crédito hipotecario, lote |
| APP | app, aplicación, error en app, problema |
| SOC | programa social, apoyo económico, ayuda |
| ATC | queja, sugerencia (default/fallback) |

## License

Gobierno del Estado de Querétaro
