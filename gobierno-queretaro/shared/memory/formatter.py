"""
Format memory bundles into context strings for prompt injection.
"""

from .models import MemoryBundle


class MemoryFormatter:
    """Format recalled memories into context strings for prompt injection."""

    @staticmethod
    def format(bundle: MemoryBundle, scope_type: str = "agent", language: str = "es") -> str:
        """
        Format a MemoryBundle into a context string.

        Args:
            bundle: The recalled memories and summaries.
            scope_type: "agent" or "orchestrator" — changes the header.
            language: Output language (only "es" supported for now).

        Returns:
            Formatted context string, or empty string if no content.
        """
        parts = []

        if scope_type == "orchestrator":
            header = "CONTEXTO DEL CIUDADANO"
        else:
            header = "MEMORIA DEL CIUDADANO (tus interacciones previas)"

        # Profile summary (orchestrator only)
        if bundle.profile and scope_type == "orchestrator":
            p = bundle.profile
            profile_parts = []
            if p.total_conversations > 0:
                profile_parts.append(f"Visitas totales: {p.total_conversations}")
            if p.total_tickets > 0:
                profile_parts.append(f"Tickets creados: {p.total_tickets}")
            if p.frequent_categories:
                cats = ", ".join(p.frequent_categories[:5])
                profile_parts.append(f"Categorías frecuentes: {cats}")
            if p.tags:
                profile_parts.append(f"Etiquetas: {', '.join(p.tags[:5])}")
            if p.first_seen_at:
                profile_parts.append(f"Primera visita: {p.first_seen_at.strftime('%Y-%m-%d')}")
            if profile_parts:
                parts.append("Perfil: " + " | ".join(profile_parts))

        # System notes (orchestrator only)
        if bundle.notes and scope_type == "orchestrator":
            for note in bundle.notes[:3]:
                severity_prefix = ""
                if note.severity == "critical":
                    severity_prefix = "[CRITICO] "
                elif note.severity == "warning":
                    severity_prefix = "[AVISO] "
                parts.append(f"Nota: {severity_prefix}{note.content}")

        # Memories
        if bundle.memories:
            for mem in bundle.memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                parts.append(f"- {mem.content}{tags_str}")

        # Summaries
        if bundle.summaries:
            for summary in bundle.summaries:
                date_str = summary.created_at.strftime("%d/%m") if summary.created_at else ""
                outcome_str = f" ({summary.outcome})" if summary.outcome else ""
                parts.append(f"- Conversación previa{f' ({date_str})' if date_str else ''}: "
                             f"{summary.summary_text}{outcome_str}")

        if not parts:
            return ""

        return f"{header}:\n" + "\n".join(parts)
