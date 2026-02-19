# Phase 2: Canvas Integration - Research

**Researched:** 2026-02-03
**Domain:** React Flow canvas integration with Next.js App Router layout and Claude-oriented node types
**Confidence:** HIGH

## Summary

This phase focuses on integrating the already-ported canvas components from Phase 1 with PACO's existing layout system, and adapting the node types for Claude Agent SDK workflows. The canvas components (builder.tsx, nodes.tsx, library.tsx, store.tsx) are fully functional but exist in isolation from PACO's dashboard layout with sidebar navigation.

The primary integration challenges are:
1. **Layout integration**: The builder route currently bypasses PACO's standard layout (sidebar + header). It needs to integrate with authentication and navigation while providing maximum canvas workspace.
2. **Node type adaptation**: Current nodes are AutoGen-oriented (team, agent, model, termination, workbench). Claude Agent SDK has different concepts (agents with built-in tools, MCP servers, subagents).
3. **Component library organization**: The palette currently shows AutoGen component categories. It needs to reflect Claude-oriented categories.

The codebase is well-structured for this integration. Phase 1 established clean type guards, a flexible data model with Claude SDK alignment, and dnd-kit + React Flow integration that works correctly. The existing PACO layout pattern (sidebar with `pl-64` offset) can be adapted for the builder with minimal changes.

**Primary recommendation:** Integrate builder with PACO's authenticated layout pattern, add a "Builder" link to the sidebar navigation, and progressively adapt node types to prioritize Claude Agent SDK concepts while maintaining backward compatibility with existing AutoGen patterns.

## Standard Stack

The stack is already established from Phase 1 and PACO's existing dependencies.

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@xyflow/react` | ^12.10.0 | Node-based canvas/flow UI | Already integrated in builder.tsx |
| `zustand` | ^4.5.7 | Client state management | Already used for auth and builder store |
| `@dnd-kit/core` | ^6.3.1 | Drag and drop | Already integrated in builder.tsx |
| `next` | 14.1.0 | Framework | PACO's existing framework |
| `antd` | ^6.2.3 | UI components | Already used for Drawer, Button, Collapse, etc. |
| `lucide-react` | ^0.312.0 | Icons | Already used throughout PACO |

### Supporting (Already Installed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@dagrejs/dagre` | ^2.0.3 | Graph layout | Auto-layout of nodes |
| `nanoid` | ^5.1.6 | ID generation | Node/edge ID generation |
| `lodash` | ^4.17.23 | Utilities | debounce, clone, isEqual |
| `@monaco-editor/react` | ^4.7.0 | Code/JSON editor | JSON view (TODO in builder) |

### No New Dependencies Required

All required libraries are already in package.json. No new installations needed for Phase 2.

## Architecture Patterns

### Recommended Project Structure (No Changes)

The current structure from Phase 1 is correct:
```
frontend/
├── app/
│   └── builder/
│       ├── layout.tsx         # Needs: auth + sidebar integration
│       └── page.tsx           # Already: renders TeamBuilder
├── components/
│   ├── ui/
│   │   ├── Sidebar.tsx        # Needs: "Builder" link added
│   │   └── Header.tsx         # Existing PACO header
│   └── builder/               # All Phase 1 components (complete)
│       ├── builder.tsx
│       ├── nodes.tsx
│       ├── library.tsx
│       ├── store.tsx
│       ├── toolbar.tsx
│       ├── component-editor/
│       └── ...
└── types/
    ├── datamodel.ts           # Claude SDK-aligned types (complete)
    └── guards.ts              # Type guards (complete)
```

### Pattern 1: Builder Layout with PACO Sidebar Integration

**What:** The builder route should integrate with PACO's authenticated layout pattern while maximizing canvas workspace.

**When to use:** For the `/builder` route layout.

**Current State (builder/layout.tsx):**
```typescript
// Current: Bare layout without sidebar/auth
export default function BuilderLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {children}
    </div>
  );
}
```

