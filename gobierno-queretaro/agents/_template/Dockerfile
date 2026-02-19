# ============================================
# Gobierno Querétaro - Agent Dockerfile
# LangGraph-based Government Service Agent
# ============================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy shared utilities first (for better caching)
COPY shared/ /app/shared/

# Copy requirements and install dependencies
COPY agents/_template/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code (will be overridden by specific agent)
COPY agents/_template/ /app/agent/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the agent
CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
