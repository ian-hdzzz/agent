"""
Gobierno Queretaro - Shared Agent Registration Utility

Extracted from agents/_template/main.py so any agent can self-register
with the orchestrator without duplicating code.

Usage:
    from shared.registration import register_with_orchestrator, start_heartbeat_loop

    # In lifespan:
    asyncio.create_task(register_with_orchestrator(settings))
    heartbeat_task = asyncio.create_task(start_heartbeat_loop(settings))
"""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


async def register_with_orchestrator(settings) -> bool:
    """
    Self-register with the orchestrator on startup.

    Args:
        settings: Agent settings object with `to_registration_payload()`
                  and `orchestrator_url` attributes.

    Returns:
        True if registration succeeded.
    """
    payload = settings.to_registration_payload()
    orchestrator_url = settings.orchestrator_url
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{orchestrator_url}/register",
                json=payload,
            )
            if response.status_code == 200:
                logger.info(f"Registered with orchestrator at {orchestrator_url}")
                return True
            else:
                logger.warning(
                    f"Registration returned {response.status_code}: {response.text}"
                )
                return False
    except Exception as e:
        logger.warning(f"Failed to register with orchestrator: {e}")
        return False


async def start_heartbeat_loop(settings) -> None:
    """
    Periodically send heartbeat to orchestrator.

    Args:
        settings: Agent settings object with `heartbeat_interval`,
                  `orchestrator_url`, and `agent_id` attributes.
    """
    interval = settings.heartbeat_interval
    orchestrator_url = settings.orchestrator_url
    agent_id = settings.agent_id

    # Wait before first heartbeat to let registration complete
    await asyncio.sleep(interval)

    while True:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{orchestrator_url}/heartbeat",
                    json={"agent_id": agent_id},
                )
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")
        await asyncio.sleep(interval)
