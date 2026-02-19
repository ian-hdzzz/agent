"""
Gobierno Querétaro - LangGraph Orchestrator Router
Routes requests to appropriate specialist agents with resilient HTTP and circuit breaker
"""

import logging
import operator
from typing import Annotated, Any, Literal, TypedDict

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from tenacity import RetryError

from agentlightning import emit_annotation, emit_message, emit_reward, operation

from .classifier import (
    CategoryCode,
    classify_intent,
    extract_contract_number,
    get_category_description,
    is_ambiguous_message,
)
from .config import get_agent_registry, get_settings
from shared.utils.http_client import (
    ResilientHTTPClient,
    CircuitOpenError,
    get_resilient_client,
    get_circuit_breaker,
)
from shared.security.audit import AuditEventType, get_audit_logger
from shared.tracing.auto_rewards import get_reward_evaluator

logger = logging.getLogger(__name__)
settings = get_settings()

# Fallback agent ID for when primary agent is unavailable
FALLBACK_AGENT_CATEGORY = "ATC"  # citizen-attention


# ============================================
# Orchestrator State
# ============================================

class OrchestratorState(TypedDict):
    """
    State for the orchestrator graph.

    Attributes:
        messages: Conversation history
        detected_category: Classified category code
        agent_response: Response from specialist agent
        agent_id: ID of agent that handled request
        contract_number: Extracted contract number
        task_type: Task type from specialist agent (for context continuity)
        metadata: Additional context
        error: Error message if any
    """

    messages: Annotated[list[BaseMessage], operator.add]
    detected_category: CategoryCode | None
    agent_response: str | None
    agent_id: str | None
    contract_number: str | None
    task_type: str | None
    metadata: dict[str, Any]
    error: str | None


# ============================================
# Node Functions
# ============================================

async def classify_intent_node(state: OrchestratorState) -> dict[str, Any]:
    """
    Classify user message into one of 13 categories.

    This node analyzes the latest user message and determines
    which specialist agent should handle the request.

    Context-aware routing: If the message is ambiguous (short/vague) and
    we have a recent agent context from the session, continue with that
    agent instead of re-classifying.
    """
    messages = state.get("messages", [])
    metadata = state.get("metadata", {})

    if not messages:
        return {"detected_category": "ATC", "error": "No message provided"}

    # Get last user message
    last_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    if not last_message:
        return {"detected_category": "ATC", "error": "No user message found"}

    with operation(name="orchestrator.classify"):
        # Emit the incoming message for tracing
        try:
            emit_message(last_message, attributes={"message.role": "user"})
        except Exception:
            pass  # Tracing failures must never break the main flow

        # Check for context continuity - if message is ambiguous and we have
        # a recent agent context, stay with that agent
        last_category = metadata.get("last_category")

        if last_category and is_ambiguous_message(last_message):
            logger.info(
                f"Ambiguous message '{last_message}', continuing with {last_category}"
            )
            try:
                emit_annotation({
                    "classification.category": last_category,
                    "classification.method": "context_continuity",
                    "classification.ambiguous": True,
                })
            except Exception:
                pass
            return {
                "detected_category": last_category,
                "contract_number": state.get("contract_number"),
            }

        # Build context from conversation history
        context_messages = []
        for msg in messages[-6:]:  # Last 6 messages for context
            role = "Usuario" if isinstance(msg, HumanMessage) else "Asistente"
            context_messages.append(f"{role}: {msg.content}")
        context = "\n".join(context_messages)

        # Classify intent
        result = await classify_intent(last_message, context)

        # Extract contract number
        contract_number = extract_contract_number(last_message)

        # Emit classification result as annotation for tracing
        try:
            emit_annotation({
                "classification.category": result["category"],
                "classification.confidence": str(result.get("confidence", 0)),
                "classification.method": result.get("method", "unknown"),
            })
        except Exception:
            pass

        logger.info(
            f"Classified: category={result['category']}, "
            f"confidence={result.get('confidence', 0):.2f}, "
            f"method={result.get('method', 'unknown')}"
        )

        return {
            "detected_category": result["category"],
            "contract_number": contract_number or state.get("contract_number"),
        }


