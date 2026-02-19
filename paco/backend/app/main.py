"""
PACO Agent Hub - Main Application

FastAPI backend for managing AI agents.
"""

import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api import agent_builder, agents, auth, codegen, company, executions, hive, infrastructures, infra_codegen, infra_deploy, infra_monitor, infra_upgrade, playground, processes, proxy, settings as settings_api, skills, tools, users, workflows, ws
from app.core.config import settings
from app.db.models import Agent, AgentSkill, Base, Skill
from app.services.skill_filesystem import SkillFilesystemService
from app.db.session import async_session_maker, engine
from app.services.langfuse_client import langfuse_client


# =============================================================================
# Startup Helpers
# =============================================================================


async def _ensure_schema_columns():
    """Schema migrations are now handled by Alembic.

    See alembic/versions/ for versioned migration files:
      - 002_add_schema_columns.py
      - 003_create_hive_tables.py
      - 004_agent_tools_uuid_migration.py

    Run migrations with:  alembic upgrade head
    """
    print("Schema migrations managed by Alembic (run: alembic upgrade head)")


async def _create_missing_tables():
    """Create any tables that exist in ORM models but not in the DB.

    This handles fully missing tables like skills and agent_skills.
    NOTE: New schema changes should use Alembic migrations (alembic/versions/).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Missing tables check completed")


async def _sync_agents_on_startup():
    """Read all agent YAML files and upsert into the agents table."""
    agents_path = Path(settings.agents_config_path)
    if not agents_path.exists():
        print(f"Agents config path not found: {agents_path} — skipping auto-seed")
        return

    yaml_files = list(agents_path.glob("*.yaml"))
    if not yaml_files:
        print("No agent YAML files found — skipping auto-seed")
        return

    synced = 0
    async with async_session_maker() as db:
        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    config = yaml.safe_load(f)

                if not config or "name" not in config:
                    continue

                name = config["name"]

                result = await db.execute(select(Agent).where(Agent.name == name))
                agent = result.scalar_one_or_none()

                # Extract model string — YAML may store it as a dict or string
                raw_model = config.get("model")
                if isinstance(raw_model, dict):
                    model_str = raw_model.get("model_id", "claude-sonnet-4-5-20250929")
                elif isinstance(raw_model, str):
                    model_str = raw_model
                else:
                    model_str = None

                if agent:
                    agent.display_name = config.get("display_name", agent.display_name)
                    agent.description = config.get("description", agent.description)
                    agent.port = config.get("runtime", {}).get("port")
                    if model_str:
                        agent.model = model_str
                    if config.get("system_prompt"):
                        agent.system_prompt = config["system_prompt"]
                else:
                    agent = Agent(
                        name=name,
                        display_name=config.get("display_name", name),
                        description=config.get("description"),
                        model=model_str or "claude-sonnet-4-5-20250929",
                        system_prompt=config.get("system_prompt"),
                        port=config.get("runtime", {}).get("port"),
                        pm2_name=name,
                        status="stopped",
                    )
                    db.add(agent)

                await db.commit()
                synced += 1
            except Exception as e:
                print(f"  Error syncing {yaml_file.name}: {e}")
                await db.rollback()

    print(f"Synced {synced} agents from YAML files")


async def _sync_skills_on_startup():
    """Sync skills from filesystem (SKILL.md files) + YAML agent configs.

    1. Scan filesystem for SKILL.md files and upsert DB index.
    2. Read agent YAML files for skill references and upsert agent↔skill links.
    """
    fs = SkillFilesystemService()

    # Phase 1: Scan filesystem for SKILL.md files
    scanned = fs.scan_skills()
    synced_skills = 0
    updated_skills = 0

    async with async_session_maker() as db:
        for skill_data in scanned:
            code = skill_data["code"]
            result = await db.execute(select(Skill).where(Skill.code == code))
            skill = result.scalar_one_or_none()

            if skill:
                skill.name = skill_data.get("name", skill.name)
                skill.description = skill_data.get("description", skill.description)
                skill.skill_path = skill_data.get("skill_path")
                updated_skills += 1
            else:
                db.add(Skill(
                    code=code,
                    name=skill_data.get("name", code),
                    description=skill_data.get("description"),
                    skill_path=skill_data.get("skill_path"),
                    is_active=True,
                ))
                synced_skills += 1

        await db.commit()

    print(f"Filesystem skill sync: {synced_skills} new, {updated_skills} updated from {len(scanned)} SKILL.md files")

    # Phase 2: Read agent YAML files for skill references → agent↔skill links
    agents_path = Path(settings.agents_config_path)
    if not agents_path.exists():
        return

    yaml_files = list(agents_path.glob("*.yaml"))
    if not yaml_files:
        return

    agent_skill_codes: Dict[str, list] = {}

    for yaml_file in yaml_files:
        try:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
            if not config or "name" not in config:
                continue
            raw_skills = config.get("skills", [])
            if not raw_skills:
                continue

            codes = []
            for entry in raw_skills:
                if isinstance(entry, str):
                    codes.append(entry)
                elif isinstance(entry, dict) and "code" in entry:
                    code = entry["code"]
                    codes.append(code)
                    # If YAML provides skill data and no SKILL.md exists, create one
                    if not fs.skill_exists(code):
                        fs.write_skill_md(
                            code,
                            entry.get("name", code),
                            entry.get("description", ""),
                            entry.get("required_tools", []),
                            "",
                        )

            agent_skill_codes[config["name"]] = codes
        except Exception as e:
            print(f"  Error reading skills from {yaml_file.name}: {e}")

    if not agent_skill_codes:
        return

    synced_links = 0
    async with async_session_maker() as db:
        # Ensure DB index exists for YAML-referenced skills
        for codes in agent_skill_codes.values():
            for code in codes:
                result = await db.execute(select(Skill).where(Skill.code == code))
                if not result.scalar_one_or_none():
                    db.add(Skill(
                        code=code,
                        name=code.capitalize(),
                        is_active=True,
                    ))
        await db.commit()

        # Upsert AgentSkill junction records
        for agent_name, codes in agent_skill_codes.items():
            agent_result = await db.execute(select(Agent).where(Agent.name == agent_name))
            agent = agent_result.scalar_one_or_none()
            if not agent:
                continue

            for code in codes:
                skill_result = await db.execute(select(Skill).where(Skill.code == code))
                skill = skill_result.scalar_one_or_none()
                if not skill:
                    continue

                existing = await db.execute(
                    select(AgentSkill).where(
                        AgentSkill.agent_id == agent.id,
                        AgentSkill.skill_id == skill.id,
                    )
                )
                if not existing.scalar_one_or_none():
                    db.add(AgentSkill(agent_id=agent.id, skill_id=skill.id))
                    synced_links += 1

        await db.commit()

    print(f"YAML skill sync: {synced_links} new agent↔skill links")


async def _sync_tools_on_startup():
    """Best-effort: try to sync tools from registered HTTP MCP servers."""
    import httpx
    from app.db.models import McpServer, Tool

    try:
        # First, fetch server info from DB
        async with async_session_maker() as db:
            result = await db.execute(
                select(McpServer).where(McpServer.transport == "http")
            )
            servers = [(s.id, s.name, s.url) for s in result.scalars().all()]

        if not servers:
            print("No HTTP MCP servers registered — skipping tool sync")
            return

        # Then, fetch tools from each server (outside DB session to avoid greenlet issues)
        for server_id, server_name, server_url in servers:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{server_url}/tools")
                    if resp.status_code != 200:
                        print(f"  Tool sync: {server_name} returned {resp.status_code}")
                        continue
                    tools_data = resp.json()

                if isinstance(tools_data, dict):
                    tools_data = tools_data.get("tools", [])

                # Insert into DB in a separate session
                async with async_session_maker() as db:
                    synced = 0
                    for tool_data in tools_data:
                        tool_name = tool_data.get("name")
                        if not tool_name:
                            continue

                        existing = await db.execute(
                            select(Tool).where(
                                Tool.name == tool_name,
                                Tool.mcp_server_id == server_id,
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue

                        tool = Tool(
                            name=tool_name,
                            description=tool_data.get("description"),
                            mcp_server_id=server_id,
                            input_schema=tool_data.get("inputSchema", tool_data.get("input_schema", {})),
                        )
                        db.add(tool)
                        synced += 1

                    if synced:
                        await db.commit()
                        print(f"  Synced {synced} tools from {server_name}")
            except Exception as e:
                print(f"  Tool sync failed for {server_name}: {e}")

    except Exception as e:
        print(f"Tool sync error: {e}")

    print("Tool sync attempt completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")

    # Schema migration (idempotent)
    try:
        await _ensure_schema_columns()
    except Exception as e:
        print(f"Schema migration warning: {e}")

    # Create any fully missing tables
    try:
        await _create_missing_tables()
    except Exception as e:
        print(f"Create tables warning: {e}")

    # Auto-seed agents from YAML
    try:
        await _sync_agents_on_startup()
    except Exception as e:
        print(f"Agent sync warning: {e}")

    # Auto-seed skills from YAML
    try:
        await _sync_skills_on_startup()
    except Exception as e:
        print(f"Skill sync warning: {e}")

    # Best-effort tool sync from MCP servers
    try:
        await _sync_tools_on_startup()
    except Exception as e:
        print(f"Tool sync warning: {e}")

    # Start heartbeat scheduler for company infrastructures
    from app.services.heartbeat_scheduler import heartbeat_scheduler
    try:
        # Try to connect Redis for distributed locking
        redis_client = None
        try:
            import redis.asyncio as aioredis
            redis_url = settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379"
            redis_client = aioredis.from_url(redis_url)
            await redis_client.ping()
            heartbeat_scheduler._redis = redis_client
            print("Heartbeat scheduler: Redis connected")
        except Exception as e:
            print(f"Heartbeat scheduler: Redis not available ({e}), running without lock")
        await heartbeat_scheduler.start()
    except Exception as e:
        print(f"Heartbeat scheduler warning: {e}")

    # Check Langfuse connectivity
    if langfuse_client.is_configured:
        healthy = await langfuse_client.health_check()
        if healthy:
            print("Langfuse connection: OK")
        else:
            print("Langfuse connection: FAILED (check configuration)")
    else:
        print("Langfuse: Not configured")

    yield

    # Shutdown
    try:
        from app.services.heartbeat_scheduler import heartbeat_scheduler
        await heartbeat_scheduler.stop()
    except Exception:
        pass
    print("Shutting down PACO")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="PACO (Pretty Advanced Cognitive Orchestrator) - Agent Hub for managing AI agents",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check including dependencies.

    Checks connectivity to:
    - Database (PostgreSQL)
    - Redis
    - Langfuse
    """
    from app.db.session import engine

    health = {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "dependencies": {},
    }

    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        health["dependencies"]["database"] = {"status": "healthy"}
    except Exception as e:
        health["dependencies"]["database"] = {"status": "unhealthy", "error": str(e)}
        health["status"] = "degraded"

    # Check Langfuse
    if langfuse_client.is_configured:
        langfuse_healthy = await langfuse_client.health_check()
        health["dependencies"]["langfuse"] = {
            "status": "healthy" if langfuse_healthy else "unhealthy",
            "configured": True,
        }
        if not langfuse_healthy:
            health["status"] = "degraded"
    else:
        health["dependencies"]["langfuse"] = {
            "status": "unconfigured",
            "configured": False,
        }

    return health


# =============================================================================
# API Routes
# =============================================================================

# Include API routers
app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(executions.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(proxy.router, prefix="/api")
app.include_router(workflows.router, prefix="/api")
app.include_router(codegen.router, prefix="/api")
app.include_router(infrastructures.router, prefix="/api")
app.include_router(infra_codegen.router, prefix="/api")
app.include_router(infra_deploy.router, prefix="/api")
app.include_router(infra_monitor.router, prefix="/api")
app.include_router(infra_upgrade.router, prefix="/api")
app.include_router(playground.router, prefix="/api")
app.include_router(agent_builder.router, prefix="/api")
app.include_router(hive.router, prefix="/api")
app.include_router(company.router, prefix="/api")
app.include_router(processes.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(ws.router)


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    print(f"Unhandled {type(exc).__name__} on {request.method} {request.url.path}: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {type(exc).__name__}",
            "type": type(exc).__name__,
            "message": str(exc),
        },
    )


# =============================================================================
# Root Endpoint
# =============================================================================


@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "PACO Agent Hub API",
        "docs": "/docs",
        "health": "/health",
    }
