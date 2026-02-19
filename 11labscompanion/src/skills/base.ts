/**
 * 11LabsCompanion - Skill Base
 * Foundation for all skill definitions
 */

import type { SkillCode } from "../types.js";

export interface Skill {
  code: SkillCode;
  name: string;
  description: string;
  systemPrompt: string;
  tools: string[];
  keywords: string[];
}

export function createSkill(skill: Skill): Skill {
  return skill;
}

export function buildSystemContext(): string {
  const now = new Date();
  return `Current time: ${now.toLocaleString("en-US", { timeZone: "America/Mexico_City" })}`;
}
