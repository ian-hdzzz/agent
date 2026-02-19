"""
Conversation summarization using Claude.
"""

import json
import logging
from typing import Optional

from anthropic import Anthropic

from .models import InteractionSummary
from .config import MemoryConfig

logger = logging.getLogger(__name__)


SUMMARY_PROMPT_ES = """Eres un asistente que resume conversaciones de servicio gubernamental.

Analiza la conversación y produce un resumen estructurado en JSON con estos campos:
- summary_text: Resumen conciso en español (máximo 2-3 oraciones)
- topics: Lista de temas tratados (ej: ["consulta de adeudo", "reporte de fuga"])
- outcome: Uno de: "resolved", "pending", "escalated", "abandoned"
- sentiment: Uno de: "positive", "neutral", "negative", "frustrated"
- ticket_folios: Lista de folios mencionados (ej: ["CEA-20250101-A1B2"])

{pii_instruction}

Responde SOLO con el JSON, sin texto adicional."""

PII_STRIP = "IMPORTANTE: NO incluyas datos personales (nombres, CURP, RFC, direcciones, teléfonos, números de contrato). Usa referencias genéricas."
PII_ALLOW = "Puedes incluir datos como números de contrato o folios que ayuden al seguimiento."


class ConversationSummarizer:
    """Generate conversation summaries using Claude."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-5-20250929"):
        self._client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self._model = model

    def summarize(
        self,
        messages: list[dict],
        scope_id: str,
        config: MemoryConfig,
        pii_allowed: bool = False,
    ) -> Optional[InteractionSummary]:
        """Summarize a conversation for a specific scope."""
        if not messages:
            return None

        # Format conversation
        conversation_text = self._format_messages(messages)
        if not conversation_text.strip():
            return None

        pii_instruction = PII_ALLOW if pii_allowed else PII_STRIP
        system_prompt = SUMMARY_PROMPT_ES.format(pii_instruction=pii_instruction)

        try:
            response = self._client.messages.create(
                model=config.summarization.model or self._model,
                max_tokens=config.summarization.max_summary_tokens or 300,
                temperature=0.1,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"Conversación del agente '{scope_id}':\n\n{conversation_text}"
                }],
            )

            content = response.content[0].text.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            data = json.loads(content)

            return InteractionSummary(
                scope_id=scope_id,
                citizen_contact_id="",  # Caller fills this in
                summary_text=data.get("summary_text", ""),
                topics=data.get("topics", []),
                outcome=data.get("outcome"),
                sentiment=data.get("sentiment"),
                ticket_folios=data.get("ticket_folios", []),
                message_count=len(messages),
            )

        except Exception as e:
            logger.error(f"Summarization failed for scope {scope_id}: {e}")
            return None

    def summarize_batch(
        self,
        snapshots: list,
        config: MemoryConfig,
    ) -> list[tuple[str, InteractionSummary]]:
        """
        Summarize multiple conversation snapshots.

        Returns list of (scope_id, summary) tuples — one per agent involved in each snapshot.
        """
        results = []

        for snapshot in snapshots:
            for scope_id in snapshot.agents_involved:
                summary = self.summarize(
                    messages=snapshot.message_history,
                    scope_id=scope_id,
                    config=config,
                    pii_allowed=config.privacy.pii_in_summaries,
                )
                if summary:
                    summary.citizen_contact_id = snapshot.contact_id
                    summary.conversation_external_id = snapshot.conversation_external_id
                    results.append((scope_id, summary))

        return results

    @staticmethod
    def _format_messages(messages: list[dict]) -> str:
        """Format message list into readable text."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    block.get("text", "") for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
            if content:
                label = "Ciudadano" if role == "user" else "Agente"
                lines.append(f"{label}: {content}")
        return "\n".join(lines)
