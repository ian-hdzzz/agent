"""
PACO Agent Manager

Manages agent lifecycle, configuration, and health monitoring.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Agent
from app.services.pm2_client import PM2Client


class AgentManager:
    """Manages agent lifecycle and health."""

    def __init__(self):
        self.pm2 = PM2Client()
        self.health_check_timeout = 10.0

    async def sync_from_yaml(self, db: AsyncSession) -> List[Agent]:
        """
        Sync agents from YAML configuration files.

        Reads all .yaml files from the agents config directory and
        creates/updates agent records in the database.
        """
        agents_path = Path(settings.agents_config_path)
        synced_agents = []

        if not agents_path.exists():
            return synced_agents

        for yaml_file in agents_path.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    config = yaml.safe_load(f)

                if not config or "name" not in config:
                    continue

                agent = await self._sync_agent_config(db, config, yaml_file)
                if agent:
                    synced_agents.append(agent)

            except Exception as e:
                print(f"Error syncing {yaml_file}: {e}")

        return synced_agents

    async def _sync_agent_config(
        self,
        db: AsyncSession,
        config: Dict[str, Any],
        yaml_file: Path,
    ) -> Optional[Agent]:
        """Sync a single agent configuration."""
        name = config["name"]
        config_yaml = yaml.dump(config)

        # Check if agent exists
        result = await db.execute(select(Agent).where(Agent.name == name))
        agent = result.scalar_one_or_none()

        if agent:
            # Update existing
            agent.config_yaml = config_yaml
            agent.type = config.get("type", agent.type)
            agent.version = config.get("version", "1.0.0")
            agent.port = config.get("runtime", {}).get("port")
            agent.display_name = config.get("display_name", agent.name)
            agent.description = config.get("description")
        else:
            # Create new
            agent = Agent(
                name=name,
                display_name=config.get("display_name", name),
                description=config.get("description"),
                type=config.get("type", "custom"),
                version=config.get("version", "1.0.0"),
                config_yaml=config_yaml,
                port=config.get("runtime", {}).get("port"),
                pm2_name=name,
                status="stopped",
            )
            db.add(agent)

        await db.commit()
        await db.refresh(agent)
        return agent

    async def check_health(self, agent: Agent) -> Dict[str, Any]:
        """
        Check the health of an agent.

        Returns health status and updates agent record.
        """
        health_result = {
            "agent_id": str(agent.id),
            "name": agent.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pm2_status": None,
            "http_health": None,
            "overall_status": "unknown",
        }

        # Check PM2 status
        if agent.pm2_name:
            pm2_status = await self.pm2.status(agent.pm2_name)
            if pm2_status:
                pm2_state = pm2_status.get("pm2_env", {}).get("status", "").lower()
                health_result["pm2_status"] = {
                    "status": pm2_state,
                    "pid": pm2_status.get("pid"),
                    "memory": pm2_status.get("monit", {}).get("memory"),
                    "cpu": pm2_status.get("monit", {}).get("cpu"),
                    "uptime": pm2_status.get("pm2_env", {}).get("pm_uptime"),
                }

        # Check HTTP health endpoint
        if agent.port and agent.health_endpoint:
            try:
                async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
                    url = f"http://localhost:{agent.port}{agent.health_endpoint}"
                    response = await client.get(url)
                    health_result["http_health"] = {
                        "status_code": response.status_code,
                        "healthy": response.status_code == 200,
                    }
            except Exception as e:
                health_result["http_health"] = {
                    "status_code": None,
                    "healthy": False,
                    "error": str(e),
                }

        # Determine overall status
        pm2_online = (
            health_result["pm2_status"]
            and health_result["pm2_status"]["status"] == "online"
        )
        http_healthy = (
            health_result["http_health"]
            and health_result["http_health"]["healthy"]
        )

        if pm2_online and http_healthy:
            health_result["overall_status"] = "healthy"
        elif pm2_online:
            health_result["overall_status"] = "degraded"
        else:
            health_result["overall_status"] = "unhealthy"

        return health_result

    async def check_all_health(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Check health of all registered agents."""
        result = await db.execute(select(Agent))
        agents = result.scalars().all()

        health_results = []
        for agent in agents:
            health = await self.check_health(agent)
            health_results.append(health)

            # Update agent status based on health
            if health["overall_status"] == "healthy":
                agent.status = "running"
            elif health["overall_status"] == "degraded":
                agent.status = "running"  # Still running, just degraded
            elif health["pm2_status"] and health["pm2_status"]["status"] == "stopped":
                agent.status = "stopped"
            else:
                agent.status = "error"

            agent.last_health_check = datetime.now(timezone.utc)

        await db.commit()
        return health_results

    async def start_agent(self, agent: Agent) -> Dict[str, Any]:
        """Start an agent via PM2."""
        if not agent.pm2_name:
            raise ValueError(f"Agent {agent.name} has no PM2 configuration")

        result = await self.pm2.start(agent.pm2_name)
        return result

    async def stop_agent(self, agent: Agent) -> Dict[str, Any]:
        """Stop an agent via PM2."""
        if not agent.pm2_name:
            raise ValueError(f"Agent {agent.name} has no PM2 configuration")

        result = await self.pm2.stop(agent.pm2_name)
        return result

    async def restart_agent(self, agent: Agent) -> Dict[str, Any]:
        """Restart an agent via PM2."""
        if not agent.pm2_name:
            raise ValueError(f"Agent {agent.name} has no PM2 configuration")

        result = await self.pm2.restart(agent.pm2_name)
        return result

    async def get_logs(self, agent: Agent, lines: int = 100) -> str:
        """Get recent logs for an agent."""
        if not agent.pm2_name:
            return ""

        return await self.pm2.logs(agent.pm2_name, lines=lines)

    def parse_config(self, agent: Agent) -> Dict[str, Any]:
        """Parse agent's YAML configuration."""
        if not agent.config_yaml:
            return {}

        try:
            return yaml.safe_load(agent.config_yaml)
        except yaml.YAMLError:
            return {}

    async def get_agent_metrics(self, agent: Agent) -> Dict[str, Any]:
        """Get runtime metrics for an agent."""
        metrics = {
            "agent_id": str(agent.id),
            "name": agent.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if agent.pm2_name:
            status = await self.pm2.status(agent.pm2_name)
            if status:
                monit = status.get("monit", {})
                metrics["memory_bytes"] = monit.get("memory", 0)
                metrics["cpu_percent"] = monit.get("cpu", 0)

                pm2_env = status.get("pm2_env", {})
                metrics["restart_count"] = pm2_env.get("restart_time", 0)
                metrics["uptime_ms"] = pm2_env.get("pm_uptime")

        return metrics


# Singleton instance
agent_manager = AgentManager()