**Target Pattern:**
```typescript
// Source: PACO's existing agents/layout.tsx pattern
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/ui/Sidebar";

export default function BuilderLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token } = useAuth();

  useEffect(() => {
    if (!token) {
      router.push("/auth/login");
    }
  }, [token, router]);

  if (!token) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="pl-64 h-screen overflow-hidden">
        {children}
      </main>
    </div>
  );
}
```

### Pattern 2: Claude-Oriented Node Type Mapping

**What:** Map Claude Agent SDK concepts to visual node types.

**Claude Agent SDK Concepts:**
- **Agents**: Primary actors with system prompts, model selection, and tools
- **Built-in Tools**: bash, file operations, web search, etc.
- **MCP Servers**: External tool providers (stdio, sse, http types)
- **Subagents**: Agents spawned by other agents for specialized tasks

**Current Node Types (AutoGen-oriented):**
| Current Type | Maps To | Action |
|--------------|---------|--------|
| `team` | `workflow` | Rename, simplify (no team coordination model) |
| `agent` | `agent` | Keep, enhance with Claude SDK fields |
| `model` | Remove | Claude handles model internally |
| `workbench` | `mcp-server` | Rename, MCP servers are primary tool mechanism |
| `tool` | `built-in-tool` | Keep for static tool config |
| `termination` | Remove | Not used in Claude Agent SDK |

**Target Node Type Hierarchy:**
```typescript
// Primary nodes (what users primarily create)
type PrimaryNodeTypes = 'agent' | 'workflow';

// Connection nodes (attached to agents)
type ConnectionNodeTypes = 'mcp-server' | 'built-in-tool';

// Future nodes (Phase 3+)
type FutureNodeTypes = 'knowledge' | 'logic';
```

### Pattern 3: Component Library Organization for Claude

**What:** Reorganize the palette to reflect Claude Agent SDK concepts.

**Current Library Structure (AutoGen):**
```
- Agents (AssistantAgent, WebSurfer, etc.)
- Models (gpt-4, claude-3, etc.)
- Workbenches (StaticWorkbench, MCPWorkbench)
- Tools (deprecated label)
- Terminations
```

**Target Library Structure (Claude):**
```
- Agents
  - Claude Agent (main agent type)
  - Subagent templates
- MCP Servers
  - Stdio Server (local commands)
  - SSE Server (remote streaming)
  - HTTP Server (REST-based)
- Built-in Tools
  - Bash
  - File Read/Write/Edit
  - Web Search
  - Glob/Grep
```

### Pattern 4: Edge Connection Rules

**What:** Define which node types can connect to which.

**Connection Rules:**
```typescript
const EDGE_RULES: Record<ComponentTypes, ComponentTypes[]> = {
  // Workflow is the root - can have agents
  'workflow': [],  // Nothing connects TO workflow

  // Agents can receive MCP servers and built-in tools
  'agent': ['workflow'],  // Agents connect FROM workflow

  // MCP servers connect to agents
  'mcp-server': ['agent'],  // MCP servers connect TO agents

  // Built-in tools connect to agents
  'tool': ['agent'],  // Tools connect TO agents
};

// Visual: workflow -> agent -> [mcp-server, tool]
```

**Handle Positions:**
- Workflow: Right handle (output to agents)
- Agent: Left handle (input from workflow), no output handles
- MCP Server: Embedded in agent node (drop zone)
- Tool: Embedded in agent node (drop zone)

### Anti-Patterns to Avoid

- **Separate node types for models:** Claude Agent SDK handles model selection internally. Don't create separate model nodes - include model selection in agent configuration.

- **Complex team coordination:** AutoGen has SelectorGroupChat, Swarm, RoundRobin. Claude Agent SDK uses subagent delegation. Don't replicate AutoGen's team types.

- **Termination conditions as nodes:** Claude agents don't need external termination - they complete naturally. Don't create termination nodes.

