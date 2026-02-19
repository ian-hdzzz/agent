/**
 * 11LabsCompanion - Skills Registry
 */

export type { Skill } from "./base.js";
export { createSkill, buildSystemContext } from "./base.js";

// Import all skills
export { voicesSkill } from "./voices.js";
export { agentsSkill } from "./agents.js";
export { toolsSkill } from "./tools.js";
export { knowledgeSkill } from "./knowledge.js";
export { audioSkill } from "./audio.js";
export { conversationsSkill } from "./conversations.js";
export { accountSkill } from "./account.js";

// Re-export for convenience
import { voicesSkill } from "./voices.js";
import { agentsSkill } from "./agents.js";
import { toolsSkill } from "./tools.js";
import { knowledgeSkill } from "./knowledge.js";
import { audioSkill } from "./audio.js";
import { conversationsSkill } from "./conversations.js";
import { accountSkill } from "./account.js";
import type { Skill } from "./base.js";
import type { SkillCode } from "../types.js";

/**
 * Registry of all skills mapped by code
 */
export const SKILL_REGISTRY: Record<SkillCode, Skill> = {
  VOI: voicesSkill,
  AGT: agentsSkill,
  TLS: toolsSkill,
  KNB: knowledgeSkill,
  AUD: audioSkill,
  CNV: conversationsSkill,
  ACC: accountSkill
};

/**
 * Get a skill by code
 */
export function getSkill(code: SkillCode): Skill {
  return SKILL_REGISTRY[code];
}

/**
 * Get all skills as an array
 */
export function getAllSkills(): Skill[] {
  return Object.values(SKILL_REGISTRY);
}

/**
 * Get skill descriptions for classification
 */
export function getSkillDescriptions(): string {
  return getAllSkills()
    .map(skill => `- ${skill.code} (${skill.name}): ${skill.description}`)
    .join('\n');
}

/**
 * Classify user input to determine which skill to use
 */
export function classifyInput(input: string): SkillCode {
  const inputLower = input.toLowerCase();

  // Check each skill's keywords
  for (const skill of getAllSkills()) {
    for (const keyword of skill.keywords) {
      if (inputLower.includes(keyword)) {
        return skill.code;
      }
    }
  }

  // Default to account for general queries or greetings
  if (inputLower.includes("hello") || inputLower.includes("hi") ||
      inputLower.includes("help") || inputLower.includes("status")) {
    return "ACC";
  }

  // Default to agents as it's the most common use case
  return "AGT";
}
