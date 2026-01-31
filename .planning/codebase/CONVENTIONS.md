# Coding Conventions

**Analysis Date:** 2026-01-31

## Naming Patterns

**Files:**
- Use kebab-case for test files: `test.ts`, `test-api.ts`, `test-all-tickets.ts`
- Use camelCase for regular source files: `server.ts`, `agent.ts`, `tools.ts`, `context.ts`
- Use PascalCase for files containing skills: `consultas.ts`, `contratos.ts`, `consumos.ts`
- Use descriptive names reflecting module purpose: `get-contract-info.ts`, `response-templates.ts`

**Functions:**
- Use camelCase consistently: `fetchWithRetry()`, `generateTicketFolio()`, `parseXMLValue()`, `getMexicoDate()`
- Use verb-prefixed names for actions: `get*`, `create*`, `parse*`, `build*`, `generate*`, `run*`
- Examples: `getDeuda()`, `buildSystemContext()`, `runWorkflow()`, `createSkill()`

**Variables:**
- Use camelCase for all local variables and parameters
- Use SCREAMING_SNAKE_CASE for constants: `MODELS`, `CEA_API_BASE`, `PROXY_URL`, `PG_CONFIG`
- Map objects use SCREAMING_SNAKE_CASE: `TICKET_CODES`, `SERVICE_TYPE_MAP`, `PRIORITY_MAP`, `STATUS_MAP`
- Examples: `pgPool`, `conversationStore`, `classificationAgent`, `ticketType`

**Types & Interfaces:**
- Use PascalCase for interfaces: `ChatRequest`, `ChatResponse`, `WorkflowInput`, `ConversationEntry`
- Use PascalCase for types: `Classification`, `TicketType`, `TicketStatus`
- Use PascalCase for TypeScript enums and unions: `CategoryCode`, `SubcategoryCode`
- Example from `types.ts`:
  ```typescript
  export interface ChatRequest {
    message: string;
    conversationId?: string;
  }

  export type Classification =
    | "fuga"
    | "pagos"
    | "hablar_asesor";
  ```

## Code Style

**Formatting:**
- No explicit linter/formatter configuration detected (no .eslintrc, .prettierrc, biome.json)
- Use 2-space indentation (consistent across all files)
- Line length: typically 80-100 characters
- Import statements at file top, organized by source

**Comments:**
- Use comment blocks with equals for section headers:
  ```typescript
  // ============================================
  // Section Name
  // ============================================
  ```
- Inline comments explain "why", not "what"
- Examples from `server.ts` and `agent.ts`:
  ```typescript
  // Request logging middleware
  app.use((req: Request, res: Response, next: NextFunction) => {

  // Cleanup old conversations (1 hour expiry)
  setInterval(() => {
  ```
- No JSDoc/TSDoc documentation enforced - comments are prose-based

**Spacing:**
- Blank line after imports
- Blank line after type/interface definitions
- Blank line before function definitions
- Blank lines between logical sections marked with comment headers

## Import Organization

**Order:**
1. Third-party imports (express, zod, dotenv, etc.)
2. Node built-ins (import type from async_hooks, etc.)
3. Local imports (relative paths with .js extension)
4. Type imports (prefixed with `import type`)

**Path Aliases:**
- Not used in this codebase
- All imports use relative paths: `"./agent.js"`, `"./tools.js"`, `"./types.js"`
- Imports always include `.js` extension for ES modules

**Examples from codebase:**
```typescript
// From server.ts
import express, { Request, Response, NextFunction } from "express";
import { config } from "dotenv";
import { runWorkflow, getAgentHealth } from "./agent.js";
import type { ChatRequest, ChatResponse } from "./types.js";

// From agent.ts
import { Agent, AgentInputItem, Runner, withTrace } from "@openai/agents";
import { z } from "zod";
import type { WorkflowInput, WorkflowOutput, Classification } from "./types.js";
```

## Error Handling

**Pattern: Try-Catch with Success/Error Objects**

Most functions follow a return object pattern rather than throwing:
```typescript
// From tools.ts - parseDeudaResponse
try {
    if (xml.includes("<faultstring>") || xml.includes("<error>")) {
        const faultMsg = parseXMLValue(xml, "faultstring") || parseXMLValue(xml, "error") || "Error desconocido";
        return { success: false, error: faultMsg };
    }
    // ... parsing logic
    return { success: true, data: { ... } };
} catch (error) {
    return { success: false, error: `Error parsing response: ${error}` };
}
```

**Pattern: API Response Handling**

API functions return typed response objects with `success` boolean and `data` or `error` fields:
- `DeudaResponse`: `{ success: boolean; data?: {...}; error?: string }`
- `ConsumoResponse`: `{ success: boolean; data?: {...}; error?: string }`
- `CreateTicketResult`: `{ success: boolean; folio?: string; error?: string }`

Example from `server.ts` - HTTP error handling:
```typescript
if (!message || typeof message !== "string") {
    res.status(400).json({
        error: "Missing or invalid 'message' field",
        response: "",
        conversationId: conversationId || crypto.randomUUID()
    } as ChatResponse);
    return;
}
```

**Pattern: Async Error Handling**

In async functions, use try-catch with structured error response:
```typescript
// From server.ts - handleChat
async function handleChat(req: Request, res: Response): Promise<void> {
    try {
        // ... process
        res.json(response);
    } catch (error) {
        console.error(`[${requestId}] Error:`, error);
        const errorMessage = error instanceof Error ? error.message : "Internal server error";
        res.status(500).json({
            error: NODE_ENV === "development" ? errorMessage : "Internal server error",
            response: "Lo siento, hubo un error procesando tu mensaje.",
            conversationId: ...
        });
    }
}
```