- **Workbench wrapper nodes:** AutoGen wraps tools in workbenches. Claude uses MCP servers directly. Don't create intermediary wrapper nodes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-drop from palette | Custom pointer tracking | `@dnd-kit/core` | Already integrated, handles touch/accessibility |
| Node connections | Custom line drawing | React Flow edges | Already works with handle system |
| Undo/redo | Custom history stack | Zustand store pattern | Already implemented in store.tsx |
| Canvas pan/zoom | Custom transform math | React Flow built-in | Already works |
| Node selection | Custom click handlers | React Flow selection | Already works |
| Auto-layout | Custom positioning | Dagre (already used) | Already works in utils.ts |

**Key insight:** Phase 1 already solved all the hard problems. Phase 2 is primarily about reorganization and configuration, not new functionality.

## Common Pitfalls

### Pitfall 1: Breaking Authentication on Builder Route

**What goes wrong:** Builder page accessible without login.
**Why it happens:** Builder layout doesn't include auth check pattern from other PACO layouts.
**How to avoid:** Copy the exact auth pattern from `agents/layout.tsx` or `dashboard/layout.tsx`.
**Warning signs:** Unauthenticated access to /builder, missing sidebar.

### Pitfall 2: Height Calculation Issues in Constrained Layout

**What goes wrong:** Canvas height is wrong, scrollbars appear, minimap clips.
**Why it happens:** Combining PACO's `pl-64` sidebar offset with builder's `h-screen`.
**How to avoid:** Use `h-screen overflow-hidden` on the main container, ensure builder fills available space.
**Warning signs:** Double scrollbars, canvas doesn't fill viewport.

### Pitfall 3: Node Type Registration Mismatch

**What goes wrong:** "Unknown node type" warnings in console, nodes don't render.
**Why it happens:** nodeTypes object doesn't match component_type values in data.
**How to avoid:** Keep nodeTypes registration in sync with ComponentTypes enum.
**Warning signs:** Console warnings about unregistered node types, blank nodes.

### Pitfall 4: Drop Zone Validation Divergence

**What goes wrong:** Users can drop MCP servers on workflows, but it doesn't work.
**Why it happens:** validateDropTarget in builder.tsx doesn't match new node type rules.
**How to avoid:** Update validTargets in builder.tsx when changing node types.
**Warning signs:** Visual drop acceptance but no effect, silent failures.

### Pitfall 5: Type Guard Breakage

**What goes wrong:** Type guards return false for all components.
**Why it happens:** Changing provider strings without updating PROVIDERS constant in guards.ts.
**How to avoid:** Update PROVIDERS when introducing new component types, add new type guards.
**Warning signs:** Components not rendering correctly, "unknown type" in UI.

### Pitfall 6: Sidebar Link Not Active

**What goes wrong:** Builder link in sidebar doesn't show active state.
**Why it happens:** Path matching logic in Sidebar.tsx doesn't include /builder.
**How to avoid:** Add builder to navigation array with correct href.
**Warning signs:** No highlighted link when on builder route.

## Code Examples

### Adding Builder to Sidebar Navigation

```typescript
// Source: Sidebar.tsx (add to navigation array)
import { Workflow } from "lucide-react";  // Add icon import

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Builder", href: "/builder", icon: Workflow },  // Add this line
  { name: "Agents", href: "/agents", icon: Bot },
  { name: "Tools", href: "/tools", icon: Wrench },
  { name: "Executions", href: "/executions", icon: Activity },
  { name: "Users", href: "/users", icon: Users, adminOnly: true },
  { name: "Settings", href: "/settings", icon: Settings },
];
```

### Updated Builder Layout with Auth

```typescript
// Source: app/builder/layout.tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "@/components/ui/Sidebar";

export default function BuilderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { token, refreshUser } = useAuth();

  useEffect(() => {
    if (!token) {
      router.push("/auth/login");
    } else {
      refreshUser();
    }
  }, [token, router, refreshUser]);

  if (!token) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="pl-64 h-screen overflow-hidden">
        <div className="flex flex-col h-full">
          {children}
        </div>
      </main>
    </div>
  );
}
```

### Claude-Oriented Library Sections