def route_to_agent(state: OrchestratorState) -> str:
    """
    Route to appropriate specialist agent based on category.

    Returns the name of the next node to execute.
    """
    category = state.get("detected_category", "ATC")

    # Handle EXIT specially
    if category == "EXIT":
        return "handle_exit"

    # Route to agent caller
    return "call_agent"


async def call_fallback_agent(
    state: OrchestratorState,
    original_agent_id: str,
    fallback_reason: str,
) -> dict[str, Any]:
    """
    Call the fallback agent (citizen-attention) when primary agent fails.

    Args:
        state: Current orchestrator state
        original_agent_id: ID of the agent that failed
        fallback_reason: Reason for fallback (for logging)

    Returns:
        Agent response dict
    """
    # Emit auto-reward for fallback event
    try:
        reward_eval = get_reward_evaluator()
        reward_eval.evaluate_routing_event(
            "fallback_triggered",
            conversation_id=state.get("metadata", {}).get("conversation_id"),
            metadata={"original_agent": original_agent_id, "reason": fallback_reason},
        )
    except Exception:
        pass

    registry = get_agent_registry()
    fallback_info = registry[FALLBACK_AGENT_CATEGORY]
    fallback_url = fallback_info["url"]
    fallback_id = fallback_info["id"]

    # Get last user message
    messages = state.get("messages", [])
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    logger.warning(
        f"Falling back to {fallback_id} from {original_agent_id}: {fallback_reason}"
    )

    # Log the fallback
    audit = get_audit_logger()
    await audit.log_agent_call(
        agent_id=fallback_id,
        action=f"Fallback from {original_agent_id}",
        conversation_id=state.get("metadata", {}).get("conversation_id"),
        details={
            "original_agent": original_agent_id,
            "fallback_reason": fallback_reason,
        },
    )

    try:
        client = get_resilient_client(timeout=settings.agent_timeout)
        response = await client.post(
            f"{fallback_url}/query",
            json={
                "message": last_message,
                "conversation_id": state.get("metadata", {}).get("conversation_id"),
                "contact_id": state.get("metadata", {}).get("contact_id"),
                "metadata": {
                    "contract_number": state.get("contract_number"),
                    "category": FALLBACK_AGENT_CATEGORY,
                    "original_category": state.get("detected_category"),
                    "is_fallback": True,
                    "fallback_reason": fallback_reason,
                    **state.get("metadata", {}),
                },
            },
            service_id=fallback_id,
        )

        data = response.json()
        agent_response = data.get("response", "")

        return {
            "agent_response": agent_response,
            "agent_id": fallback_id,
            "messages": [AIMessage(content=agent_response)],
        }

    except Exception as e:
        # Even fallback failed
        logger.error(f"Fallback agent {fallback_id} also failed: {e}")
        return {
            "error": f"Both primary and fallback agents failed: {str(e)}",
            "agent_id": fallback_id,
        }


