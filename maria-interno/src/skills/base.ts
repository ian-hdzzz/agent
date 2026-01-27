// ============================================
// Maria Interno - Base Skill Definition
// ============================================

import type { CategoryCode, SubcategoryCode, TicketPriority } from "../types.js";

/**
 * Skill interface for internal ticket system
 * Each skill corresponds to one department category
 */
export interface InternalSkill {
    /** Category code */
    code: CategoryCode;

    /** Human-readable skill name */
    name: string;

    /** Description for classification */
    description: string;

    /** System prompt for the agent when using this skill */
    systemPrompt: string;

    /** List of tool names this skill can use */
    tools: string[];

    /** Subcategories this skill handles */
    subcategories: SubcategoryInfo[];

    /** Responsible department */
    area_responsable: string;

    /** Whether this skill is currently enabled */
    enabled: boolean;

    /** Default priority for tickets created by this skill */
    defaultPriority?: TicketPriority;
}

export interface SubcategoryInfo {
    code: SubcategoryCode;
    name: string;
    description: string;
    defaultPriority?: TicketPriority;
}

/**
 * Helper to create a skill with type safety
 */
export function createInternalSkill(config: InternalSkill): InternalSkill {
    return config;
}

/**
 * Build context with current date/time for Mexico
 */
export function buildSystemContext(): string {
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "America/Mexico_City" }));
    const dateStr = now.toLocaleDateString('es-MX', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    const timeStr = now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });

    return `[Fecha: ${dateStr}, Hora: ${timeStr} (hora de Querétaro)]`;
}

/**
 * Get emoji for a category
 */
export function getCategoryEmoji(code: CategoryCode): string {
    const emojis: Record<CategoryCode, string> = {
        TI: "💻",
        RH: "👥",
        MNT: "🔧",
        VEH: "🚗",
        ALM: "📦",
        ADM: "📋",
        COM: "📢",
        JUR: "⚖️",
        SEG: "🔒"
    };
    return emojis[code] || "📝";
}
