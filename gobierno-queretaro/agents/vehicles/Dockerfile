# ============================================
# Gobierno Queretaro - Vehicles Agent
# LangGraph-based Vehicle Registration Agent
# ============================================

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy shared utilities
COPY shared/ /app/shared/

# Copy template requirements and install
COPY agents/_template/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent-specific code
COPY agents/vehicles/ /app/agent/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
