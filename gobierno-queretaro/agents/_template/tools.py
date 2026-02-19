"""
Gobierno Querétaro - Agent Tools Template
Define domain-specific tools for the agent

Each specialized agent should override this file with
their own tools relevant to their domain.
"""

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# ============================================
# Generic Tools (Available to all agents)
# ============================================

@tool
def create_ticket(
    title: str,
    description: str,
    category: str,
    priority: str = "medium",
    contact_name: str | None = None,
    contact_phone: str | None = None,
    contact_email: str | None = None,
) -> dict[str, Any]:
    """
    Create a new government service ticket.

    Args:
        title: Brief title of the request
        description: Detailed description of the issue
        category: Category code (e.g., CEA, TRA, EDU)
        priority: Priority level (low, medium, high, urgent)
        contact_name: Contact person's name
        contact_phone: Contact phone number
        contact_email: Contact email address

    Returns:
        Ticket information including folio number
    """
    # This is a placeholder - implement actual ticket creation
    import uuid
    from datetime import datetime

    folio = f"{category}-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

    logger.info(f"Created ticket: {folio}")

    return {
        "success": True,
        "folio": folio,
        "title": title,
        "category": category,
        "priority": priority,
        "status": "open",
        "message": f"Tu solicitud ha sido registrada con el folio {folio}.",
        "formatted_response": f"""✅ *Ticket Creado*

📋 *Folio:* {folio}
📝 *Asunto:* {title}
⚡ *Prioridad:* {priority}
📊 *Estado:* Abierto

Recibirás seguimiento a tu solicitud.""",
    }


@tool
def get_ticket_status(folio: str) -> dict[str, Any]:
    """
    Check the status of an existing ticket.

    Args:
        folio: Ticket folio number

    Returns:
        Ticket status information
    """
    # This is a placeholder - implement actual status lookup
    logger.info(f"Checking status for ticket: {folio}")

    return {
        "success": True,
        "folio": folio,
        "status": "in_progress",
        "last_update": "2024-01-15",
        "formatted_response": f"""📋 *Estado del Ticket*

🔖 *Folio:* {folio}
📊 *Estado:* En proceso
📅 *Última actualización:* Hoy

Tu solicitud está siendo atendida por nuestro equipo.""",
    }


@tool
def handoff_to_human(reason: str) -> dict[str, Any]:
    """
    Transfer the conversation to a human agent.

    Args:
        reason: Reason for the handoff

    Returns:
        Handoff confirmation
    """
    logger.info(f"Handoff to human requested: {reason}")

    return {
        "success": True,
        "reason": reason,
        "formatted_response": """👤 *Transferencia a Asesor*

Te estoy transfiriendo con un asesor humano.

Por favor espera un momento, alguien te atenderá pronto.""",
    }


@tool
def request_handoff(
    target_agent_id: str,
    reason: str,
    context_summary: str,
    extracted_entities: str | None = None,
) -> dict[str, Any]:
    """
    Request handoff to another specialist agent.

    Use this when a citizen's request involves a different department.
    For example, if someone asks about housing subsidies for women,
    hand off to women-iqm or housing-iveq as appropriate.

    Args:
        target_agent_id: ID of the agent to hand off to (e.g., 'women-iqm', 'vehicles', 'water-cea')
        reason: Why the handoff is needed
        context_summary: Brief summary of the conversation so far
        extracted_entities: Key entities extracted (e.g., contract numbers, names)

    Returns:
        Handoff request result
    """
    logger.info(f"Agent handoff requested to {target_agent_id}: {reason}")

    return {
        "success": True,
        "handoff_requested": True,
        "target_agent_id": target_agent_id,
        "reason": reason,
        "context_summary": context_summary,
        "extracted_entities": extracted_entities,
        "formatted_response": f"Te voy a transferir con el área especializada para atenderte mejor.",
    }


# ============================================
# Tool Registry
# ============================================

def get_tools() -> list:
    """
    Get all available tools for this agent.

    Override this function in specialized agents
    to return domain-specific tools.
    """
    return [
        create_ticket,
        get_ticket_status,
        handoff_to_human,
        request_handoff,
    ]
