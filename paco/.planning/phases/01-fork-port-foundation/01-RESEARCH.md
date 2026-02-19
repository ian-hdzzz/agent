# Phase 1: Fork & Port Foundation - Research

**Researched:** 2026-02-03
**Domain:** React canvas/flow UI migration from Gatsby to Next.js App Router with Claude Agent SDK data model
**Confidence:** HIGH

## Summary

This phase involves extracting the AutoGen Studio frontend's canvas builder components and porting them from Gatsby to Next.js App Router, while updating the data model types to align with the Claude Agent SDK instead of AutoGen.

The AutoGen Studio source at `/tmp/autogen-temp/python/packages/autogen-studio/frontend/` contains a well-structured React application with:
- A **Zustand store** (733 lines) managing canvas state with undo/redo
- **React Flow** (`@xyflow/react` v12.3.5) for the node-based canvas
- **Ant Design** for UI components
- **Component editor** with MCP workbench UI

The Gatsby-specific patterns are limited to:
- `graphql` imports for static data at build time
- `Link` component from `gatsby` (in ~8 files)
- `navigate` function from `gatsby` (in ~3 files)
- Gatsby plugin configuration

The good news: **The builder components themselves have zero Gatsby dependencies** - they are pure React components using Zustand and React Flow. The Gatsby patterns are isolated to page wrappers and navigation.

**Primary recommendation:** Extract builder components as-is, create Next.js App Router page wrappers with `'use client'` directive, and replace Gatsby `Link`/`navigate` with Next.js equivalents.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@xyflow/react` | ^12.4.4 | Node-based canvas/flow UI | Official React Flow library; already used by AutoGen Studio |
| `zustand` | ^5.0.1 | Client state management | Already used; works well with Next.js App Router |
| `next` | ^15.x | Framework | PACO standard; App Router is recommended approach |
| `react` | ^18.2.0 | UI library | Standard React version |
| `antd` | ^5.22.1 | UI component library | Already used by AutoGen Studio for drawer, button, etc. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@dnd-kit/core` | ^6.2.0 | Drag and drop | Component library drag-drop to canvas |
| `@dagrejs/dagre` | ^1.1.4 | Graph layout | Auto-layout of nodes |
| `nanoid` | latest | ID generation | Node/edge ID generation |
| `lodash` | latest | Utilities | debounce, clone, isEqual |
| `@monaco-editor/react` | ^4.6.0 | Code/JSON editor | JSON view of agent configuration |
| `lucide-react` | ^0.460.0 | Icons | UI icons |
| `@headlessui/react` | ^2.2.0 | Accessible UI primitives | Dropdowns, dialogs |
| `@heroicons/react` | ^2.0.18 | Icon set | Additional icons |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Ant Design | shadcn/ui | Would require rewriting all UI components; stick with antd for faster port |
| Zustand | Jotai/Redux | Zustand already works; no reason to change |
| React Flow | Custom canvas | Would lose undo/redo, zoom, pan, minimap for free |

**Installation:**
```bash
npm install @xyflow/react zustand @dnd-kit/core @dagrejs/dagre nanoid lodash @monaco-editor/react lucide-react antd @headlessui/react @heroicons/react
```

## Architecture Patterns

### Recommended Project Structure
```
paco/frontend/
├── src/
│   └── app/
│       └── builder/
│           └── page.tsx        # 'use client' page for canvas
├── components/
│   └── builder/                # Ported from AutoGen Studio
│       ├── store.tsx           # Zustand store (keep as-is)
│       ├── types.ts            # Update for Claude Agent SDK
│       ├── builder.tsx         # Main canvas component
│       ├── nodes.tsx           # Node type definitions
│       ├── library.tsx         # Component library sidebar
│       ├── toolbar.tsx         # Canvas toolbar
│       ├── utils.ts            # Layout utilities
│       ├── layout-storage.ts   # Position persistence
│       └── component-editor/   # Property panel
│           ├── component-editor.tsx
│           └── fields/
│               ├── agent-fields.tsx
│               ├── tool-fields.tsx
│               └── workbench/   # MCP UI
│                   ├── mcp-capabilities-panel.tsx
│                   ├── mcp-tools-tab.tsx
│                   └── useMcpWebSocket.ts
├── lib/
│   └── stores/                 # Zustand stores
│       └── builder-store.ts    # Re-export for Next.js patterns
└── types/
    ├── datamodel.ts            # Claude Agent SDK types (new)
    └── guards.ts               # Type guards (updated)
```

