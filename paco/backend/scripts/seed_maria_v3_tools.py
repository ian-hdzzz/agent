"""
Seed script: Register maria-v3 tools into PACO tools table.

Inserts the 9 tools defined in maria-v3/src/tools.ts into the PACO database,
mapped to existing MCP servers (cea-tools, agora-tools).

Idempotent: safe to run multiple times (upserts by name + mcp_server_id).

Usage:
    cd paco/backend && python scripts/seed_maria_v3_tools.py
"""

import asyncio
import json
import os

import asyncpg

# ---------------------------------------------------------------------------
# Tool definitions (from maria-v3/src/tools.ts Zod schemas)
# ---------------------------------------------------------------------------

TOOLS = [
    # ── CEA SOAP API tools (cea-tools server) ──
    {
        "name": "get_deuda",
        "description": "Obtiene el saldo y adeudo de un contrato CEA. Retorna totalDeuda, vencido, porVencer y conceptos.",
        "server_name": "cea-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "contrato": {
                    "type": "string",
                    "description": "Numero de contrato CEA (ej: 123456)",
                },
            },
            "required": ["contrato"],
        },
    },
    {
        "name": "get_consumo",
        "description": "Obtiene el historial de consumo de agua de un contrato. Retorna consumos por periodo, promedio mensual y tendencia.",
        "server_name": "cea-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "contrato": {
                    "type": "string",
                    "description": "Numero de contrato CEA",
                },
                "year": {
                    "type": "number",
                    "description": "Ano especifico para filtrar los consumos (ej: 2022)",
                },
            },
            "required": ["contrato"],
        },
    },
    {
        "name": "get_contract_details",
        "description": "Obtiene los detalles de un contrato CEA. Retorna titular, direccion, tarifa y estado del contrato.",
        "server_name": "cea-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "contrato": {
                    "type": "string",
                    "description": "Numero de contrato CEA",
                },
            },
            "required": ["contrato"],
        },
    },
    {
        "name": "get_recibo_link",
        "description": "Genera el enlace para descargar el recibo digital de un contrato CEA.",
        "server_name": "cea-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "contract_number": {
                    "type": "string",
                    "description": "Numero de contrato CEA",
                },
            },
            "required": ["contract_number"],
        },
    },
    # ── AGORA ticket/CRM tools (agora-tools server) ──
    {
        "name": "create_ticket",
        "description": "Crea un ticket en el sistema AGORA CEA y retorna el folio generado. Categorias: CON, FAC, CTR, CVN, REP, SRV.",
        "server_name": "agora-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "category_code": {
                    "type": "string",
                    "enum": ["CON", "FAC", "CTR", "CVN", "REP", "SRV"],
                    "description": "Codigo de categoria AGORA",
                },
                "subcategory_code": {
                    "type": "string",
                    "description": "Codigo de subcategoria (ej: FAC-001, REP-FVP)",
                },
                "titulo": {
                    "type": "string",
                    "description": "Titulo breve del ticket",
                },
                "descripcion": {
                    "type": "string",
                    "description": "Descripcion detallada del problema",
                },
                "contract_number": {
                    "type": "string",
                    "description": "Numero de contrato - NO requerido para fugas/drenaje en via publica",
                },
                "email": {
                    "type": "string",
                    "description": "Email del cliente (si aplica)",
                },
                "ubicacion": {
                    "type": "string",
                    "description": "Ubicacion - REQUERIDO para reportes REP en via publica",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "default": "medium",
                    "description": "Prioridad del ticket",
                },
            },
            "required": ["category_code", "titulo", "descripcion"],
        },
    },
    {
        "name": "get_client_tickets",
        "description": "Obtiene los tickets de un cliente por numero de contrato. Retorna folio, status, titulo y fecha.",
        "server_name": "agora-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "contract_number": {
                    "type": "string",
                    "description": "Numero de contrato CEA",
                },
            },
            "required": ["contract_number"],
        },
    },
    {
        "name": "search_customer_by_contract",
        "description": "Busca un cliente por su numero de contrato en la base de datos CEA (AGORA contacts).",
        "server_name": "agora-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "contract_number": {
                    "type": "string",
                    "description": "Numero de contrato CEA",
                },
            },
            "required": ["contract_number"],
        },
    },
    {
        "name": "update_ticket",
        "description": "Actualiza el estado u otros campos de un ticket existente. Estados permitidos: in_progress, waiting_client, waiting_internal, escalated.",
        "server_name": "agora-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "folio": {
                    "type": "string",
                    "description": "Folio del ticket a actualizar",
                },
                "status": {
                    "type": "string",
                    "enum": [
                        "open",
                        "in_progress",
                        "waiting_client",
                        "waiting_internal",
                        "escalated",
                        "resolved",
                        "closed",
                        "cancelled",
                    ],
                    "description": "Nuevo estado del ticket",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "Nueva prioridad del ticket",
                },
                "notes": {
                    "type": "string",
                    "description": "Notas adicionales",
                },
            },
            "required": ["folio"],
        },
    },
    {
        "name": "handoff_to_human",
        "description": "Transfiere la conversacion a un agente humano de CEA. Usar cuando el usuario pida hablar con una persona o no se pueda resolver el problema.",
        "server_name": "agora-tools",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Motivo de la transferencia (breve)",
                },
            },
            "required": ["reason"],
        },
    },
]


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

