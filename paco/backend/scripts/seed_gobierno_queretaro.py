"""
Seed script: Import gobierno-queretaro into PACO

Reads the gobierno-queretaro agent source files and populates
paco's DB with Infrastructure, InfraOrchestrator, and InfraAgent records.

Usage:
    cd paco/backend && python scripts/seed_gobierno_queretaro.py
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from textwrap import dedent

import asyncpg

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent.parent  # agents-maria
GOB_ROOT = REPO_ROOT / "gobierno-queretaro"

# ---------------------------------------------------------------------------
# Agent definitions (slug -> meta)
# ---------------------------------------------------------------------------

AGENTS = [
    {"slug": "water-cea",          "code": "CEA", "port": 9101, "conf": "INTERNAL",     "display": "Agente de Agua - CEA",                "desc": "Agua, fugas, consumos, reconexion"},
    {"slug": "transport-ameq",     "code": "TRA", "port": 9102, "conf": "INTERNAL",     "display": "Agente de Transporte - AMEQ",         "desc": "Rutas, horarios, autobus"},
    {"slug": "education-usebeq",   "code": "EDU", "port": 9103, "conf": "INTERNAL",     "display": "Agente de Educacion - USEBEQ",        "desc": "Escuelas, inscripciones, becas"},
    {"slug": "vehicles",           "code": "VEH", "port": 9104, "conf": "INTERNAL",     "display": "Agente de Tramites Vehiculares",      "desc": "Placas, multas, licencias"},
    {"slug": "psychology-sejuve",  "code": "PSI", "port": 9105, "conf": "CONFIDENTIAL", "display": "Agente de Psicologia - SEJUVE",       "desc": "Citas, salud mental"},
    {"slug": "women-iqm",          "code": "IQM", "port": 9106, "conf": "SECRET",       "display": "Agente de Atencion a Mujeres - IQM",  "desc": "Apoyo, violencia de genero"},
    {"slug": "culture",            "code": "CUL", "port": 9107, "conf": "PUBLIC",       "display": "Agente de Cultura",                   "desc": "Eventos, talleres, becas"},
    {"slug": "registry-rpp",       "code": "RPP", "port": 9108, "conf": "CONFIDENTIAL", "display": "Agente de Registro Publico - RPP",    "desc": "Documentos, certificados"},
    {"slug": "labor-cclq",         "code": "LAB", "port": 9109, "conf": "INTERNAL",     "display": "Agente de Conciliacion Laboral - CCLQ","desc": "Trabajo, demandas"},
    {"slug": "housing-iveq",       "code": "VIV", "port": 9110, "conf": "INTERNAL",     "display": "Agente de Vivienda - IVEQ",           "desc": "Creditos, vivienda"},
    {"slug": "appqro",             "code": "APP", "port": 9111, "conf": "PUBLIC",       "display": "Agente de Soporte APPQRO",            "desc": "Soporte de la app"},
    {"slug": "social-sedesoq",     "code": "SOC", "port": 9112, "conf": "INTERNAL",     "display": "Agente de Programas Sociales - SEDESOQ","desc": "Beneficios, ayudas"},
    {"slug": "citizen-attention",  "code": "ATC", "port": 9113, "conf": "INTERNAL",     "display": "Agente de Atencion Ciudadana",        "desc": "Quejas, sugerencias, PQRS"},
]


# ---------------------------------------------------------------------------
# Text parsing helpers
# ---------------------------------------------------------------------------

def read_file(path: Path) -> str:
    """Read file content, return empty string if missing."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"  [WARN] File not found: {path}")
        return ""


def extract_triple_quoted(source: str, var_name: str) -> str | None:
    """Extract a triple-quoted string variable from Python source.

    Handles both plain triple-quoted and f-string triple-quoted assignments.
    Returns None if not found.
    """
    # Match: VAR_NAME = f"""...""" or VAR_NAME = """..."""
    pattern = rf'^{var_name}\s*=\s*f?"""(.*?)"""'
    m = re.search(pattern, source, re.DOTALL | re.MULTILINE)
    if m:
        return m.group(1).strip()

    # Also try single-triple quotes
    pattern = rf"^{var_name}\s*=\s*f?'''(.*?)'''"
    m = re.search(pattern, source, re.DOTALL | re.MULTILINE)
    if m:
        return m.group(1).strip()

    return None


