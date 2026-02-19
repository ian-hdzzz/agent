"""
Gobierno Querétaro - Agent-Lightning Tracing
Centralized tracing and reward signal collection for the multi-agent system.
"""

from .setup import get_store, get_tracer, init_tracing
from .auto_rewards import AutoRewardEvaluator, get_reward_evaluator

__all__ = [
    "init_tracing",
    "get_store",
    "get_tracer",
    "AutoRewardEvaluator",
    "get_reward_evaluator",
]
