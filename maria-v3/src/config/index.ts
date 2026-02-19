// ============================================
// Maria V3 - Configuration Exports
// ============================================

export * from "./response-templates.js";

// ============================================
// Environment Configuration
// ============================================

export const config = {
    // Server
    port: parseInt(process.env.PORT || "3002"),
    nodeEnv: process.env.NODE_ENV || "development",

    // Claude
    claudeModel: process.env.CLAUDE_MODEL || "claude-sonnet-4-5-20250929",
    maxBudgetPerMessage: parseFloat(process.env.MAX_BUDGET_PER_MESSAGE || "0.50"),

    // CEA API
    ceaApiBase: process.env.CEA_API_BASE || "https://aquacis-cf.ceaqueretaro.gob.mx/Comercial/services",
    ceaProxyUrl: process.env.CEA_PROXY_URL || null,

    // PostgreSQL
    pg: {
        host: process.env.PGHOST || "localhost",
        port: parseInt(process.env.PGPORT || "5432"),
        user: process.env.PGUSER || "postgres",
        password: process.env.PGPASSWORD || "",
        database: process.env.PGDATABASE || "agora_production",
        max: parseInt(process.env.PGPOOL_MAX || "10")
    },

    // Chatwoot
    chatwoot: {
        baseUrl: process.env.CHATWOOT_BASE_URL || "",
        apiToken: process.env.CHATWOOT_API_TOKEN || ""
    },

    // Memory
    memoryDbPath: process.env.MEMORY_DB_PATH || "./data/maria_memory.db",
    memoryRetentionDays: parseInt(process.env.MEMORY_RETENTION_DAYS || "30"),

    // Cache
    cacheTtlSeconds: parseInt(process.env.CACHE_TTL_SECONDS || "300"),
    cacheCheckPeriod: parseInt(process.env.CACHE_CHECK_PERIOD || "60"),

    // Rate Limiting
    rateLimitConversation: parseInt(process.env.RATE_LIMIT_CONVERSATION || "20"),
    rateLimitApi: parseInt(process.env.RATE_LIMIT_API || "100"),
    rateLimitBudget: parseInt(process.env.RATE_LIMIT_BUDGET || "50"),

    // Logging
    logLevel: process.env.LOG_LEVEL || "info",

    // OpenAI (for Whisper transcription)
    openaiApiKey: process.env.OPENAI_API_KEY || ""
};

/**
 * Validate required configuration
 */
export function validateConfig(): { valid: boolean; missing: string[] } {
    const required = ["ANTHROPIC_API_KEY"];
    const missing: string[] = [];

    for (const key of required) {
        if (!process.env[key]) {
            missing.push(key);
        }
    }

    return {
        valid: missing.length === 0,
        missing
    };
}

/**
 * Check if Chatwoot is configured
 */
export function isChatwootConfigured(): boolean {
    return !!(config.chatwoot.baseUrl && config.chatwoot.apiToken);
}

/**
 * Check if OpenAI is configured (for Whisper)
 */
export function isOpenAIConfigured(): boolean {
    return !!config.openaiApiKey;
}
