-- PACO Persistent Memory Schema
-- Migration 002: Memory tables for citizen context across sessions
-- Run after init.sql (001)

-- Enable UUID generation if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- memory_config: Global and per-scope memory settings
-- =============================================================================
CREATE TABLE IF NOT EXISTS memory_config (
    id VARCHAR(50) PRIMARY KEY,               -- 'global', 'water-cea', 'vehicles', etc.
    config JSONB NOT NULL DEFAULT '{}',
    updated_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Seed global defaults
INSERT INTO memory_config (id, config, updated_by) VALUES (
    'global',
    '{
        "enabled": true,
        "summarization": {
            "enabled": true,
            "model": "claude-sonnet-4-5-20250929",
            "max_summary_tokens": 300,
            "batch_hour": 1
        },
        "retention": {
            "profile_days": 365,
            "summary_days": 90,
            "memory_days": 180,
            "max_per_citizen": 100
        },
        "injection": {
            "enabled": true,
            "max_in_prompt": 5,
            "include_summaries": true,
            "include_memories": true
        },
        "privacy": {
            "allow_deletion": true,
            "auto_anonymize_days": 730,
            "pii_in_summaries": false
        }
    }',
    'system'
) ON CONFLICT (id) DO NOTHING;

-- IQM disabled by default (sensitive: women's services)
INSERT INTO memory_config (id, config, updated_by) VALUES (
    'women-iqm',
    '{"enabled": false}',
    'system'
) ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- citizen_profiles: High-level citizen identity (orchestrator use)
-- =============================================================================
CREATE TABLE IF NOT EXISTS citizen_profiles (
    contact_id VARCHAR(100) PRIMARY KEY,
    citizen_id_hash VARCHAR(128),              -- Pseudonymized CURP/RFC hash
    display_name_encrypted TEXT,               -- Fernet-encrypted display name
    preferred_language VARCHAR(10) DEFAULT 'es',
    total_conversations INTEGER DEFAULT 0,
    total_tickets INTEGER DEFAULT 0,
    frequent_categories TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    first_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    confidentiality_level VARCHAR(20) DEFAULT 'PUBLIC',
    anonymized_at TIMESTAMPTZ,
    deletion_requested_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_profiles_last_seen ON citizen_profiles(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_profiles_categories ON citizen_profiles USING GIN(frequent_categories);

-- =============================================================================
-- memories: Core scoped fact storage (each agent independently)
-- =============================================================================
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope_id VARCHAR(50) NOT NULL,             -- 'water-cea', 'vehicles', 'orchestrator'
    citizen_contact_id VARCHAR(100) NOT NULL,   -- Chatwoot contact ID
    memory_type VARCHAR(50) NOT NULL,           -- 'fact', 'preference', 'issue', 'note'
    content TEXT NOT NULL,
    content_encrypted BOOLEAN DEFAULT false,
    importance FLOAT DEFAULT 0.5,               -- 0.0-1.0 for retrieval ranking
    tags TEXT[] DEFAULT '{}',
    source_conversation_id VARCHAR(100),
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ
);

-- Scope isolation index (all queries MUST filter by scope_id)
CREATE INDEX IF NOT EXISTS idx_memories_scope_citizen ON memories(scope_id, citizen_contact_id);
CREATE INDEX IF NOT EXISTS idx_memories_scope_importance ON memories(scope_id, importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_expires ON memories(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING GIN(tags);

-- =============================================================================
-- interaction_summaries: Scoped conversation summaries
-- =============================================================================
CREATE TABLE IF NOT EXISTS interaction_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope_id VARCHAR(50) NOT NULL,
    citizen_contact_id VARCHAR(100) NOT NULL,
    conversation_external_id VARCHAR(100),
    summary_text TEXT NOT NULL,
    topics TEXT[] DEFAULT '{}',
    outcome VARCHAR(50),                        -- 'resolved', 'pending', 'escalated', 'abandoned'
    sentiment VARCHAR(20),                      -- 'positive', 'neutral', 'negative', 'frustrated'
    ticket_folios TEXT[] DEFAULT '{}',
    message_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_summaries_scope_citizen ON interaction_summaries(scope_id, citizen_contact_id);
CREATE INDEX IF NOT EXISTS idx_summaries_scope_created ON interaction_summaries(scope_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_summaries_topics ON interaction_summaries USING GIN(topics);

-- =============================================================================
-- system_notes: Admin observations about citizens
-- =============================================================================
CREATE TABLE IF NOT EXISTS system_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citizen_contact_id VARCHAR(100) NOT NULL,
    note_type VARCHAR(50) NOT NULL,             -- 'vip', 'escalation_pattern', 'observation', 'flag'
    content TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'info',        -- 'info', 'warning', 'critical'
    created_by VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notes_citizen ON system_notes(citizen_contact_id);
CREATE INDEX IF NOT EXISTS idx_notes_active ON system_notes(citizen_contact_id, is_active) WHERE is_active = true;

-- =============================================================================
-- memory_audit_log: GDPR compliance trail
-- =============================================================================
CREATE TABLE IF NOT EXISTS memory_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citizen_contact_id VARCHAR(100),
    scope_id VARCHAR(50),
    action VARCHAR(50) NOT NULL,                -- 'created', 'read', 'deleted', 'forgotten', 'anonymized'
    memory_type VARCHAR(50),
    performed_by VARCHAR(100) NOT NULL,         -- 'system', 'admin:username', 'agent:water-cea'
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_citizen ON memory_audit_log(citizen_contact_id);
CREATE INDEX IF NOT EXISTS idx_audit_scope ON memory_audit_log(scope_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON memory_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON memory_audit_log(created_at DESC);

-- =============================================================================
-- conversation_snapshots: Queue for nightly batch summarization
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversation_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_external_id VARCHAR(100) NOT NULL,
    contact_id VARCHAR(100) NOT NULL,
    message_history JSONB NOT NULL DEFAULT '[]',
    agents_involved TEXT[] DEFAULT '{}',
    categories_involved TEXT[] DEFAULT '{}',
    summarized BOOLEAN DEFAULT false,
    session_ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snapshots_unsummarized ON conversation_snapshots(summarized, created_at)
    WHERE summarized = false;
CREATE INDEX IF NOT EXISTS idx_snapshots_contact ON conversation_snapshots(contact_id);

-- =============================================================================
-- Auto-update triggers for updated_at
-- =============================================================================
CREATE OR REPLACE FUNCTION update_memory_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_memory_config_updated') THEN
        CREATE TRIGGER trigger_memory_config_updated
            BEFORE UPDATE ON memory_config
            FOR EACH ROW EXECUTE FUNCTION update_memory_updated_at();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_memories_updated') THEN
        CREATE TRIGGER trigger_memories_updated
            BEFORE UPDATE ON memories
            FOR EACH ROW EXECUTE FUNCTION update_memory_updated_at();
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trigger_system_notes_updated') THEN
        CREATE TRIGGER trigger_system_notes_updated
            BEFORE UPDATE ON system_notes
            FOR EACH ROW EXECUTE FUNCTION update_memory_updated_at();
    END IF;
END
$$;
