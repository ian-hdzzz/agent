"""
Migrate agents from legacy schema to SDK-aligned schema.

Parses existing config_yaml to extract model, system_prompt, etc.
and populates the new SDK-aligned columns.

Usage:
    python -m scripts.migrate_agents_to_sdk
"""

import asyncio
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.db.session import async_session_maker


async def migrate():
    migrated = 0

    async with async_session_maker() as db:
        # Check if config_yaml column still exists
        col_check = await db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'agents' AND column_name = 'config_yaml'
        """))
        has_config_yaml = col_check.first() is not None

        if not has_config_yaml:
            print("config_yaml column not found — migration may have already run or schema is already updated")
            return

        result = await db.execute(text("""
            SELECT id, name, config_yaml, type, runtime
            FROM agents
            WHERE config_yaml IS NOT NULL AND config_yaml != ''
        """))
        rows = result.fetchall()

        for row in rows:
            agent_id = row[0]
            agent_name = row[1]
            config_yaml_str = row[2]
            agent_type = row[3]
            runtime = row[4]

            try:
                config = yaml.safe_load(config_yaml_str) if config_yaml_str else {}
            except Exception as e:
                print(f"  Error parsing YAML for '{agent_name}': {e}")
                config = {}

            if not config:
                continue

            # Extract SDK-aligned fields from config_yaml
            model = config.get("model", "claude-sonnet-4-5-20250929")
            system_prompt = config.get("system_prompt") or config.get("systemPrompt")
            permission_mode = config.get("permission_mode", "default")
            max_turns = config.get("max_turns")
            max_budget_usd = config.get("max_budget_usd")
            max_thinking_tokens = config.get("max_thinking_tokens")

            # Extract env_vars from various locations in config
            env_vars = config.get("env_vars") or config.get("env") or {}

            # Build sdk_config from remaining useful config
            sdk_config = {}
            for key in ("temperature", "top_p", "top_k", "stop_sequences", "max_tokens"):
                if key in config:
                    sdk_config[key] = config[key]

            await db.execute(
                text("""
                    UPDATE agents SET
                        model = :model,
                        system_prompt = :system_prompt,
                        permission_mode = :permission_mode,
                        max_turns = :max_turns,
                        max_budget_usd = :max_budget_usd,
                        max_thinking_tokens = :max_thinking_tokens,
                        env_vars = :env_vars,
                        sdk_config = :sdk_config
                    WHERE id = :id
                """),
                {
                    "id": agent_id,
                    "model": model,
                    "system_prompt": system_prompt,
                    "permission_mode": permission_mode,
                    "max_turns": max_turns,
                    "max_budget_usd": max_budget_usd,
                    "max_thinking_tokens": max_thinking_tokens,
                    "env_vars": str(env_vars) if not isinstance(env_vars, str) else env_vars,
                    "sdk_config": str(sdk_config) if not isinstance(sdk_config, str) else sdk_config,
                },
            )

            migrated += 1
            print(f"  Migrated '{agent_name}' (model={model}, permission_mode={permission_mode})")

        await db.commit()

    print(f"\nMigration complete: {migrated} agents migrated to SDK-aligned schema")
    print("You can now safely drop legacy columns: type, version, config_yaml, runtime, conversation_rules,")
    print("classifier_config, memory_config, cache_config, rate_limit_config, metrics_config, webhook_config, confidentiality_level")


if __name__ == "__main__":
    asyncio.run(migrate())
