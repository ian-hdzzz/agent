# Phase 6 Research: Knowledge & Validation

**Phase:** 06-knowledge-validation
**Date:** 2026-02-04
**Discovery Level:** 0 (Skip) - All work follows established codebase patterns

## Research Summary

No external research needed. Phase 6 uses established patterns from Phases 3-5:

1. **Node creation pattern** - nodes.tsx BaseNode component
2. **Type guards pattern** - guards.ts function pattern
3. **Properties panel pattern** - React Hook Form + Zod schemas
4. **Library integration pattern** - library.tsx sections
5. **Store integration pattern** - store.tsx addNode, updateNode

## Existing Infrastructure

### Data Model Types (Already Defined)

From `frontend/types/datamodel.ts`:

```typescript
// Knowledge Base Configuration
export type KnowledgeSourceType = 'document' | 'url' | 'database';

export interface KnowledgeConfig {
  name: string;
  sourceType: KnowledgeSourceType;
  sources: string[];  // File paths or URLs
  chunkSize?: number;
  overlapSize?: number;
}

// Logic Node Configuration
export type LogicType = 'condition' | 'loop' | 'parallel' | 'approval';

export interface LogicConfig {
  name: string;
  logicType: LogicType;
  condition?: string;
  maxIterations?: number;
}
```

### Type Guards (Skeleton Exists)

From `frontend/types/guards.ts`:

```typescript
export function isKnowledgeComponent(
  component: Component<ComponentConfig>
): component is Component<KnowledgeConfig> {
  return false; // Knowledge not yet supported
}

export function isLogicComponent(
  component: Component<ComponentConfig>
): component is Component<LogicConfig> {
  return false; // Logic not yet supported
}
```

### Icon Mapping (Exists)

From `frontend/components/builder/nodes.tsx`:

```typescript
export const iconMap: Record<...> = {
  // ... existing types
  knowledge: BookOpen,
  logic: GitBranch,
  workflow: Workflow,
};
```

### Component Types (Exists)

From `frontend/types/datamodel.ts`:

```typescript
export type ComponentTypes =
  | 'agent'
  | 'mcp-server'
  | 'tool'
  | 'knowledge'  // Already defined
  | 'logic'      // Already defined
  | 'workflow'
  // Legacy types...
```

## Implementation Approach

### Plan 06-01: Knowledge Base Node

Following MCP server pattern from Phase 5:
1. Enable type guards for knowledge component
2. Create KnowledgeNode component (similar to McpServerNode)
3. Create knowledge-base-form.tsx with source type selection
4. Add Knowledge Base section to library.tsx
5. Update properties panel to render KnowledgeForm

### Plan 06-02: Logic Node

Following agent node pattern:
1. Enable type guards for logic component
2. Create LogicNode component
3. Create logic-form.tsx with condition editor
4. Add Logic section to library.tsx
5. Update properties panel to render LogicForm

### Plan 06-03: Workflow Validation

New pattern but uses existing infrastructure:
1. Create validation utilities (check connections, required fields)
2. Create ValidationErrors component (UI for displaying errors)
3. Integrate validation into builder.tsx (show errors on save attempt)
4. Add validation checks to store (optional - could be component-level)

## Validation Rules

### Connection Validation

- Agent nodes should connect to at least one source (MCP, knowledge, or built-in tools)
- Knowledge nodes should connect to agents (not floating)
- Logic nodes should have at least one incoming and one outgoing connection
- No cycles allowed (basic check for infinite loops)

### Configuration Validation

- Agent: Must have name, model, system prompt (recommended)
- Knowledge: Must have name, sourceType, at least one source
- Logic: Must have name, logicType, condition for condition/loop types
- MCP Server: Must have command (stdio) or URL (sse/http)

## File Structure

```
frontend/components/builder/
├── properties-panel/
│   ├── schemas/
│   │   ├── knowledge-schema.ts   # New
│   │   └── logic-schema.ts       # New
│   ├── knowledge-form.tsx        # New
│   ├── logic-form.tsx            # New
│   └── index.tsx                 # Update
├── validation/
│   ├── index.ts                  # New
│   ├── rules.ts                  # New
│   └── types.ts                  # New
├── nodes.tsx                     # Update
├── library.tsx                   # Update
└── builder.tsx                   # Update
```

## Decision Log

| Decision | Rationale |
|----------|-----------|
| File upload as path input | Full upload infrastructure is out of scope; user provides file path or URL |
| Show validation on save | Don't block editing, show errors when attempting to save/export |
| Validation as component | Separate ValidationErrors component for reusability |
| Basic cycle detection | Prevent obvious infinite loops without complex graph analysis |

---
*Research completed: 2026-02-04*