```typescript
// Source: library.tsx - updated sections
const sections = React.useMemo(() => [
  {
    title: "Agents",
    type: "agent" as ComponentTypes,
    items: [
      {
        label: "Claude Agent",
        config: {
          provider: "claude.agent.ClaudeAgent",
          component_type: "agent",
          version: 1,
          label: "Claude Agent",
          description: "A Claude-powered agent with tools and MCP support",
          config: {
            name: "my_agent",
            systemPrompt: "You are a helpful assistant.",
            model: "claude-sonnet-4-20250514",
            tools: [],
            mcpServers: [],
          },
        },
      },
    ],
    icon: <Bot className="w-4 h-4" />,
  },
  {
    title: "MCP Servers",
    type: "mcp-server" as ComponentTypes,
    items: [
      {
        label: "Stdio Server",
        config: {
          provider: "claude.mcp.StdioServer",
          component_type: "mcp-server",
          version: 1,
          label: "Stdio MCP Server",
          description: "Local command-based MCP server",
          config: {
            name: "my_mcp_server",
            serverType: "stdio",
            command: "npx",
            args: ["-y", "@modelcontextprotocol/server-example"],
          },
        },
      },
      {
        label: "SSE Server",
        config: {
          provider: "claude.mcp.SSEServer",
          component_type: "mcp-server",
          version: 1,
          label: "SSE MCP Server",
          description: "Remote streaming MCP server",
          config: {
            name: "my_sse_server",
            serverType: "sse",
            url: "https://example.com/sse",
          },
        },
      },
    ],
    icon: <Server className="w-4 h-4" />,
  },
  {
    title: "Built-in Tools",
    type: "tool" as ComponentTypes,
    items: [
      { label: "Bash", config: { name: "bash", toolType: "bash" } },
      { label: "File Read", config: { name: "file_read", toolType: "file_read" } },
      { label: "File Write", config: { name: "file_write", toolType: "file_write" } },
      { label: "Web Search", config: { name: "web_search", toolType: "web_search" } },
    ],
    icon: <Wrench className="w-4 h-4" />,
  },
], []);
```

### New AgentNode for Claude Agents

```typescript
// Source: nodes.tsx - Claude-oriented agent node
export const ClaudeAgentNode = memo<NodeProps<CustomNode>>((props) => {
  const component = props.data.component as Component<AgentConfig>;
  const config = component.config;

  const hasSystemPrompt = !!config.systemPrompt;
  const mcpServerCount = config.mcpServers?.length || 0;
  const builtInToolCount = config.tools?.length || 0;

  return (
    <BaseNode
      {...props}
      icon={iconMap.agent}
      headerContent={
        <div className="flex gap-2 mt-2">
          <ConnectionBadge
            connected={true}
            label={config.model || "claude-sonnet-4"}
          />
          <ConnectionBadge
            connected={mcpServerCount > 0}
            label={`${mcpServerCount} MCP`}
          />
          <ConnectionBadge
            connected={builtInToolCount > 0}
            label={`${builtInToolCount} Tools`}
          />
        </div>
      }
      descriptionContent={
        <div>
          <div className="break-words truncate mb-1">{config.name}</div>
          {hasSystemPrompt && (
            <div className="text-xs text-gray-500 truncate">
              {config.systemPrompt?.substring(0, 50)}...
            </div>
          )}
        </div>
      }
    >
      <Handle
        type="target"
        position={Position.Left}
        id={`${props.id}-agent-input-handle`}
        className="my-left-handle z-100"
      />

      {/* Model Selection (inline, not a separate node) */}
      <NodeSection title="Model">
        <div className="text-sm">{config.model || "claude-sonnet-4-20250514"}</div>
      </NodeSection>

      {/* MCP Servers */}
      <NodeSection title={`MCP Servers (${mcpServerCount})`}>
        <div className="space-y-1">
          {(config.mcpServers || []).map((serverRef, index) => (
            <div key={index} className="text-sm py-1 px-2 bg-white rounded flex items-center gap-2">
              <Server className="w-4 h-4 text-gray-500" />
              <span>{serverRef}</span>
            </div>
          ))}
          <DroppableZone id={`${props.id}@@@mcp-zone`} accepts={["mcp-server"]}>
            <div className="text-secondary text-xs my-1 text-center">
              Drop MCP server here
            </div>
          </DroppableZone>
        </div>
      </NodeSection>

      {/* Built-in Tools */}
      <NodeSection title={`Built-in Tools (${builtInToolCount})`}>
        <div className="space-y-1">
          {(config.tools || []).map((toolName, index) => (
            <div key={index} className="text-sm py-1 px-2 bg-white rounded flex items-center gap-2">
              <Wrench className="w-4 h-4 text-gray-500" />
              <span>{toolName}</span>
            </div>
          ))}
          <DroppableZone id={`${props.id}@@@tool-zone`} accepts={["tool"]}>
            <div className="text-secondary text-xs my-1 text-center">
              Drop tool here
            </div>
          </DroppableZone>
        </div>
      </NodeSection>
    </BaseNode>
  );
});
```

