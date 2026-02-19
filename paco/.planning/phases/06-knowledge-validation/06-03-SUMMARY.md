# Phase 06-03 Summary: Workflow Validation

**Completed**: 2026-02-04

## What Was Built

### Validation System
- `validation/types.ts` - Type definitions:
  - `ValidationSeverity` ('error' | 'warning')
  - `ValidationError` with nodeId, nodeName, field, message, severity
  - `ValidationResult` with valid flag, errors array, warnings array

- `validation/rules.ts` - Validation logic:
  - `validateWorkflow()` - Main entry point, validates nodes and edges
  - `validateNode()` - Per-node validation based on component type
  - `validateConnections()` - Edge integrity and self-loop detection
  - `checkOrphanNodes()` - Finds disconnected nodes (warnings)

### Validation Rules
- **Agent nodes**: name required, model required
- **MCP Server nodes**: name required, command (stdio) or URL (sse/http) required
- **Knowledge nodes**: name required, at least one source required
- **Logic nodes**: name required, condition required for condition/loop types
- **Connections**: Detects missing source/target, prevents self-loops
- **Orphans**: Warns about nodes not connected to anything (except team root)

### ValidationErrors Component
- `validation-errors.tsx` - Non-blocking alert panel:
  - Shows error and warning counts
  - Lists all errors with red icons
  - Lists all warnings with amber icons
  - Clicking an error selects the corresponding node
  - Closable with X button
  - Positioned at bottom of canvas

### Builder Integration
- Validate button runs `validateWorkflow()` and shows results
- Save button runs validation (non-blocking, shows warning but saves)
- Validation panel renders when errors/warnings exist
- Clear validation on cleanup

## Files Created
- `frontend/components/builder/validation/types.ts`
- `frontend/components/builder/validation/rules.ts`
- `frontend/components/builder/validation/index.ts`
- `frontend/components/builder/validation-errors.tsx`

## Files Modified
- `frontend/components/builder/builder.tsx` - Validation integration

## Verification
- TypeScript compiles without errors
- Clicking Validate shows validation results
- Errors appear for missing required fields
- Warnings appear for disconnected nodes
- Clicking an error selects the relevant node
- Validation panel can be closed
