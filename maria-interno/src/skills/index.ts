// ============================================
// Maria Interno - Skills Registry
// ============================================

export type { InternalSkill, SubcategoryInfo } from "./base.js";
export { createInternalSkill, buildSystemContext, getCategoryEmoji } from "./base.js";

// Import all skills
export { tiSkill } from "./ti.js";
export { rhSkill } from "./rh.js";
export { mntSkill } from "./mnt.js";
export { vehSkill } from "./veh.js";
export { almSkill } from "./alm.js";
export { admSkill } from "./adm.js";
export { comSkill } from "./com.js";
export { jurSkill } from "./jur.js";
export { segSkill } from "./seg.js";

// Re-export for convenience
import { tiSkill } from "./ti.js";
import { rhSkill } from "./rh.js";
import { mntSkill } from "./mnt.js";
import { vehSkill } from "./veh.js";
import { almSkill } from "./alm.js";
import { admSkill } from "./adm.js";
import { comSkill } from "./com.js";
import { jurSkill } from "./jur.js";
import { segSkill } from "./seg.js";
import type { InternalSkill } from "./base.js";
import type { CategoryCode } from "../types.js";

/**
 * Registry of all skills mapped by category code
 */
export const SKILL_REGISTRY: Record<CategoryCode, InternalSkill> = {
    TI: tiSkill,
    RH: rhSkill,
    MNT: mntSkill,
    VEH: vehSkill,
    ALM: almSkill,
    ADM: admSkill,
    COM: comSkill,
    JUR: jurSkill,
    SEG: segSkill
};

/**
 * Get a skill by category code
 */
export function getSkill(code: CategoryCode): InternalSkill {
    return SKILL_REGISTRY[code];
}

/**
 * Get all skills as an array
 */
export function getAllSkills(): InternalSkill[] {
    return Object.values(SKILL_REGISTRY);
}

/**
 * Get only enabled skills
 */
export function getEnabledSkills(): InternalSkill[] {
    return getAllSkills().filter(skill => skill.enabled);
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
 * Get enabled skill descriptions for classification
 */
export function getEnabledSkillDescriptions(): string {
    return getEnabledSkills()
        .map(skill => `- ${skill.code} (${skill.name}): ${skill.description}`)
        .join('\n');
}

/**
 * Summary of all categories and subcategories count
 */
export function getCategorySummary(): Array<{
    code: CategoryCode;
    name: string;
    subcategories: number;
    area: string;
    enabled: boolean;
}> {
    return getAllSkills().map(skill => ({
        code: skill.code,
        name: skill.name,
        subcategories: skill.subcategories.length,
        area: skill.area_responsable,
        enabled: skill.enabled
    }));
}