def extract_prompts_dict(source: str) -> dict[str, str]:
    """Extract the PROMPTS = { ... } dictionary from prompts.py.

    Returns dict of key -> prompt text. Since the values contain f-string
    references to BASE_RULES etc., we store the raw text.
    """
    # Find the PROMPTS dict block
    m = re.search(r'^PROMPTS\s*=\s*\{', source, re.MULTILINE)
    if not m:
        return {}

    # Find matching closing brace
    start = m.start()
    brace_count = 0
    end = start
    for i in range(start, len(source)):
        if source[i] == '{':
            brace_count += 1
        elif source[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i + 1
                break

    block = source[start:end]

    # Extract keys - we want the key names (not "inquiry" which points to a var)
    result = {}
    # Match patterns like "key": f"""...""" + BASE_RULES,
    # or "key": """...""",
    key_pattern = r'"(\w+)":\s*f?"""(.*?)"""'
    for km in re.finditer(key_pattern, block, re.DOTALL):
        key = km.group(1)
        # Skip "inquiry" since it typically points to the main system prompt
        if key == "inquiry":
            continue
        text = km.group(2).strip()
        # Clean up f-string references - remove {BASE_RULES} and {KNOWLEDGE_BASE}
        text = re.sub(r'\{BASE_RULES\}', '', text)
        text = re.sub(r'\{KNOWLEDGE_BASE\}', '', text)
        text = text.strip()
        result[key] = text

    return result


def extract_tool_functions(source: str) -> list[dict]:
    """Extract @tool decorated functions from tools.py.

    Returns list of {name, description, function_code, params}.
    """
    tools = []

    # Find all @tool function blocks
    # Pattern: @tool\ndef func_name(...) -> ...:
    # or: @tool\nasync def func_name(...) -> ...:
    pattern = r'(@tool\n(?:async )?def (\w+)\(([^)]*)\)[^:]*:.*?)(?=\n@tool\n|\ndef get_tools|\nclass |\Z)'
    for m in re.finditer(pattern, source, re.DOTALL):
        func_code = m.group(1).rstrip()
        func_name = m.group(2)
        params_raw = m.group(3).strip()

        # Skip common tools that the template already provides
        if func_name in ("handoff_to_human",):
            continue

        # Extract docstring
        doc_match = re.search(r'"""(.*?)"""', func_code, re.DOTALL)
        description = ""
        if doc_match:
            # First line of docstring
            doc_lines = doc_match.group(1).strip().split('\n')
            description = doc_lines[0].strip()

        # Clean params - remove 'self' and type annotations for storage
        params = params_raw

        tools.append({
            "name": func_name,
            "description": description,
            "function_code": func_code,
            "params": params,
        })

    return tools


def extract_keyword_map(source: str) -> dict[str, list[str]]:
    """Extract KEYWORD_MAP from classifier.py."""
    m = re.search(r'^KEYWORD_MAP[^=]*=\s*\{', source, re.MULTILINE)
    if not m:
        return {}

    # Find matching closing brace
    start = m.start()
    brace_count = 0
    end = start
    for i in range(start, len(source)):
        if source[i] == '{':
            brace_count += 1
        elif source[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i + 1
                break

    block = source[start:end]

    # Parse each category
    result = {}
    # Match "CODE": [\n  "keyword1", "keyword2", ...\n]
    cat_pattern = r'"(\w+)":\s*\[(.*?)\]'
    for cm in re.finditer(cat_pattern, block, re.DOTALL):
        code = cm.group(1)
        keywords_raw = cm.group(2)
        # Extract quoted strings
        keywords = re.findall(r'"([^"]+)"', keywords_raw)
        result[code] = keywords

    return result


def extract_classification_prompt(source: str) -> str | None:
    """Extract CLASSIFICATION_PROMPT from classifier.py."""
    return extract_triple_quoted(source, "CLASSIFICATION_PROMPT")


# ---------------------------------------------------------------------------
# Agent data extraction
# ---------------------------------------------------------------------------

def extract_agent_data(slug: str) -> dict:
    """Extract all data for one agent from its source files."""
    agent_dir = GOB_ROOT / "agents" / slug

    # Read source files
    prompts_src = read_file(agent_dir / "prompts.py")
    tools_src = read_file(agent_dir / "tools.py")

    # --- System prompts ---
    system_prompts = {}

    # Extract KNOWLEDGE_BASE
    kb = extract_triple_quoted(prompts_src, "KNOWLEDGE_BASE")
    if kb:
        system_prompts["knowledge_base"] = kb

    # Extract BASE_RULES
    br = extract_triple_quoted(prompts_src, "BASE_RULES")
    if br:
        system_prompts["base_rules"] = br

    # Extract main system prompt (e.g. VEHICLES_SYSTEM_PROMPT, WATER_SYSTEM_PROMPT)
    # Pattern: {SOMETHING}_SYSTEM_PROMPT = f"""..."""
    main_prompt_match = re.search(
        r'^(\w+_SYSTEM_PROMPT)\s*=\s*f?"""(.*?)"""',
        prompts_src, re.DOTALL | re.MULTILINE,
    )
    if main_prompt_match:
        main_prompt_text = main_prompt_match.group(2).strip()
        # Clean f-string references
        main_prompt_text = re.sub(r'\{BASE_RULES\}', '', main_prompt_text)
        main_prompt_text = re.sub(r'\{KNOWLEDGE_BASE\}', '', main_prompt_text)
        main_prompt_text = main_prompt_text.strip()
        system_prompts["main_prompt"] = main_prompt_text

    # Extract task prompts dict
    task_prompts = extract_prompts_dict(prompts_src)
    if task_prompts:
        system_prompts["task_prompts"] = task_prompts

    # --- Tools ---
    tools_config = extract_tool_functions(tools_src)

    return {
        "system_prompts": system_prompts,
        "tools_config": tools_config,
    }


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

async def seed():
    """Main seed function."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://paco:paco_secret@localhost:5432/paco",
    )

    print(f"Connecting to: {db_url}")
    conn = await asyncpg.connect(db_url)

    try:
        # Check if already seeded
        existing = await conn.fetchval(
            "SELECT id FROM infrastructures WHERE name = $1",
            "gobierno-queretaro",
        )
        if existing:
            print(f"Infrastructure 'gobierno-queretaro' already exists (id={existing}).")
            print("Deleting existing data to re-seed...")
            await conn.execute(
                "DELETE FROM infrastructures WHERE name = $1",
                "gobierno-queretaro",
            )
            print("  Deleted. Re-seeding...")

        # ---------------------------------------------------------------
        # 1. Create Infrastructure
        # ---------------------------------------------------------------
        print("\n[1/3] Creating infrastructure...")
        infra_id = await conn.fetchval("""
            INSERT INTO infrastructures (name, display_name, description, port_range_start, db_name, status)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """,
            "gobierno-queretaro",
            "Gobierno de Queretaro",
            "Sistema multi-agente de 13 agentes para servicios del Gobierno de Queretaro",
            9100,
            "gobierno_queretaro",
            "draft",
        )
        print(f"  Infrastructure created: {infra_id}")

        # ---------------------------------------------------------------
        # 2. Create Orchestrator
        # ---------------------------------------------------------------
        print("\n[2/3] Creating orchestrator...")

        classifier_src = read_file(GOB_ROOT / "orchestrator" / "classifier.py")

        keyword_map = extract_keyword_map(classifier_src)
        classification_prompt = extract_classification_prompt(classifier_src) or ""

        print(f"  Extracted {len(keyword_map)} categories from KEYWORD_MAP")
        total_keywords = sum(len(v) for v in keyword_map.values())
        print(f"  Total keywords: {total_keywords}")

        circuit_breaker = {
            "failure_threshold": 5,
            "recovery_timeout": 30,
            "success_threshold": 2,
        }

        orch_id = await conn.fetchval("""
            INSERT INTO infra_orchestrators
                (infrastructure_id, classification_model, classification_temperature,
                 keyword_map, classification_prompt, fallback_agent, agent_timeout,
                 circuit_breaker_config, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """,
            infra_id,
            "claude-sonnet-4-5-20250929",
            0.1,
            json.dumps(keyword_map),
            classification_prompt,
            "ATC",
            30.0,
            json.dumps(circuit_breaker),
            "stopped",
        )
        print(f"  Orchestrator created: {orch_id}")

        # ---------------------------------------------------------------
        # 3. Create 13 Agents
        # ---------------------------------------------------------------
        print(f"\n[3/3] Creating {len(AGENTS)} agents...")

        for agent_meta in AGENTS:
            slug = agent_meta["slug"]
            code = agent_meta["code"]

            print(f"\n  [{code}] {slug}...")

            # Extract data from source files
            agent_data = extract_agent_data(slug)

            # Get keywords for this agent from the keyword map
            agent_keywords = keyword_map.get(code, [])

            # Determine task types from prompts keys
            task_types = list(agent_data["system_prompts"].get("task_prompts", {}).keys())
            if not task_types:
                task_types = ["inquiry"]
            if "inquiry" not in task_types:
                task_types.append("inquiry")

            agent_id = await conn.fetchval("""
                INSERT INTO infra_agents
                    (infrastructure_id, agent_id_slug, display_name, description,
                     category_code, system_prompts, tools_config, task_types,
                     keywords, confidentiality_level, capabilities, port, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
            """,
                infra_id,
                slug,
                agent_meta["display"],
                agent_meta["desc"],
                code,
                json.dumps(agent_data["system_prompts"]),
                json.dumps(agent_data["tools_config"]),
                json.dumps(task_types),
                json.dumps(agent_keywords),
                agent_meta["conf"],
                json.dumps({}),
                agent_meta["port"],
                "stopped",
            )

            n_tools = len(agent_data["tools_config"])
            n_prompts = len(agent_data["system_prompts"].get("task_prompts", {}))
            n_kw = len(agent_keywords)
            has_kb = "knowledge_base" in agent_data["system_prompts"]
            has_main = "main_prompt" in agent_data["system_prompts"]

            print(f"    id={agent_id}")
            print(f"    tools={n_tools}, task_prompts={n_prompts}, keywords={n_kw}")
            print(f"    knowledge_base={'yes' if has_kb else 'no'}, main_prompt={'yes' if has_main else 'no'}")

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------
        agent_count = await conn.fetchval(
            "SELECT COUNT(*) FROM infra_agents WHERE infrastructure_id = $1",
            infra_id,
        )
        print(f"\n{'='*60}")
        print(f"Seed complete!")
        print(f"  Infrastructure: gobierno-queretaro ({infra_id})")
        print(f"  Orchestrator: {orch_id}")
        print(f"  Agents: {agent_count}")
        print(f"  Keyword categories: {len(keyword_map)}")
        print(f"  Total keywords: {total_keywords}")
        print(f"{'='*60}")

    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(seed())
