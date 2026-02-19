#!/bin/bash
# ============================================
# Gobierno Querétaro - Create New Agent Script
# Scaffolds a new agent from the template
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$PROJECT_DIR/agents/_template"
AGENTS_DIR="$PROJECT_DIR/agents"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 <agent-id> <agent-name> <category-code>"
    echo ""
    echo "Arguments:"
    echo "  agent-id       Unique identifier (e.g., 'transport-ameq')"
    echo "  agent-name     Display name (e.g., 'Agente de Transporte - AMEQ')"
    echo "  category-code  Category code (e.g., 'TRA')"
    echo ""
    echo "Example:"
    echo "  $0 transport-ameq 'Agente de Transporte - AMEQ' TRA"
    exit 1
}

# Check arguments
if [ $# -lt 3 ]; then
    usage
fi

AGENT_ID="$1"
AGENT_NAME="$2"
CATEGORY_CODE="$3"
AGENT_DIR="$AGENTS_DIR/$AGENT_ID"

# Check if agent already exists
if [ -d "$AGENT_DIR" ]; then
    echo -e "${RED}Error: Agent '$AGENT_ID' already exists at $AGENT_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}Creating new agent: $AGENT_ID${NC}"
echo "  Name: $AGENT_NAME"
echo "  Category: $CATEGORY_CODE"
echo ""

# Create agent directory
mkdir -p "$AGENT_DIR"

# Copy template files
echo "Copying template files..."
cp "$TEMPLATE_DIR/Dockerfile" "$AGENT_DIR/"
cp "$TEMPLATE_DIR/__init__.py" "$AGENT_DIR/"
cp "$TEMPLATE_DIR/config.py" "$AGENT_DIR/"
cp "$TEMPLATE_DIR/prompts.py" "$AGENT_DIR/"
cp "$TEMPLATE_DIR/tools.py" "$AGENT_DIR/"
cp "$TEMPLATE_DIR/agent.py" "$AGENT_DIR/"
cp "$TEMPLATE_DIR/main.py" "$AGENT_DIR/"

# Update Dockerfile
echo "Updating Dockerfile..."
sed -i.bak "s|agents/_template|agents/$AGENT_ID|g" "$AGENT_DIR/Dockerfile"
rm -f "$AGENT_DIR/Dockerfile.bak"

# Update config.py
echo "Updating config.py..."
sed -i.bak "s|agent_id: str = \"template-agent\"|agent_id: str = \"$AGENT_ID\"|g" "$AGENT_DIR/config.py"
sed -i.bak "s|agent_name: str = \"Template Agent\"|agent_name: str = \"$AGENT_NAME\"|g" "$AGENT_DIR/config.py"
rm -f "$AGENT_DIR/config.py.bak"

# Update agent.py AGENT_CONFIG
echo "Updating agent.py..."
sed -i.bak "s|\"id\": \"template-agent\"|\"id\": \"$AGENT_ID\"|g" "$AGENT_DIR/agent.py"
sed -i.bak "s|\"name\": \"Template Agent\"|\"name\": \"$AGENT_NAME\"|g" "$AGENT_DIR/agent.py"
sed -i.bak "s|\"category_code\": \"ATC\"|\"category_code\": \"$CATEGORY_CODE\"|g" "$AGENT_DIR/agent.py"
rm -f "$AGENT_DIR/agent.py.bak"

echo ""
echo -e "${GREEN}Agent '$AGENT_ID' created successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $AGENT_DIR/config.py to add any custom settings"
echo "  2. Edit $AGENT_DIR/prompts.py to customize system prompts"
echo "  3. Edit $AGENT_DIR/tools.py to add domain-specific tools"
echo "  4. Edit $AGENT_DIR/agent.py to customize task types and handlers"
echo ""
echo "To add to docker-compose.yml, add:"
echo ""
echo "  agent-$AGENT_ID:"
echo "    build: ./agents/$AGENT_ID"
echo "    container_name: gobierno-agent-$AGENT_ID"
echo "    restart: unless-stopped"
echo "    ports:"
echo "      - \"800X:8000\"  # Choose unused port"
echo "    environment:"
echo "      - AGENT_ID=$AGENT_ID"
echo "      - AGENT_NAME=$AGENT_NAME"
echo "      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}"
echo "      - DATABASE_URL=postgres://postgres:postgres@postgres:5432/gobierno"
echo "      - REDIS_URL=redis://redis:6379"
echo "    networks:"
echo "      - gobierno-network"
