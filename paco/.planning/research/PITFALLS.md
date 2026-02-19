# Domain Pitfalls: Visual Agent Builder

**Domain:** Visual workflow/agent builder with React Flow
**Researched:** 2026-02-03
**Confidence:** MEDIUM

---

## Critical Pitfalls

### Pitfall 1: React Flow State vs React State Collision

**What goes wrong:** Mixing controlled (you manage state) and uncontrolled (React Flow manages state) modes causes sync issues, stale renders, and lost user changes.

**Warning signs:**
- Nodes snap back to original position after drag
- Saved workflow doesn't match what user sees

**Prevention:**
```typescript
// CORRECT: Fully controlled mode with Zustand
const { nodes, edges, onNodesChange, onEdgesChange } = useWorkflowStore();
<ReactFlow
  nodes={nodes}
  edges={edges}
  onNodesChange={onNodesChange}
  onEdgesChange={onEdgesChange}
/>
```

**Phase mapping:** Phase 1 (Canvas Foundation)

---

### Pitfall 2: Workflow Serialization Round-Trip Failures

**What goes wrong:** Custom node `data` contains non-serializable values (functions, React components).

**Prevention:**
- Define serializable schema upfront
- Validate round-trip in tests
- Schema version field for migrations

**Phase mapping:** Phase 2-3 (Persistence)

---

### Pitfall 3: Code Generation Complexity Explosion

**What goes wrong:** Code generation becomes exponentially complex as node types increase.

**Prevention:**
1. Template-based generation (not string concatenation)
2. Intermediate representation (Workflow -> IR -> Code)
3. Start with 4-6 node types, prove pattern works

**Phase mapping:** Phase 4 (Code Generation) — highest risk phase

---

### Pitfall 4: Node Connection Validation Gap

**What goes wrong:** React Flow allows any connection by default. Invalid workflows reach runtime.

**Prevention:**
```typescript
const isValidConnection = useCallback((connection) => {
  const sourceHandle = getHandle(connection.sourceHandle);
  const targetHandle = getHandle(connection.targetHandle);
  return targetHandle.accepts.includes(sourceHandle.type);
}, []);
<ReactFlow isValidConnection={isValidConnection} />
```

**Phase mapping:** Phase 1-2 (Canvas Foundation)

---

### Pitfall 5: Deployment State Machine Complexity

**What goes wrong:** UI gets out of sync with PM2 process state.

**Prevention:**
```typescript
type DeploymentState =
  | 'draft' | 'validating' | 'generating_code'
  | 'deploying' | 'running' | 'failed' | 'stopped';

// Disable UI actions based on current state
const canDeploy = ['draft', 'failed', 'stopped'].includes(state);
```

**Phase mapping:** Phase 5 (Deployment)

---

## Moderate Pitfalls

### Pitfall 6: React Flow Performance
- Memoize custom nodes
- Define nodeTypes outside component
- Isolate property panel state from canvas

### Pitfall 7: Undo/Redo Afterthought
- Design state for immutability from start
- Use immer for predictable updates

### Pitfall 8: Custom Node Styling Inconsistency
- Build shared NodeShell component
- Establish design system before individual nodes

### Pitfall 9: MCP Tool Discovery Fragility
- Validate tool references before save/deploy
- Check schema compatibility

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why Bad | Instead |
|--------------|---------|---------|
| Auto-connect nodes when dropped near handles | Users lose control | Show suggestions, require explicit action |
| Too many node types in v1 | Complexity explosion | Ship 4-6 core nodes first |
| Real-time collaboration early | CRDTs for graphs are research territory | Single-user with locking |
| Store React Flow state directly in DB | Library updates break saved workflows | Define your own schema |
| Generated code as only artifact | Users can't debug | Allow manual editing, track modifications |

---

## Phase-Specific Risk Summary

| Phase | Primary Risk | Mitigation |
|-------|--------------|------------|
| 1. Canvas Foundation | State management collision | Establish Zustand pattern day 1 |
| 2. Core Nodes | Connection validation gap | Build type system with first node |
| 3. Persistence | Serialization failures | Round-trip testing mandatory |
| 4. Code Generation | Complexity explosion | IR pattern, limited initial nodes |
| 5. Deployment | State machine complexity | Explicit state machine design |

---
*Pitfalls analysis: 2026-02-03*