### Pattern 1: Client Component for React Flow
**What:** React Flow requires browser APIs and cannot be a Server Component
**When to use:** Any page using the canvas builder
**Example:**
```typescript
// src/app/builder/page.tsx
'use client';

import { ReactFlow, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { TeamBuilder } from '@/components/builder/builder';

export default function BuilderPage() {
  return (
    <div className="h-screen w-full">
      <TeamBuilder />
    </div>
  );
}
```
Source: [React Flow Next.js App Router Example](https://github.com/xyflow/react-flow-example-apps/tree/main/reactflow-nextjs-app-router)

### Pattern 2: Zustand Store with Next.js App Router
**What:** Keep stores outside app directory, use context for per-request isolation if needed
**When to use:** Client-side state that doesn't need server-side rendering
**Example:**
```typescript
// lib/stores/builder-store.ts
'use client';
import { create } from 'zustand';
import { CustomNode, CustomEdge } from '@/types/builder';

export interface TeamBuilderState {
  nodes: CustomNode[];
  edges: CustomEdge[];
  // ... rest of state
}

export const useTeamBuilderStore = create<TeamBuilderState>((set, get) => ({
  // ... existing implementation
}));
```
Source: [Zustand Next.js Guide](https://zustand.docs.pmnd.rs/guides/nextjs)

### Pattern 3: Replace Gatsby Link with Next.js Link
**What:** Navigation component swap
**When to use:** All internal navigation
**Example:**
```typescript
// Before (Gatsby)
import { Link } from 'gatsby';
<Link to="/build">Build</Link>

// After (Next.js)
import Link from 'next/link';
<Link href="/build">Build</Link>
```
Source: [Next.js Migration from Gatsby](https://nextjs.org/docs/app/guides/migrating/app-router-migration)

### Pattern 4: Replace Gatsby navigate with Next.js useRouter
**What:** Programmatic navigation
**When to use:** Navigation triggered by code (auth redirects, form submissions)
**Example:**
```typescript
// Before (Gatsby)
import { navigate } from 'gatsby';
navigate('/login');

// After (Next.js)
'use client';
import { useRouter } from 'next/navigation';
const router = useRouter();
router.push('/login');
```

### Anti-Patterns to Avoid
- **Global Zustand stores in Server Components:** Store state is client-side only; don't try to access in server components
- **Missing 'use client' directive:** Any component using React Flow, Zustand, or browser APIs must have `'use client'`
- **Importing React Flow in Server Components:** Will cause hydration errors
- **Using Gatsby's graphql for data fetching:** Replace with Next.js data fetching patterns (fetch in Server Components or client-side SWR)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Node-based canvas | Custom canvas with SVG/Canvas | `@xyflow/react` | Zoom, pan, minimap, selection, undo/redo built-in |
| Undo/redo | Custom history stack | Zustand history from AutoGen Studio | Already implemented, handles edge cases |
| Drag-and-drop | Custom drag handlers | `@dnd-kit/core` | Accessibility, touch support, collision detection |
| Graph layout | Custom positioning algorithm | `@dagrejs/dagre` | Proper graph layout algorithms |
| Code/JSON editor | Textarea | `@monaco-editor/react` | Syntax highlighting, validation, intellisense |
| Unique IDs | Custom UUID | `nanoid` | Smaller, faster, collision-resistant |

**Key insight:** AutoGen Studio already solved these problems. Port the solutions, don't rebuild them.

## Common Pitfalls

### Pitfall 1: Hydration Mismatches with React Flow
**What goes wrong:** Server-rendered HTML doesn't match client-rendered React Flow nodes
**Why it happens:** React Flow relies on browser APIs (window, document) not available during SSR
**How to avoid:** Always use `'use client'` directive on any component that imports from `@xyflow/react`
**Warning signs:** Console errors about hydration mismatches, nodes appearing then disappearing

### Pitfall 2: Zustand Store Shared Across Requests
**What goes wrong:** User A sees User B's state in the store
**Why it happens:** Server-side store is singleton, shared between all requests
**How to avoid:** Only use Zustand in client components; don't access store in Server Components or server actions
**Warning signs:** State bleeding between users, stale data after navigation

### Pitfall 3: Missing CSS for React Flow
**What goes wrong:** Canvas renders but nodes are invisible or mispositioned
**Why it happens:** React Flow's required CSS not imported
**How to avoid:** Always import `'@xyflow/react/dist/style.css'` in the component using ReactFlow
**Warning signs:** Empty canvas, nodes positioned at 0,0, no zoom/pan controls visible

### Pitfall 4: Deep Clone Required for Zustand State Updates
**What goes wrong:** UI doesn't update when nested object properties change
**Why it happens:** Shallow comparison doesn't detect nested changes
**How to avoid:** Use `JSON.parse(JSON.stringify(component))` for deep clone (as AutoGen Studio does)
**Warning signs:** Form changes not reflected, undo/redo not working correctly

### Pitfall 5: AutoGen Provider Strings in Type Guards
**What goes wrong:** Type guards fail after porting because provider strings reference AutoGen
**Why it happens:** Provider strings like `"autogen_agentchat.teams.SelectorGroupChat"` are hardcoded
**How to avoid:** Create new PROVIDERS constant with Claude Agent SDK equivalents
**Warning signs:** All components fail type guards, "unknown component type" errors

## Code Examples

Verified patterns from official sources:

### React Flow Basic Setup (Next.js App Router)
```typescript
// Source: https://github.com/xyflow/react-flow-example-apps
'use client';

import { useCallback } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Background,
  MiniMap,
  Connection
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export default function Flow() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      >
        <Background />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
```

### Gatsby to Next.js Link Migration
```typescript
// Before (Gatsby header.tsx line 21, 111-114)
import { Link } from "gatsby";
<Link className="hover:text-accent" to={data.href}>
  {data.name}
</Link>

// After (Next.js)
import Link from 'next/link';
<Link className="hover:text-accent" href={data.href}>
  {data.name}
</Link>
```

### Gatsby to Next.js Navigate Migration
```typescript
// Before (Gatsby auth/context.tsx, auth/protected.tsx, pages/login.tsx)
import { navigate } from "gatsby";
navigate('/login');

// After (Next.js)
'use client';
import { useRouter } from 'next/navigation';

function Component() {
  const router = useRouter();
  // ...
  router.push('/login');
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `reactflow` package | `@xyflow/react` package | 2024 | Update imports; API is compatible |
| Gatsby graphql queries | Next.js Server Components + fetch | Next.js 13+ (2023) | No build-time data layer needed |
| Gatsby Link | Next.js Link | N/A | `to` prop becomes `href` |
| Gatsby navigate | Next.js useRouter | N/A | Different import path and API |
| Zustand v4 | Zustand v5 | 2024 | Minor API changes; AutoGen uses v5 already |

**Deprecated/outdated:**
- `reactflow` package name: Replaced by `@xyflow/react` under xyflow umbrella
- Gatsby's useStaticQuery: Not applicable in Next.js; use server components or client-side fetching
- Pages Router: App Router is now the recommended Next.js approach

## Claude Agent SDK Data Model Types

The Claude Agent SDK TypeScript types are fundamentally different from AutoGen's data model. Key differences:

### AutoGen Data Model (Current)
```typescript
// Component wrapper with provider-based polymorphism
interface Component<T extends ComponentConfig> {
  provider: string;  // e.g., "autogen_agentchat.teams.SelectorGroupChat"
  component_type: ComponentTypes;
  config: T;
}

// Type discrimination via provider strings
const PROVIDERS = {
  SELECTOR_TEAM: "autogen_agentchat.teams.SelectorGroupChat",
  ASSISTANT_AGENT: "autogen_agentchat.agents.AssistantAgent",
  // ... many AutoGen-specific providers
};
```

### Claude Agent SDK Types (Target)
```typescript
// Source: https://platform.claude.com/docs/en/agent-sdk/typescript

// Agent definition for subagents
interface AgentDefinition {
  description: string;
  tools?: string[];
  prompt: string;
  model?: 'sonnet' | 'opus' | 'haiku' | 'inherit';
}

// MCP Server configuration (similar structure to AutoGen's McpWorkbench)
type McpServerConfig =
  | McpStdioServerConfig    // command + args + env
  | McpSSEServerConfig      // url + headers
  | McpHttpServerConfig     // url + headers
  | McpSdkServerConfigWithInstance;  // in-process server

// Tool definitions (built-in tools + MCP tools)
type ToolInput =
  | BashInput
  | FileEditInput
  | FileReadInput
  | WebSearchInput
  // ... many built-in tools
```

### Key Transformation Strategy
The canvas will need PACO-specific types that bridge visual representation and Claude Agent SDK configuration:

```typescript
// PACO Component (for canvas)
interface PacoComponent<T extends PacoComponentConfig> {
  id: string;
  type: 'agent' | 'tool' | 'mcp-server';
  label: string;
  config: T;
}

// Agent node on canvas
interface PacoAgentConfig {
  name: string;
  description: string;
  prompt: string;
  model: 'sonnet' | 'opus' | 'haiku';
  tools: string[];  // Built-in tool names
  mcpServers: string[];  // References to MCP server nodes
}

// MCP Server node on canvas
interface PacoMcpServerConfig {
  name: string;
  type: 'stdio' | 'sse' | 'http';
  command?: string;  // for stdio
  url?: string;      // for sse/http
  args?: string[];
  env?: Record<string, string>;
}
```

## Open Questions

Things that couldn't be fully resolved:

1. **MCP WebSocket Protocol in PACO**
   - What we know: AutoGen Studio has `useMcpWebSocket.ts` for real-time MCP server communication
   - What's unclear: Whether PACO will use the same WebSocket approach or Claude Agent SDK's native MCP handling
   - Recommendation: Port the UI components but abstract the WebSocket layer for later replacement

2. **Validation API Replacement**
   - What we know: AutoGen Studio has `validationAPI.validateComponent()` for server-side validation
   - What's unclear: What PACO's validation endpoint will look like
   - Recommendation: Create validation interface, mock implementation initially

3. **Gallery/Team Persistence**
   - What we know: AutoGen Studio stores teams/galleries in a database via API
   - What's unclear: PACO's persistence strategy (local storage? backend?)
   - Recommendation: Port components with persistence interface, implement storage layer separately

## Sources

### Primary (HIGH confidence)
- AutoGen Studio source code at `/tmp/autogen-temp/python/packages/autogen-studio/frontend/` - Direct file analysis
- [Claude Agent SDK TypeScript Reference](https://platform.claude.com/docs/en/agent-sdk/typescript) - Complete type definitions
- [React Flow Next.js App Router Example](https://github.com/xyflow/react-flow-example-apps/tree/main/reactflow-nextjs-app-router) - Official example
- [Zustand Next.js Guide](https://zustand.docs.pmnd.rs/guides/nextjs) - Official documentation

### Secondary (MEDIUM confidence)
- [Next.js Migration from Gatsby](https://nextjs.org/docs/app/guides/migrating/app-router-migration) - Official migration guide
- [React Flow Quick Start](https://reactflow.dev/learn) - Official documentation
- [xyflow Spring 2025 Update](https://xyflow.com/blog/spring-update-2025) - Recent version information

### Tertiary (LOW confidence)
- Various Medium articles on Zustand + Next.js patterns (validated against official docs)
- Community discussions on Gatsby to Next.js migration patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Direct analysis of AutoGen Studio source code
- Architecture: HIGH - Official React Flow examples and Zustand docs confirm patterns
- Pitfalls: HIGH - Well-documented issues with React Flow SSR and Zustand Next.js usage
- Claude SDK types: MEDIUM - Official documentation reviewed but integration patterns are new

**Research date:** 2026-02-03
**Valid until:** 30 days (stable libraries, patterns well-established)
