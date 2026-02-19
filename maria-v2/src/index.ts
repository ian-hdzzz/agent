// ============================================
// Maria V2 - Main Entry Point
// ============================================

import { config } from "dotenv";
config();

// Re-export for programmatic usage
export { runWorkflow, getAgentHealth, shutdown } from "./agent.js";
export { SKILL_REGISTRY, getSkill, getAllSkills } from "./skills/index.js";
export * from "./types.js";
export { metrics } from "./utils/metrics.js";
export { getCache } from "./utils/cache.js";
export { getMemoryStore } from "./utils/memory.js";

// Start server if running directly
if (import.meta.url === `file://${process.argv[1]}`) {
    await import("./server.js");
}