## State of the Art

| Old Approach (AutoGen) | Current Approach (Claude) | Impact |
|------------------------|---------------------------|--------|
| Team coordination models (Selector, Swarm, RoundRobin) | Subagent delegation | Simpler - agents spawn subagents as needed |
| Separate model nodes | Model as agent config field | Fewer node types, cleaner UI |
| Workbench wrapper for tools | Direct MCP server attachment | Simpler connection model |
| Termination conditions | Natural completion | No need for termination nodes |

**Claude Agent SDK Key Differences:**
- Models are internal configuration, not separate entities
- MCP servers are first-class citizens for tool provision
- Subagents are created by agents, not pre-configured in teams
- Built-in tools (bash, file ops, web search) are always available

## Open Questions

### 1. Workflow vs Team Naming

**What we know:** AutoGen calls groups "teams" with coordination. Claude SDK doesn't have this concept.
**What's unclear:** Should we keep "team" naming for backward compatibility, or rename to "workflow"?
**Recommendation:** Keep internal type as "team" for now (backward compat), but display as "Workflow" in UI. Rename in later phase.

### 2. Built-in Tool Toggles

**What we know:** Claude Agent SDK has built-in tools that are always available.
**What's unclear:** Should users explicitly enable/disable each built-in tool, or just have them all?
**Recommendation:** Add checkboxes in agent configuration for built-in tools, default all to enabled.

### 3. MCP Server Discovery

**What we know:** MCP servers provide tools dynamically.
**What's unclear:** How to show available tools from an MCP server in the canvas (they're discovered at runtime).
**Recommendation:** Show "Tools: Dynamic" for MCP servers. Implement tool preview in Phase 3.

### 4. Subagent Visualization

**What we know:** Claude agents can spawn subagents for specialized tasks.
**What's unclear:** Should subagents be visualized on canvas? They're created at runtime.
**Recommendation:** Defer to Phase 3. For now, subagent configuration is in agent's config, not a separate node.

## Sources

### Primary (HIGH confidence)
- PACO codebase analysis: `frontend/components/builder/*.tsx`, `frontend/types/*.ts`
- Phase 1 research: `.planning/phases/01-fork-port-foundation/01-RESEARCH.md`
- [Claude Agent SDK TypeScript Reference](https://platform.claude.com/docs/en/agent-sdk/typescript) - Complete type definitions and patterns

### Secondary (MEDIUM confidence)
- [React Flow Drag and Drop](https://reactflow.dev/examples/interaction/drag-and-drop) - Palette integration pattern
- [Next.js App Router Layouts](https://nextjs.org/docs/pages/building-your-application/routing/pages-and-layouts) - Layout pattern

### Tertiary (LOW confidence)
- Community patterns for sidebar + canvas layouts (verified against existing PACO code)

## Metadata

**Confidence breakdown:**
- Layout integration: HIGH - Direct pattern from existing PACO layouts
- Node type mapping: HIGH - Based on Claude Agent SDK official docs
- Component library: MEDIUM - Design decision, no external verification
- Edge rules: MEDIUM - Derived from Claude SDK concepts

**Research date:** 2026-02-03
**Valid until:** 30 days (stable patterns, no rapid changes expected)