**Pattern: Request Retry Logic**

API calls use exponential backoff retry:
```typescript
// From tools.ts - fetchWithRetry
async function fetchWithRetry(
    url: string,
    options: RequestInit,
    maxRetries = 3,
    delayMs = 1000
): Promise<Response> {
    let lastError: Error | null = null;
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            // ... attempt request
            if (!response.ok && attempt < maxRetries) {
                await new Promise(r => setTimeout(r, delayMs * attempt));
                continue;
            }
            return response;
        } catch (error) {
            lastError = error as Error;
            if (attempt < maxRetries) {
                await new Promise(r => setTimeout(r, delayMs * attempt));
            }
        }
    }
    throw lastError || new Error("Request failed after retries");
}
```

## Logging

**Framework:** `console` (no structured logging library)

**Patterns:**

1. **Request tracking with IDs:**
   ```typescript
   const requestId = crypto.randomUUID().substring(0, 8);
   console.log(`→ [${requestId}] ${req.method} ${req.path}`);
   console.log(`← [${requestId}] ${res.statusCode} (${duration}ms)`);
   ```

2. **Workflow progress logging:**
   ```typescript
   console.log(`[${requestId}] Processing: "${message.substring(0, 100)}"`);
   console.log(`[${requestId}] Classification: ${result.classification}`);
   console.log(`[${requestId}] Response length: ${response.response.length} chars`);
   ```

3. **Informational messages:**
   ```typescript
   console.log(`[API] Using proxy: ${PROXY_URL} for ${url}`);
   console.log(`[API] Attempt ${attempt} failed with status ${response.status}, retrying...`);
   ```

4. **Error logging:**
   ```typescript
   console.error(`[${requestId}] Error:`, error);
   console.error("Unhandled error:", error);
   ```

## Function Design

**Size:** Functions typically 10-50 lines; longer functions (100+ lines) broken by internal comments marking sections

**Parameters:**
- Use typed parameters (TypeScript strict mode)
- Pass objects for multiple related parameters (not individual args)
- Example:
  ```typescript
  async function runWithChatwootContext<T>(
      context: ChatwootContext,
      fn: () => T | Promise<T>
  ): T | Promise<T>
  ```

**Return Values:**
- Use explicit return types (no implicit `any`)
- Return objects with `success` boolean for operations
- Return typed interfaces for complex data: `ChatResponse`, `WorkflowOutput`, `DeudaResponse`
- Return void only for side-effect functions

**Default Parameters:**
- Used for retry logic: `maxRetries = 3, delayMs = 1000`
- Used for API configuration: `limit: "10mb"`

## Module Design

**Exports:**
- Use named exports for tools: `export const getDeudaTool`, `export const createTicketTool`
- Use default export for single main function where appropriate
- Export types with `export interface/type`
- Re-export utilities with `export { getCurrentChatwootContext }`

**Examples from `tools.ts`:**
```typescript
export const getDeudaTool = tool({
    name: "get_deuda",
    description: "...",
    // ...
});

export const createTicketTool = tool({
    // ...
});

export { nativeTools };
```

**File Organization:**
- All tools in `tools.ts`: `getDeudaTool`, `getConsumoTool`, `createTicketTool`, etc.
- All types in `types.ts`: interfaces, unions, constants
- All agent definitions in `agent.ts`: one agent per skill/category
- All helper functions: `getMexicoDate()`, `generateTicketFolio()` in respective modules

## TypeScript Configuration

**File:** `tsconfig.json`
- Target: ES2022
- Module: ESNext
- Module resolution: node
- Strict mode: enabled
- Declaration: true
- skipLibCheck: true

**Type Safety:**
- Never use `any` - use `unknown` and narrow, or correct type
- Exception: `@ts-ignore` used only for undici types compatibility
- Example: `// @ts-ignore - undici types are compatible at runtime`

## Special Patterns

**Agent Configuration:**

Agents are statically defined with consistent structure:
```typescript
const classificationAgent = new Agent({
    name: "Clasificador María",
    model: MODELS.CLASSIFIER,
    instructions: `...`,  // Long multiline string
    outputType: ClassificationSchema,  // Zod schema
    modelSettings: {
        temperature: 0.3,
        maxTokens: 256
    }
});
```

**Zod Schema Usage:**

Validation schemas define tool parameters and agent outputs:
```typescript
const ClassificationSchema = z.object({
    classification: z.enum([...]),
    confidence: z.number().min(0).max(1).nullable(),
    extractedContract: z.string().nullable()
});
```

**Conversation State Management:**

Uses Map for in-memory conversation tracking:
```typescript
const conversationStore = new Map<string, ConversationEntry>();

function getConversation(id: string): ConversationEntry {
    const existing = conversationStore.get(id);
    if (existing) {
        existing.lastAccess = new Date();
        return existing;
    }
    // ... create new entry
}

// Cleanup old entries every 5 minutes
setInterval(() => {
    const now = Date.now();
    for (const [id, entry] of conversationStore.entries()) {
        if (now - entry.lastAccess.getTime() > 3600000) {
            conversationStore.delete(id);
        }
    }
}, 300000);
```

---

*Convention analysis: 2026-01-31*
