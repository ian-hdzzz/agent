"""
Gobierno Queretaro - Per-Agent Heartbeat Loop

Runs inside each agent process as asyncio background tasks.
Each agent fetches its own schedules from PACO, runs heartbeat checks
through its own LangGraph, and reports results back.

Usage:
    from shared.heartbeat import AgentHeartbeatLoop

    loop = AgentHeartbeatLoop(
        agent_slug="vehicles",
        paco_api_url="http://localhost:8000",
        infrastructure_id="...",
        agent_graph=agent.graph,
    )
    await loop.start()
    # ... later ...
    await loop.stop()
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def _compute_next_trigger(schedule: dict) -> datetime:
    """Compute next trigger time from a schedule dict."""
    now = datetime.now(timezone.utc)
    schedule_type = schedule.get("schedule_type", "heartbeat")
    interval = schedule.get("interval_seconds")
    cron_expr = schedule.get("cron_expression")
    tz_name = schedule.get("timezone", "America/Mexico_City")

    if schedule_type == "cron" and cron_expr:
        try:
            from croniter import croniter
            import zoneinfo
            local_tz = zoneinfo.ZoneInfo(tz_name)
            local_now = now.astimezone(local_tz)
            cron = croniter(cron_expr, local_now)
            next_local = cron.get_next(datetime)
            return next_local.astimezone(timezone.utc)
        except Exception:
            return now + timedelta(hours=1)

    if interval:
        return now + timedelta(seconds=interval)

    return now + timedelta(minutes=30)


def _is_within_active_hours(schedule: dict, config_defaults: dict | None = None) -> bool:
    """Check if current time is within active hours for a schedule."""
    import zoneinfo

    defaults = config_defaults or {}
    tz_name = schedule.get("timezone") or defaults.get("timezone", "America/Mexico_City")
    active_start = schedule.get("active_hours_start") or defaults.get("active_hours_start")
    active_end = schedule.get("active_hours_end") or defaults.get("active_hours_end")
    working_days = defaults.get("working_days", [1, 2, 3, 4, 5])

    local_tz = zoneinfo.ZoneInfo(tz_name)
    now_local = datetime.now(local_tz)

    if working_days and now_local.isoweekday() not in working_days:
        return False

    if active_start and active_end:
        try:
            start_h, start_m = map(int, active_start.split(":"))
            end_h, end_m = map(int, active_end.split(":"))
            current_minutes = now_local.hour * 60 + now_local.minute
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m
            return start_minutes <= current_minutes <= end_minutes
        except (ValueError, AttributeError):
            return True

    return True


class AgentHeartbeatLoop:
    """Runs inside each agent process as asyncio background tasks.

    Responsibilities:
    - Fetch schedules from PACO for this agent
    - Run heartbeat checks on schedule through agent's LangGraph
    - Report results back to PACO
    - Poll inbox for peer messages
    """

    def __init__(
        self,
        agent_slug: str,
        paco_api_url: str,
        infrastructure_id: str,
        agent_graph: Any,
    ):
        self.slug = agent_slug
        self.paco_url = paco_api_url.rstrip("/")
        self.infra_id = infrastructure_id
        self.graph = agent_graph
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._schedules: list[dict] = []
        self._config: dict = {}

    async def start(self):
        """Fetch schedules from PACO and start background loops."""
        self._running = True
        try:
            self._schedules = await self._fetch_schedules()
            self._config = await self._fetch_config()
        except Exception as e:
            logger.warning("Failed to fetch schedules from PACO: %s", e)
            self._schedules = []
            self._config = {}

        if self._schedules:
            for schedule in self._schedules:
                task = asyncio.create_task(
                    self._schedule_loop(schedule),
                    name=f"heartbeat:{self.slug}:{schedule.get('name', 'unknown')}",
                )
                self._tasks.append(task)
            logger.info(
                "AgentHeartbeatLoop started for %s with %d schedule(s)",
                self.slug,
                len(self._schedules),
            )
        else:
            logger.info("AgentHeartbeatLoop: no schedules for %s", self.slug)

        # Always start inbox polling
        inbox_task = asyncio.create_task(
            self._inbox_loop(),
            name=f"inbox:{self.slug}",
        )
        self._tasks.append(inbox_task)

    async def stop(self):
        """Cancel all background tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        logger.info("AgentHeartbeatLoop stopped for %s", self.slug)

    # ------------------------------------------------------------------
    # Schedule loop
    # ------------------------------------------------------------------

    async def _schedule_loop(self, schedule: dict):
        """One loop per schedule. Sleeps until next trigger, then executes."""
        while self._running:
            try:
                next_at = _compute_next_trigger(schedule)
                sleep_seconds = (next_at - datetime.now(timezone.utc)).total_seconds()
                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)

                if not self._running:
                    break

                if not _is_within_active_hours(schedule, self._config):
                    logger.debug(
                        "Schedule %s/%s: outside active hours, skipping",
                        self.slug,
                        schedule.get("name"),
                    )
                    continue

                result = await self._execute(schedule)
                await self._report_task(schedule, result)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Schedule loop error for %s/%s: %s",
                    self.slug,
                    schedule.get("name"),
                    e,
                    exc_info=True,
                )
                # Back off on error
                await asyncio.sleep(60)

    async def _execute(self, schedule: dict) -> dict:
        """Run heartbeat check through agent's LangGraph."""
        prompt = self._build_prompt(schedule)
        state = {"messages": [HumanMessage(content=prompt)]}

        start = datetime.now(timezone.utc)
        try:
            result = await self.graph.ainvoke(state)
            response_text = result["messages"][-1].content
            is_ok = "HEARTBEAT_OK" in response_text.upper()
            duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            return {
                "response": response_text,
                "heartbeat_ok": is_ok,
                "duration_ms": duration_ms,
                "status": "heartbeat_ok" if is_ok else "completed",
            }
        except Exception as e:
            duration_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            return {
                "response": "",
                "heartbeat_ok": False,
                "duration_ms": duration_ms,
                "status": "failed",
                "error": str(e)[:1000],
            }

    def _build_prompt(self, schedule: dict) -> str:
        """Build heartbeat prompt from schedule checklist + template."""
        parts = []
        if schedule.get("checklist_md"):
            parts.append(schedule["checklist_md"])
        if schedule.get("prompt_template"):
            parts.append(schedule["prompt_template"])
        if not parts:
            parts.append(
                "Perform your routine check. Reply HEARTBEAT_OK if nothing needs attention."
            )
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def _report_task(self, schedule: dict, result: dict):
        """POST task result to PACO backend."""
        payload = {
            "schedule_id": schedule.get("id"),
            "agent_slug": self.slug,
            "title": f"{schedule.get('name', 'heartbeat')} - {schedule.get('schedule_type', 'heartbeat')}",
            "task_type": (
                "heartbeat_check"
                if schedule.get("schedule_type") == "heartbeat"
                else "scheduled_job"
            ),
            "status": result["status"],
            "result": {"response": result["response"], "heartbeat_ok": result["heartbeat_ok"]},
            "duration_ms": result.get("duration_ms"),
            "error_message": result.get("error"),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.paco_url}/api/infrastructures/{self.infra_id}/company/tasks/report",
                    json=payload,
                )
                if resp.status_code not in (200, 201):
                    logger.warning(
                        "Task report failed for %s: HTTP %d", self.slug, resp.status_code
                    )
        except Exception as e:
            logger.warning("Failed to report task for %s: %s", self.slug, e)

    # ------------------------------------------------------------------
    # Inbox polling
    # ------------------------------------------------------------------

    async def _inbox_loop(self):
        """Poll inbox every 30 seconds for peer messages."""
        while self._running:
            try:
                messages = await self._fetch_inbox()
                for msg in messages:
                    await self._process_message(msg)
                    await self._mark_read(msg["id"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug("Inbox poll error for %s: %s", self.slug, e)
            await asyncio.sleep(30)

    async def _process_message(self, msg: dict):
        """Process a peer message through agent's LangGraph."""
        sender = msg.get("sender_slug", "unknown")
        content = msg.get("content", "")
        subject = msg.get("subject", "")
        msg_type = msg.get("message_type", "direct")

        prompt = f"[Company Message from {sender}]"
        if subject:
            prompt += f" Subject: {subject}"
        prompt += f"\nType: {msg_type}\n\n{content}"

        try:
            state = {"messages": [HumanMessage(content=prompt)]}
            result = await self.graph.ainvoke(state)
            response_text = result["messages"][-1].content

            # If message expects a reply, send it back
            if msg_type in ("task_request", "direct"):
                await self._send_reply(msg, response_text)

            logger.info(
                "Processed message from %s → %s (%s)", sender, self.slug, msg_type
            )
        except Exception as e:
            logger.error("Failed to process message for %s: %s", self.slug, e)

    async def _send_reply(self, original_msg: dict, response_text: str):
        """Send reply back via PACO messaging API."""
        payload = {
            "sender_slug": self.slug,
            "recipient_slug": original_msg.get("sender_slug"),
            "message_type": "task_result" if original_msg.get("message_type") == "task_request" else "direct",
            "subject": f"Re: {original_msg.get('subject', '')}",
            "content": response_text,
            "parent_message_id": original_msg.get("id"),
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.paco_url}/api/infrastructures/{self.infra_id}/company/messages",
                    json=payload,
                )
        except Exception as e:
            logger.warning("Failed to send reply from %s: %s", self.slug, e)

    async def _mark_read(self, message_id: str):
        """Mark a message as read via PACO API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.put(
                    f"{self.paco_url}/api/infrastructures/{self.infra_id}/company/messages/{message_id}/read",
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # PACO API calls
    # ------------------------------------------------------------------

    async def _fetch_schedules(self) -> list[dict]:
        """Fetch this agent's schedules from PACO."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.paco_url}/api/infrastructures/{self.infra_id}/company/schedules",
                params={"agent_slug": self.slug},
            )
            if resp.status_code == 200:
                return resp.json()
            return []

    async def _fetch_config(self) -> dict:
        """Fetch company config defaults from PACO."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.paco_url}/api/infrastructures/{self.infra_id}/company/config",
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return {}

    async def _fetch_inbox(self) -> list[dict]:
        """Fetch unread messages from PACO inbox."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.paco_url}/api/infrastructures/{self.infra_id}/company/messages/inbox/{self.slug}",
            )
            if resp.status_code == 200:
                return resp.json()
            return []
