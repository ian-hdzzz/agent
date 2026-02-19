"""
Gobierno Querétaro - Human Feedback Collection
Endpoint for collecting reward signals from Chatwoot agents and citizens.

Sources of feedback:
- Chatwoot agent ratings (was routing correct? was response helpful?)
- Citizen satisfaction (thumbs up/down on WhatsApp)
- Automatic signals (processed via auto_rewards module)
"""

import logging
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agentlightning.agent import emit_reward

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedbackRequest(BaseModel):
    """Request model for submitting feedback on an interaction."""

    conversation_id: str = Field(description="Chatwoot conversation ID")
    score: float = Field(
        ge=-1.0, le=1.0,
        description="Feedback score from -1.0 (terrible) to 1.0 (excellent)",
    )
    feedback_type: Literal[
        "routing_accuracy",
        "response_quality",
        "resolution_speed",
        "overall_satisfaction",
    ] = Field(description="What aspect of the interaction is being rated")
    category: str | None = Field(
        default=None,
        description="Category code of the agent that handled the request",
    )
    agent_id: str | None = Field(
        default=None,
        description="ID of the agent that handled the request",
    )
    comment: str | None = Field(
        default=None,
        description="Optional free-text comment from the rater",
    )


class FeedbackResponse(BaseModel):
    """Response confirming feedback was recorded."""

    status: str = "recorded"
    conversation_id: str
    feedback_type: str


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Collect human feedback as reward signals for agent-lightning.

    This endpoint accepts feedback from:
    - Chatwoot agents rating routing accuracy and response quality
    - Citizens providing satisfaction ratings (via WhatsApp buttons)
    - Internal QA reviews

    Feedback is emitted as reward spans that agent-lightning uses
    for APO (Automatic Prompt Optimization) and RL training.
    """
    attributes = {
        "reward.source": "human_feedback",
        "reward.feedback_type": request.feedback_type,
        "conversation_id": request.conversation_id,
    }
    if request.category:
        attributes["reward.category"] = request.category
    if request.agent_id:
        attributes["reward.agent_id"] = request.agent_id
    if request.comment:
        attributes["reward.comment"] = request.comment

    try:
        emit_reward(request.score, attributes=attributes)
    except Exception as e:
        # Log but don't fail - feedback collection should be best-effort
        logger.warning(f"Failed to emit feedback reward: {e}")

    logger.info(
        f"Feedback recorded: conversation={request.conversation_id}, "
        f"type={request.feedback_type}, score={request.score:.2f}"
    )

    return FeedbackResponse(
        conversation_id=request.conversation_id,
        feedback_type=request.feedback_type,
    )
