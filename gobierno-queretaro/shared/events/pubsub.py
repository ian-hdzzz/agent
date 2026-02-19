"""
Gobierno Querétaro - Event Pub/Sub System
Redis-based event messaging for inter-agent communication
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Coroutine
from uuid import UUID, uuid4

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EventBus:
    """
    Redis-based event bus for agent communication.

    Supports:
    - Publishing events to channels
    - Subscribing to event patterns
    - Event persistence for audit
    """

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._subscriptions: dict[str, list[Callable]] = {}
        self._running = False

    async def connect(self) -> None:
        """Connect to Redis"""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Connected to Redis: {self.redis_url}")

    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None

        if self._redis:
            await self._redis.close()
            self._redis = None

        self._running = False
        logger.info("Disconnected from Redis")

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any],
        source_agent: str | None = None,
        target_agent: str | None = None,
        conversation_id: str | UUID | None = None,
    ) -> str:
        """
        Publish an event to the bus.

        Args:
            event_type: Type of event (e.g., 'agent.handoff', 'task.completed')
            payload: Event data
            source_agent: ID of agent publishing the event
            target_agent: ID of target agent (optional)
            conversation_id: Related conversation ID (optional)

        Returns:
            Event ID
        """
        await self.connect()

        event_id = str(uuid4())
        event = {
            "id": event_id,
            "type": event_type,
            "source_agent": source_agent,
            "target_agent": target_agent,
            "conversation_id": str(conversation_id) if conversation_id else None,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Publish to channel
        channel = f"gobierno:events:{event_type}"
        await self._redis.publish(channel, json.dumps(event))

        # Also store in stream for persistence/replay
        await self._redis.xadd(
            "gobierno:events:stream",
            {"data": json.dumps(event)},
            maxlen=10000,  # Keep last 10k events
        )

        logger.debug(f"Published event {event_id} to {channel}")
        return event_id

    async def subscribe(
        self,
        pattern: str,
        handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """
        Subscribe to events matching a pattern.

        Args:
            pattern: Event type pattern (e.g., 'agent.*', 'task.completed')
            handler: Async function to handle events
        """
        await self.connect()

        if self._pubsub is None:
            self._pubsub = self._redis.pubsub()

        channel_pattern = f"gobierno:events:{pattern}"

        if pattern not in self._subscriptions:
            self._subscriptions[pattern] = []
            await self._pubsub.psubscribe(channel_pattern)
            logger.info(f"Subscribed to pattern: {channel_pattern}")

        self._subscriptions[pattern].append(handler)

    async def start_listening(self) -> None:
        """Start listening for events"""
        if self._pubsub is None:
            logger.warning("No subscriptions, cannot start listening")
            return

        self._running = True
        logger.info("Started listening for events")

        async for message in self._pubsub.listen():
            if not self._running:
                break

            if message["type"] == "pmessage":
                try:
                    pattern = message["pattern"].decode() if isinstance(message["pattern"], bytes) else message["pattern"]
                    # Extract pattern from channel name
                    pattern = pattern.replace("gobierno:events:", "")
                    data = json.loads(message["data"])

                    # Call all handlers for this pattern
                    for handler in self._subscriptions.get(pattern, []):
                        try:
                            await handler(data)
                        except Exception as e:
                            logger.error(f"Handler error for {pattern}: {e}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse event: {e}")

    def stop_listening(self) -> None:
        """Stop listening for events"""
        self._running = False


# ============================================
# Event Types
# ============================================

class EventTypes:
    """Standard event types"""

    # Agent events
    AGENT_HANDOFF = "agent.handoff"
    AGENT_RESPONSE = "agent.response"
    AGENT_ERROR = "agent.error"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    SUBTASK_COMPLETED = "task.subtask_completed"

    # Conversation events
    CONVERSATION_STARTED = "conversation.started"
    CONVERSATION_ENDED = "conversation.ended"
    MESSAGE_RECEIVED = "conversation.message_received"

    # Ticket events
    TICKET_CREATED = "ticket.created"
    TICKET_UPDATED = "ticket.updated"
    TICKET_RESOLVED = "ticket.resolved"

    # System events
    HUMAN_HANDOFF = "system.human_handoff"
    ESCALATION = "system.escalation"


# ============================================
# Helper Functions
# ============================================

async def publish_handoff(
    event_bus: EventBus,
    source_agent: str,
    target_agent: str,
    conversation_id: str,
    reason: str,
    context: dict[str, Any] | None = None,
) -> str:
    """Publish agent handoff event"""
    return await event_bus.publish(
        EventTypes.AGENT_HANDOFF,
        {
            "reason": reason,
            "context": context or {},
        },
        source_agent=source_agent,
        target_agent=target_agent,
        conversation_id=conversation_id,
    )


async def publish_task_completed(
    event_bus: EventBus,
    agent_id: str,
    task_id: str,
    task_type: str,
    result: dict[str, Any],
    conversation_id: str | None = None,
) -> str:
    """Publish task completion event"""
    return await event_bus.publish(
        EventTypes.TASK_COMPLETED,
        {
            "task_id": task_id,
            "task_type": task_type,
            "result": result,
        },
        source_agent=agent_id,
        conversation_id=conversation_id,
    )


async def publish_ticket_created(
    event_bus: EventBus,
    agent_id: str,
    ticket_folio: str,
    category: str,
    title: str,
    conversation_id: str | None = None,
) -> str:
    """Publish ticket creation event"""
    return await event_bus.publish(
        EventTypes.TICKET_CREATED,
        {
            "folio": ticket_folio,
            "category": category,
            "title": title,
        },
        source_agent=agent_id,
        conversation_id=conversation_id,
    )


# ============================================
# Singleton Event Bus
# ============================================

_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the singleton event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
