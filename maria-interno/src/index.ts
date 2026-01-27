// ============================================
// Maria Interno - Main Entry Point
// ============================================

export { runInternalWorkflow, getAgentHealth } from "./agent.js";
export { allTools } from "./tools.js";
export * from "./types.js";
// Export skills explicitly to avoid InternalSkill conflict
export {
    createInternalSkill,
    buildSystemContext,
    getCategoryEmoji,
    tiSkill,
    rhSkill,
    mntSkill,
    vehSkill,
    almSkill,
    admSkill,
    comSkill,
    jurSkill,
    segSkill,
    SKILL_REGISTRY,
    getSkill,
    getAllSkills,
    getEnabledSkills,
    getSkillDescriptions,
    getEnabledSkillDescriptions,
    getCategorySummary
} from "./skills/index.js";

// Start server when run directly
import "./server.js";