async def call_agent(state: OrchestratorState) -> dict[str, Any]:
    """
    Call the specialist agent via HTTP with retry and circuit breaker.

    Features:
    - Automatic retries with exponential backoff
    - Circuit breaker to prevent cascading failures
    - Fallback to citizen-attention agent when primary fails
    """
    category = state.get("detected_category", "ATC")
    registry = get_agent_registry()

    agent_info = registry.get(category, registry["ATC"])
    agent_url = agent_info["url"]
    agent_id = agent_info["id"]

    # Get last user message
    messages = state.get("messages", [])
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    logger.info(f"Calling agent {agent_id} at {agent_url}")

    # Get resilient HTTP client with shared circuit breaker
    client = get_resilient_client(timeout=settings.agent_timeout)

    # Check if agent is available (circuit not open)
    if not client.is_service_available(agent_id):
        logger.warning(f"Circuit open for {agent_id}, using fallback")
        return await call_fallback_agent(
            state,
            original_agent_id=agent_id,
            fallback_reason="Circuit breaker open",
        )

    # Build conversation history (excluding last message which is sent separately)
    conversation_history = []
    for msg in messages[:-1]:
        if isinstance(msg, HumanMessage):
            conversation_history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            conversation_history.append({"role": "assistant", "content": msg.content})

    try:
        response = await client.post(
            f"{agent_url}/query",
            json={
                "message": last_message,
                "conversation_id": state.get("metadata", {}).get("conversation_id"),
                "contact_id": state.get("metadata", {}).get("contact_id"),
                "conversation_history": conversation_history,
                "metadata": {
                    "contract_number": state.get("contract_number"),
                    "category": category,
                    **state.get("metadata", {}),
                },
            },
            service_id=agent_id,
        )

        if response.status_code == 200:
            data = response.json()
            agent_response = data.get("response", "")

            logger.info(f"Agent {agent_id} responded successfully")

            # Log successful call
            audit = get_audit_logger()
            await audit.log_agent_call(
                agent_id=agent_id,
                action=f"Agent {agent_id} processed message",
                conversation_id=state.get("metadata", {}).get("conversation_id"),
                success=True,
            )

            return {
                "agent_response": agent_response,
                "agent_id": agent_id,
                "task_type": data.get("task_type"),
                "messages": [AIMessage(content=agent_response)],
            }
        else:
            error_msg = f"Agent returned status {response.status_code}"
            logger.error(f"Agent {agent_id} error: {error_msg}")

            # Fallback on 5xx errors
            if response.status_code >= 500:
                return await call_fallback_agent(
                    state,
                    original_agent_id=agent_id,
                    fallback_reason=error_msg,
                )

            return {
                "error": error_msg,
                "agent_id": agent_id,
            }

    except CircuitOpenError:
        logger.warning(f"Circuit opened during request to {agent_id}")
        return await call_fallback_agent(
            state,
            original_agent_id=agent_id,
            fallback_reason="Circuit opened during request",
        )

    except RetryError as e:
        logger.error(f"All retries exhausted for {agent_id}")
        return await call_fallback_agent(
            state,
            original_agent_id=agent_id,
            fallback_reason=f"All retries exhausted: {str(e)}",
        )

    except httpx.TimeoutException:
        error_msg = f"Agent {agent_id} timed out after retries"
        logger.error(error_msg)
        return await call_fallback_agent(
            state,
            original_agent_id=agent_id,
            fallback_reason=error_msg,
        )

    except Exception as e:
        error_msg = f"Agent {agent_id} error: {str(e)}"
        logger.error(error_msg)
        return await call_fallback_agent(
            state,
            original_agent_id=agent_id,
            fallback_reason=error_msg,
        )


def handle_exit(state: OrchestratorState) -> dict[str, Any]:
    """Handle conversation exit"""
    farewell = "¡Gracias por usar el Portal de Gobierno de Querétaro! Que tengas un excelente día."

    return {
        "agent_response": farewell,
        "agent_id": "orchestrator",
        "messages": [AIMessage(content=farewell)],
    }


def handle_error(state: OrchestratorState) -> dict[str, Any]:
    """Handle errors gracefully"""
    error = state.get("error")

    if error:
        response = (
            "Lo siento, tuve un problema conectando con el servicio. "
            "Por favor intenta de nuevo en unos momentos."
        )
    else:
        response = (
            "Lo siento, no pude procesar tu solicitud. "
            "¿Podrías reformular tu pregunta?"
        )

    return {
        "agent_response": response,
        "messages": [AIMessage(content=response)],
    }


def should_handle_error(state: OrchestratorState) -> str:
    """Check if we need to handle an error"""
    if state.get("error"):
        return "handle_error"
    return "end"


# ============================================
# Build the Graph
# ============================================