async def seed():
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://paco:paco_secret@localhost:5432/paco",
    )

    print(f"Connecting to: {db_url}")
    conn = await asyncpg.connect(db_url)

    try:
        # Look up MCP server UUIDs
        server_ids = {}
        for server_name in ("cea-tools", "agora-tools"):
            row = await conn.fetchrow(
                "SELECT id FROM mcp_servers WHERE name = $1", server_name
            )
            if not row:
                print(f"ERROR: MCP server '{server_name}' not found in mcp_servers table.")
                print("  Make sure the PACO database has been initialized (docker compose up).")
                return
            server_ids[server_name] = row["id"]
            print(f"  Found server '{server_name}': {row['id']}")

        # Upsert each tool
        inserted = 0
        updated = 0

        for tool_def in TOOLS:
            name = tool_def["name"]
            server_id = server_ids[tool_def["server_name"]]
            description = tool_def["description"]
            input_schema = json.dumps(tool_def["input_schema"])

            existing = await conn.fetchrow(
                "SELECT id FROM tools WHERE name = $1 AND mcp_server_id = $2",
                name,
                server_id,
            )

            if existing:
                await conn.execute(
                    """
                    UPDATE tools
                    SET description = $1, input_schema = $2, is_enabled = true
                    WHERE id = $3
                    """,
                    description,
                    input_schema,
                    existing["id"],
                )
                print(f"  [UPDATE] {tool_def['server_name']}/{name}")
                updated += 1
            else:
                await conn.execute(
                    """
                    INSERT INTO tools (name, description, mcp_server_id, input_schema, is_enabled)
                    VALUES ($1, $2, $3, $4, true)
                    """,
                    name,
                    description,
                    server_id,
                    input_schema,
                )
                print(f"  [INSERT] {tool_def['server_name']}/{name}")
                inserted += 1

        # Summary
        total = await conn.fetchval("SELECT COUNT(*) FROM tools")
        print(f"\n{'='*50}")
        print(f"Seed complete!")
        print(f"  Inserted: {inserted}")
        print(f"  Updated:  {updated}")
        print(f"  Total tools in DB: {total}")
        print(f"{'='*50}")

        # Verification query
        rows = await conn.fetch("""
            SELECT t.name, s.name as server, t.is_enabled
            FROM tools t
            JOIN mcp_servers s ON t.mcp_server_id = s.id
            ORDER BY s.name, t.name
        """)
        print(f"\nTools in database:")
        for row in rows:
            enabled = "enabled" if row["is_enabled"] else "disabled"
            print(f"  {row['server']}/{row['name']} ({enabled})")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed())
