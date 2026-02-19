"""
Gobierno Querétaro - Automatic Reward Heuristics
Derives reward signals from conversation patterns without human labeling.

These heuristics provide training signal from day 1 for agent-lightning
APO and RL training phases.

Reward signals:
    +0.8  Citizen said "gracias" after answer → Satisfied
    +0.5  Conversation ended in <3 turns → Efficient resolution
    -0.5  Agent was re-routed mid-conversation → Likely misclassification
    -0.7  Citizen asked to speak to human → Agent couldn't help
    -0.6  Citizen repeated same question → Agent response unclear
    -0.3  Fallback agent triggered → Primary agent unavailable or misrouted
"""

import logging
import re

try:
    from agentlightning.agent import emit_reward
except (ImportError, ModuleNotFoundError):
    emit_reward = None

logger = logging.getLogger(__name__)

# Patterns for detecting satisfaction signals in Spanish
GRATITUDE_PATTERNS = [
    r"\bgracias\b", r"\bmuchas gracias\b", r"\bperfecto\b",
    r"\bexcelente\b", r"\bgenial\b", r"\bmuy bien\b",
    r"\bme ayudaste\b", r"\bme sirvió\b",
]

# Patterns for detecting frustration / escalation signals
ESCALATION_PATTERNS = [
    r"\bhablar con (una |un )?persona\b",
    r"\bagente humano\b",
    r"\bpersona real\b",
    r"\bquiero hablar\b",
    r"\boperador\b",
    r"\bsupervisor\b",
    r"\bno me (ayudas?|sirves?|entiendes?)\b",
]

# Patterns for detecting repetition / confusion
REPETITION_INDICATORS = [
    r"\bya te (dije|pregunté)\b",
    r"\brepito\b",
    r"\botra vez\b",
    r"\bno entendiste\b",
    r"\beso no es lo que (te )?pregunt[eé]\b",
    r"\bte estoy diciendo\b",
]


class AutoRewardEvaluator:
    """
    Evaluates conversation events and emits reward signals automatically.

    Used by the orchestrator to generate training data from production traffic
    without requiring manual labeling.
    """

    def evaluate_citizen_message(
        self,
        message: str,
        conversation_id: str | None = None,
        turn_count: int = 0,
    ) -> float | None:
        """
        Evaluate a citizen message for automatic reward signals.

        Args:
            message: The citizen's message text
            conversation_id: Conversation identifier for tracking
            turn_count: Number of turns in the conversation so far

        Returns:
            Reward value if a signal was detected, None otherwise
        """
        lower_message = message.lower().strip()
        reward = None

        # Check for gratitude (positive signal)
        if any(re.search(p, lower_message) for p in GRATITUDE_PATTERNS):
            reward = 0.8
            self._emit(reward, "gratitude", conversation_id)

        # Check for escalation request (negative signal)
        elif any(re.search(p, lower_message) for p in ESCALATION_PATTERNS):
            reward = -0.7
            self._emit(reward, "escalation_request", conversation_id)

        # Check for repetition / frustration (negative signal)
        elif any(re.search(p, lower_message) for p in REPETITION_INDICATORS):
            reward = -0.6
            self._emit(reward, "repetition_detected", conversation_id)

        return reward

    def evaluate_routing_event(
        self,
        event_type: str,
        conversation_id: str | None = None,
        metadata: dict | None = None,
    ) -> float:
        """
        Evaluate a routing event for automatic reward signals.

        Args:
            event_type: Type of routing event
            conversation_id: Conversation identifier
            metadata: Additional context about the event

        Returns:
            Reward value
        """
        metadata = metadata or {}

        reward_map = {
            "fallback_triggered": -0.3,
            "rerouted_mid_conversation": -0.5,
            "efficient_resolution": 0.5,  # <3 turns
            "agent_success": 0.3,
        }

        reward = reward_map.get(event_type, 0.0)
        self._emit(reward, event_type, conversation_id, metadata)
        return reward

    def evaluate_conversation_end(
        self,
        turn_count: int,
        had_fallback: bool = False,
        had_reroute: bool = False,
        conversation_id: str | None = None,
    ) -> float:
        """
        Evaluate the overall conversation quality at conversation end.

        Args:
            turn_count: Total number of turns in the conversation
            had_fallback: Whether a fallback agent was used
            had_reroute: Whether the conversation was re-routed
            conversation_id: Conversation identifier

        Returns:
            Aggregate reward value
        """
        reward = 0.0

        # Efficient resolution bonus
        if turn_count <= 3 and not had_fallback:
            reward += 0.5

        # Penalties
        if had_fallback:
            reward -= 0.3
        if had_reroute:
            reward -= 0.5

        if reward != 0.0:
            self._emit(reward, "conversation_end", conversation_id, {
                "turn_count": turn_count,
                "had_fallback": had_fallback,
                "had_reroute": had_reroute,
            })

        return reward

    def _emit(
        self,
        reward: float,
        signal_type: str,
        conversation_id: str | None = None,
        metadata: dict | None = None,
    ):
        """Emit a reward signal via agent-lightning."""
        attributes = {
            "reward.signal_type": signal_type,
            "reward.source": "auto_heuristic",
        }
        if conversation_id:
            attributes["conversation_id"] = conversation_id
        if metadata:
            for k, v in metadata.items():
                attributes[f"reward.{k}"] = str(v)

        try:
            if emit_reward is None:
                logger.debug(
                    f"Auto-reward skipped (agentlightning not available): "
                    f"{signal_type}={reward:.2f}"
                )
                return
            emit_reward(reward, attributes=attributes)
            logger.debug(
                f"Auto-reward emitted: {signal_type}={reward:.2f} "
                f"(conversation={conversation_id})"
            )
        except Exception as e:
            # Tracing failures should never break the main flow
            logger.warning(f"Failed to emit auto-reward: {e}")


# Singleton instance
_evaluator: AutoRewardEvaluator | None = None


def get_reward_evaluator() -> AutoRewardEvaluator:
    """Get or create the singleton reward evaluator."""
    global _evaluator
    if _evaluator is None:
        _evaluator = AutoRewardEvaluator()
    return _evaluator