def build_orchestrator_graph() -> StateGraph:
    """
    Build the LangGraph orchestrator graph.

    Graph structure:
    1. classify -> determine category
    2. route -> select agent or handle exit
    3. call_agent -> make HTTP request to agent
    4. handle_error (if needed) -> graceful error handling
    5. end
    """
    graph = StateGraph(OrchestratorState)

    # Add nodes
    graph.add_node("classify", classify_intent_node)
    graph.add_node("call_agent", call_agent)
    graph.add_node("handle_exit", handle_exit)
    graph.add_node("handle_error", handle_error)

    # Set entry point
    graph.set_entry_point("classify")

    # Add routing from classify
    graph.add_conditional_edges(
        "classify",
        route_to_agent,
        {
            "call_agent": "call_agent",
            "handle_exit": "handle_exit",
        },
    )

    # Add error handling after agent call
    graph.add_conditional_edges(
        "call_agent",
        should_handle_error,
        {
            "handle_error": "handle_error",
            "end": END,
        },
    )

    # Exit and error handling go to END
    graph.add_edge("handle_exit", END)
    graph.add_edge("handle_error", END)

    return graph


# ============================================
# Orchestrator Runner
# ============================================

class Orchestrator:
    """
    Wrapper class for the LangGraph orchestrator.

    Provides a simple interface for routing requests
    to specialist agents.
    """

    def __init__(self):
        self.graph = build_orchestrator_graph()
        self.app = self.graph.compile()

    async def route(
        self,
        message: str,
        conversation_history: list[BaseMessage] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Route a user message to the appropriate specialist agent.

        Args:
            message: User's message
            conversation_history: Previous messages (optional)
            metadata: Additional context (optional)

        Returns:
            Orchestrator response with agent_response and routing info
        """
        # Build initial state
        messages = list(conversation_history or [])
        messages.append(HumanMessage(content=message))

        initial_state: OrchestratorState = {
            "messages": messages,
            "detected_category": None,
            "agent_response": None,
            "agent_id": None,
            "contract_number": metadata.get("contract_number") if metadata else None,
            "task_type": None,
            "metadata": metadata or {},
            "error": None,
        }

        conversation_id = (metadata or {}).get("conversation_id")

        with operation(name="orchestrator.route"):
            try:
                # Emit incoming user message
                try:
                    emit_message(message, attributes={"message.role": "user"})
                except Exception:
                    pass

                # Evaluate citizen message for auto-rewards
                try:
                    reward_eval = get_reward_evaluator()
                    reward_eval.evaluate_citizen_message(
                        message, conversation_id=conversation_id
                    )
                except Exception:
                    pass

                result = await self.app.ainvoke(initial_state)

                # Emit agent response
                agent_response = result.get("agent_response", "")
                try:
                    emit_message(
                        agent_response,
                        attributes={"message.role": "assistant"},
                    )
                    emit_annotation({
                        "route.category": result.get("detected_category", ""),
                        "route.agent_id": result.get("agent_id", ""),
                        "route.task_type": result.get("task_type", ""),
                    })
                except Exception:
                    pass

                return {
                    "response": agent_response,
                    "category": result.get("detected_category"),
                    "category_description": get_category_description(
                        result.get("detected_category", "ATC")
                    ),
                    "agent_id": result.get("agent_id"),
                    "contract_number": result.get("contract_number"),
                    "task_type": result.get("task_type"),
                    "error": result.get("error"),
                }

            except Exception as e:
                logger.error(f"Orchestrator error: {e}")
                return {
                    "response": "Lo siento, tuve un problema procesando tu solicitud.",
                    "category": "ATC",
                    "error": str(e),
                }

    def get_health(self) -> dict[str, Any]:
        """Get orchestrator health status"""
        registry = get_agent_registry()
        circuit_breaker = get_circuit_breaker()

        # Get circuit status for each agent
        agent_status = {}
        for category, info in registry.items():
            agent_id = info["id"]
            agent_status[agent_id] = {
                **circuit_breaker.get_stats(agent_id),
                "version": info.get("version", "unknown"),
                "sla_tier": info.get("sla_tier", "standard"),
            }

        return {
            "status": "healthy",
            "service": "orchestrator",
            "agents": list(registry.keys()),
            "agent_count": len(registry),
            "circuit_status": agent_status,
        }


# Singleton orchestrator instance
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get or create the singleton orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
