// ============================================
// Maria V2 - Response Validator & Enforcer
// ============================================

import { logger } from "./logger.js";

export interface ValidationResult {
    valid: boolean;
    violations: string[];
    correctedResponse?: string;
}

/**
 * Response rules from MARIA_DOCUMENTATION.md
 */
const RULES = {
    // Rule 1: Max 2-3 sentences
    maxSentences: 3,

    // Rule 2: One question per message (check for multiple question marks)
    maxQuestions: 1,

    // Rule 4: No internal codes (FAC-004, etc.)
    noInternalCodes: /\b(CON|FAC|CTR|CVN|REP|SRV|CNS)-\d+\b/gi,

    // Rule 8: No emojis at end of message (already handled in prompt)
    trailingEmoji: /\s*[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]+\s*$/u,

    // Prohibited prefixes
    prohibitedPrefixes: [
        /^voy a (consultar|revisar|buscar|verificar)/i,
        /^d[eé]jame (consultar|revisar|buscar|verificar)/i,
        /^un momento/i,
        /^esp[eé]rame/i,
        /^claro[,.]?\s*(aqu[ií] est[aá]|d[eé]jame|voy a)/i,
        /^listo[,.]?\s*(aqu[ií] est[aá])/i
    ]
};

/**
 * Count sentences in text
 */
function countSentences(text: string): number {
    // Split by sentence-ending punctuation
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    return sentences.length;
}

/**
 * Count questions in text
 */
function countQuestions(text: string): number {
    const matches = text.match(/\?/g);
    return matches ? matches.length : 0;
}

/**
 * Check for prohibited prefixes
 */
function checkProhibitedPrefixes(text: string): string[] {
    const violations: string[] = [];
    for (const pattern of RULES.prohibitedPrefixes) {
        if (pattern.test(text)) {
            violations.push(`Prohibited prefix: ${pattern.source}`);
        }
    }
    return violations;
}

/**
 * Validate response against conversation rules
 */
export function validateResponse(response: string): ValidationResult {
    const violations: string[] = [];

    // Check 1: Sentence count
    const sentenceCount = countSentences(response);
    if (sentenceCount > RULES.maxSentences) {
        violations.push(`Too many sentences (${sentenceCount} > ${RULES.maxSentences})`);
    }

    // Check 2: Question count
    const questionCount = countQuestions(response);
    if (questionCount > RULES.maxQuestions) {
        violations.push(`Too many questions (${questionCount} > ${RULES.maxQuestions})`);
    }

    // Check 3: Internal codes
    if (RULES.noInternalCodes.test(response)) {
        violations.push("Contains internal category codes (FAC-004, etc.)");
    }

    // Check 4: Trailing emojis
    if (RULES.trailingEmoji.test(response)) {
        violations.push("Contains trailing emojis");
    }

    // Check 5: Prohibited prefixes
    violations.push(...checkProhibitedPrefixes(response));

    return {
        valid: violations.length === 0,
        violations
    };
}

/**
 * Try to auto-correct common violations
 */
export function autoCorrect(response: string): string {
    let corrected = response;

    // Remove trailing emojis
    corrected = corrected.replace(RULES.trailingEmoji, "");

    // Remove prohibited prefixes
    for (const pattern of RULES.prohibitedPrefixes) {
        corrected = corrected.replace(pattern, "");
    }

    // Clean up multiple spaces
    corrected = corrected.replace(/\s+/g, " ").trim();

    // Ensure first letter is capitalized
    corrected = corrected.charAt(0).toUpperCase() + corrected.slice(1);

    return corrected;
}

/**
 * Validate and optionally correct response
 */
export function validateAndCorrect(response: string): {
    original: string;
    corrected: string;
    wasCorrected: boolean;
    violations: string[];
} {
    const validation = validateResponse(response);
    
    if (validation.valid) {
        return {
            original: response,
            corrected: response,
            wasCorrected: false,
            violations: []
        };
    }

    const corrected = autoCorrect(response);
    const reValidation = validateResponse(corrected);

    logger.warn({
        original: response.slice(0, 100),
        violations: validation.violations,
        corrected: corrected !== response
    }, "Response validation issues detected");

    return {
        original: response,
        corrected,
        wasCorrected: corrected !== response,
        violations: validation.violations
    };
}

/**
 * Check if response is a formatted_response from a tool
 */
export function isFormattedResponse(response: string): boolean {
    // Check for formatted_response marker in JSON
    return response.includes('"formatted_response"') || 
           response.includes("'formatted_response'");
}

/**
 * Extract formatted_response from tool output
 */
export function extractFormattedResponse(toolOutput: string): string | null {
    try {
        const parsed = JSON.parse(toolOutput);
        if (parsed.formatted_response) {
            return parsed.formatted_response;
        }
    } catch {
        // Not valid JSON, return null
    }
    return null;
}

/**
 * Sanitize user input to prevent prompt injection
 */
export function sanitizeInput(input: string): string {
    return input
        .slice(0, 1000) // Limit length
        .replace(/[<>]/g, "") // Remove potential HTML/XML
        .replace(/\{\{.*?\}\}/g, "") // Remove template syntax
        .trim();
}
