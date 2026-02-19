---
phase: 04-persistence
plan: 02
subsystem: frontend
tags: [api-client, workflow, save-load, modal, react-flow]

dependency-graph:
  requires:
    - 04-01 (workflow API endpoints)
  provides:
    - workflow save functionality with modal
    - workflow load from URL parameter
    - workflow API client methods
  affects:
    - 04-03 (auto-save will use these methods)

tech-stack:
  added: []
  patterns:
    - URL-based workflow routing (/builder?id=xxx)
    - Suspense boundary for useSearchParams
    - Modal-based save for new workflows

key-files:
  created: []
  modified:
    - frontend/lib/api.ts
    - frontend/components/builder/builder.tsx
    - frontend/app/builder/page.tsx

decisions:
  - id: url-workflow-id
    context: How to persist workflow context across page refreshes
    choice: URL query parameter (/builder?id=xxx)
    rationale: Standard web pattern, enables sharing, bookmarking, browser history

  - id: modal-for-new-save
    context: UX for first save of a new workflow
    choice: Modal dialog asking for name/description
    rationale: Prevents save without name, matches common SaaS patterns

  - id: suspense-for-search-params
    context: Next.js App Router requires Suspense for useSearchParams
    choice: Wrap BuilderContent in Suspense with loading fallback
    rationale: Next.js 14+ requirement, prevents hydration errors

metrics:
  duration: 20 min
  completed: 2026-02-04
---

# Phase 4 Plan 02: Canvas Save/Load API Connection Summary

Frontend workflow save/load connected to backend API with modal-based new workflow creation and URL-based workflow loading.

## What Was Built

### 1. Workflow API Client Methods (frontend/lib/api.ts)

Added complete CRUD methods to the ApiClient:

```typescript
// Types
interface Workflow {
  id: string;
  name: string;
  description: string | null;
  config: Record<string, any>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

// Methods
async getWorkflows(): Promise<Workflow[]>
async getWorkflow(id: string): Promise<Workflow>
async createWorkflow(data: CreateWorkflowRequest): Promise<Workflow>
async updateWorkflow(id: string, data: UpdateWorkflowRequest): Promise<Workflow>
async deleteWorkflow(id: string): Promise<void>
```

### 2. Save Workflow Modal (frontend/components/builder/builder.tsx)

Updated TeamBuilder component with:

- `workflowId` prop for tracking current workflow
- Save modal with name/description fields for new workflows
- Direct API update for existing workflows
- URL update after first save (`/builder?id=xxx`)
- Loading state on save button

```typescript
interface TeamBuilderProps {
  team: Team;
  workflowId?: string | null;  // NEW
  onChange?: (team: Partial<Team>) => void;
  onDirtyStateChange?: (isDirty: boolean) => void;
  selectedGallery?: Gallery | null;
}
```

### 3. Workflow Loading (frontend/app/builder/page.tsx)

Updated builder page with:

- URL query parameter reading via `useSearchParams`
- Workflow fetching from API when ID present
- Loading and error state handling
- Workflow-to-Team conversion for builder
- Suspense boundary for Next.js compatibility

## Data Flow

```
[New Workflow]
User creates canvas -> Clicks Save -> Modal appears -> Enters name
-> api.createWorkflow() -> URL updates to /builder?id=xxx

[Load Existing]
User navigates to /builder?id=xxx -> api.getWorkflow() -> Team loaded into canvas

[Update Existing]
User modifies canvas -> Clicks Save -> api.updateWorkflow() -> Success message
```

## Key Implementation Details

### Save Logic Flow

```typescript
const handleSave = async () => {
  const component = syncToJson();

  // New workflow - show modal
  if (!workflowId) {
    setSaveModalVisible(true);
    return;
  }

  // Existing workflow - update directly
  await api.updateWorkflow(workflowId, { config: component });
  resetHistory();
  messageApi.success("Workflow saved");
};
```

### Workflow Loading

```typescript
useEffect(() => {
  if (workflowId) {
    setLoading(true);
    api.getWorkflow(workflowId)
      .then(setWorkflow)
      .catch((err) => setError(err.detail || 'Failed to load workflow'))
      .finally(() => setLoading(false));
  }
}, [workflowId]);
```

## Commits

| Commit | Description |
|--------|-------------|
| bd99645 | feat(04-02): add workflow CRUD methods to API client |
| 2137f2b | feat(04-02): add save workflow modal to builder |
| aee1984 | feat(04-02): add workflow loading to builder page |

## Verification Checklist

- [x] `frontend/lib/api.ts` has workflow CRUD methods
- [x] Builder shows save modal when saving new workflow
- [x] Existing workflow updates directly on save
- [x] `/builder?id=xxx` loads workflow from database
- [x] URL updates after first save to include workflow ID

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Plan 04-03 (auto-save) can now use:
- `api.updateWorkflow()` for periodic saves
- `workflowId` state to determine if auto-save is enabled
- `syncToJson()` to get current canvas state
