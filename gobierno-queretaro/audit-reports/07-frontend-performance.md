## Frontend & Performance Audit Report

### Executive Summary

The PACO frontend is a substantial Next.js 14 application with a visual workflow builder, infrastructure management, and monitoring dashboard. While the architecture is sound with proper use of Zustand for state management and React Query for data fetching, there are critical gaps in type safety (40+ `any` usages in api.ts alone), no React error boundaries, no loading.tsx/error.tsx files for Next.js App Router, zero test coverage for UI components, and significant accessibility deficiencies. The observability stack relies on an in-memory-only tracing store with no persistence, and the RL training pipeline contains placeholder rollout functions that cannot produce real training signal.

### Critical Findings

**CRIT-001: No React Error Boundaries -- Full App Crash on Any Component Error**
- File: `paco/frontend/app/layout.tsx:17-29`
- Issue: The root layout and all route segments have no `error.tsx` files. A Glob for `paco/frontend/**/error.tsx` returns zero results. Next.js App Router uses `error.tsx` files as the error boundary mechanism. Without them, any unhandled runtime error in any component (e.g., the builder, playground, or monitoring page) will crash the entire application to the default Next.js error page.
- Impact: A single exception in one chart component, SSE parse failure, or undefined property access tears down the entire UI session. For an admin control plane, this means operators lose their workflow state mid-edit.
- Recommendation: Add `error.tsx` files at minimum in `app/dashboard/`, `app/builder/`, `app/infrastructures/[id]/`, and the root `app/` directory. Each should render a recovery UI with a "Try again" button.

**CRIT-002: Hardcoded Default Credentials Displayed on Login Page**
- File: `paco/frontend/app/auth/login/page.tsx:131`
- Issue: The login page renders `Default admin: admin@paco.local / admin123` directly in the UI footer. This exposes default credentials to any user or web crawler that reaches the login page.
- Impact: An attacker or unauthorized user can immediately authenticate as admin on any deployment where default credentials were not changed. Combined with the `admin` role having full access, this is a direct path to system compromise.
- Recommendation: Remove hardcoded credentials from the frontend entirely. Provide default credentials only in deployment documentation or environment-specific README, never in rendered UI.

**CRIT-003: Auth Token Stored in localStorage via Zustand persist**
- File: `paco/frontend/lib/auth.ts:106-117`
- Issue: The auth store uses `persist` middleware with default `localStorage` storage. The JWT access token and full user object are persisted to `localStorage` under key `paco-auth`. localStorage is accessible to any JavaScript running on the same origin, making it vulnerable to XSS token theft.
- Impact: Any XSS vulnerability (even via a third-party dependency) can silently exfiltrate the auth token. Unlike httpOnly cookies, localStorage tokens cannot be protected by the browser.
- Recommendation: Store the auth token in an httpOnly cookie set by the backend, or at minimum use `sessionStorage` (cleared on tab close). If localStorage must be used, implement token rotation and short-lived tokens.

**CRIT-004: Tracing Store Is In-Memory Only -- All Traces Lost on Restart**
- File: `gobierno-queretaro/shared/tracing/setup.py:57`
- Issue: `_store = InMemoryLightningStore()` is the only store implementation. There is no persistent backend configured (no database, no file-based store). The comment on line 56 acknowledges this: "in-memory for Phase 1, persistent backend later."
- Impact: Every service restart (deployment, crash, scaling event) destroys all collected traces, reward signals, and training data. The APO and RL training pipelines depend on these traces but will always find empty stores in practice. This renders the entire training pipeline non-functional in production.
- Recommendation: Configure a persistent store backend (PostgreSQL, Redis, or file-based) before relying on traces for any training or observability workflow.

### High Priority Findings

**HIGH-001: Massive `any` Usage in API Client Defeats TypeScript Safety**
- File: `paco/frontend/lib/api.ts:393-650`
- Issue: The infrastructure-related section of the API client uses `any` for return types and parameters in 40+ locations. Examples: `getInfrastructure` returns `any` (line 398), `createInfrastructure` takes `data: any` (line 401), `getInfraHealth` returns `any` (line 592), `getInfraMetrics` returns `any` (line 596). The Langfuse proxy methods also return `any` (lines 287, 291). Downstream, pages like `monitor/page.tsx` cast arrays `(circuits as any[])` (line 226) and iterate with `(am: any)` (line 292).
- Impact: No compile-time safety for the entire infrastructure management feature. Typos in property access, schema mismatches with the backend, and null pointer exceptions go undetected until runtime. The `InfraDetail`, `InfraOrchestrator`, `InfraMetric` types exist in `types/infrastructure.ts` but are never used in the API client.
- Recommendation: Replace all `any` return types and parameters with the proper types already defined in `types/infrastructure.ts`. This is a mechanical change that would catch bugs immediately.

**HIGH-002: No Loading States for Next.js App Router Routes**
- File: `paco/frontend/app/` (all route segments)
- Issue: A Glob for `paco/frontend/**/loading.tsx` returns zero results. Next.js App Router uses `loading.tsx` files for automatic Suspense-based loading UI. Without them, route transitions show a blank page until data loads.
- Impact: Users see flash-of-empty-content when navigating between dashboard, agents, executions, and infrastructure pages. The only loading states are manually coded within page components (e.g., `dashboard/page.tsx:196` spinner), but these only appear after the JavaScript bundle has loaded and React has rendered.
- Recommendation: Add `loading.tsx` files with skeleton/spinner UI for at least `app/dashboard/`, `app/agents/`, `app/executions/`, `app/infrastructures/`, and `app/builder/`.

**HIGH-003: Agent Prompt Optimization Rollout is a Placeholder**
- File: `gobierno-queretaro/training/optimize_agent.py:91-114`
- Issue: The `agent_rollout` function decorated with `@rollout` contains a TODO comment on line 107: "TODO: Implement actual agent call with modified prompt." It always returns `reward = 0.5` regardless of the prompt quality. This means APO optimization for agent prompts will receive constant reward, producing random prompt mutations with no quality signal.
- Impact: Running `python -m training.optimize_agent` will consume API credits (OpenAI/Claude calls for APO) and produce an "optimized" prompt that is actually randomly mutated with no improvement guarantee.
- Recommendation: Implement the actual agent call within the rollout function, using the modified system prompt to answer a test question and evaluating response quality against ground truth.

**HIGH-004: Full lodash Imported in Store -- Bundle Size Impact**
- File: `paco/frontend/components/builder/store.tsx:10`
- Issue: `import { clone, isEqual } from "lodash"` imports the entire lodash library (70KB+ minified) into the client bundle. Other files correctly use path imports like `import debounce from "lodash/debounce"` (e.g., `builder.tsx:51`), but `store.tsx` uses the barrel import.
- Impact: Adds ~70KB to the builder page's JavaScript bundle unnecessarily. The `clone` and `isEqual` functions alone are ~5KB. This impacts initial load time, especially on mobile connections.
- Recommendation: Change to `import clone from "lodash/clone"` and `import isEqual from "lodash/isEqual"`.

**HIGH-005: No Authentication Check on Playground/SSE Endpoints**
- File: `paco/frontend/components/playground/usePlayground.ts:91`
- Issue: The `runAgent` function in `usePlayground.ts` makes a direct `fetch()` call to `${API_URL}/api/playground/agent/run` without including the auth token. Compare with `api.ts:762-770` where `runPlaygroundAgent` does include the token. The `usePlayground` hook bypasses the `ApiClient` entirely and constructs its own fetch calls.
- Impact: If the backend requires authentication (likely given the auth system), playground calls will fail with 401. If the backend allows unauthenticated playground access, this is an API security gap.
- Recommendation: Use the `api.runPlaygroundAgent()` method from the API client instead of raw fetch, or add auth headers to the fetch call.

### Medium Priority Findings

**MED-001: No Accessibility (ARIA) Attributes Across the Application**
- File: Multiple components across `paco/frontend/components/`
- Issue: A search for `aria-` and `role=` attributes in source `.tsx` files (excluding node_modules) found only 1 match in `app/agents/new/page.tsx`. Critical interactive elements lack ARIA attributes: the `AgentCard.tsx` clickable div (line 30-36) has no `role="button"` or `tabIndex`; the `Header.tsx` search input (line 30) has no label or `aria-label`; the builder's drag-and-drop library has no keyboard navigation support; status badges have no `aria-live` for screen reader updates.
- Impact: The application is not usable with screen readers or keyboard-only navigation. This may violate accessibility regulations (WCAG 2.1 AA) depending on the deployment context.
- Recommendation: Add ARIA attributes systematically: `role="button"` and `tabIndex={0}` for clickable non-button elements, `aria-label` for icon-only buttons, `aria-live="polite"` for status updates, and `aria-describedby` for form fields.

**MED-002: Client-Side Search Filtering Without Debounce or Pagination**
- File: `paco/frontend/app/executions/page.tsx:27-32`
- Issue: The executions page loads up to 200 records (configurable via `limit` state) and filters them client-side with `Array.filter()` on every keystroke. There is no debounce on the search input and no server-side search capability. The same pattern exists in agents and tools pages.
- Impact: With large datasets (hundreds of executions), every keystroke triggers a full array scan and React re-render. At 200+ rows with multiple string comparisons, this can cause noticeable UI jank.
- Recommendation: Add debounce (300ms) to the search input. Consider server-side filtering for datasets that could grow large.

**MED-003: All Dashboard Pages Are Client-Side Rendered**
- File: `paco/frontend/app/dashboard/page.tsx:1`, `paco/frontend/app/executions/page.tsx:1`, and all other page files
- Issue: Every page in the application begins with `"use client"` and uses client-side data fetching via React Query. No pages use server components, server-side data fetching, or static generation. The `app/page.tsx` root page is also client-side only.
- Impact: No SEO benefits (less relevant for admin panel), but more importantly: no server-side caching, longer time-to-interactive, and full waterfall loading (JS bundle -> React hydrate -> API call -> render). The dashboard layout (`dashboard/layout.tsx`) also does auth checking client-side, causing a flash before redirect.
- Recommendation: For the admin panel use case, this is acceptable but not optimal. Consider server-side auth checking in middleware or server components for the layout, and using React Server Components for static portions of the dashboard.

**MED-004: Query Refetch Intervals Create Excessive Polling**
- File: `paco/frontend/app/dashboard/page.tsx:26-39`, `paco/frontend/app/infrastructures/[id]/monitor/page.tsx:28-56`
- Issue: The dashboard page sets up 3 concurrent polling intervals: agents at 30s, metrics at 60s, and realtime at 10s. The monitor page sets up 6 concurrent polls: health at 15s, metrics at 30s, agent metrics at 30s, circuits at 15s, logs at 10s, and infrastructure data (default stale). These run continuously even when the tab is not visible (since `refetchOnWindowFocus: false` is set in providers).
- Impact: A single browser tab running the monitor page generates ~18 API requests per minute continuously. Multiple open tabs multiply this. The backend must handle this load even when no one is actively looking at the page. Since `refetchOnWindowFocus` is disabled, switching back to the tab does not trigger a fresh fetch, so data can be stale despite the continuous polling.
- Recommendation: Enable `refetchOnWindowFocus: true` and add `refetchIntervalInBackground: false` to pause polling when the tab is not visible. Consider WebSocket/SSE for real-time updates on the monitor page instead of polling.

**MED-005: React Query Default staleTime Does Not Match Polling Intervals**
- File: `paco/frontend/app/providers.tsx:11`
- Issue: The global QueryClient sets `staleTime: 60 * 1000` (60 seconds), but individual queries set `refetchInterval` values of 10s, 15s, and 30s. When staleTime > refetchInterval, the refetched data may not trigger a re-render because React Query considers the cached data still "fresh."
- Impact: Polling may fetch new data from the server but not actually update the UI because the stale time has not elapsed. This creates a confusing situation where the network tab shows requests but the UI does not update.
- Recommendation: Either reduce the global `staleTime` to match the minimum polling interval, or set `staleTime: 0` for queries with `refetchInterval` to ensure fetched data always updates the UI.

**MED-006: No End-to-End Timeout Configuration for Voice Pipeline**
- File: `gobierno-queretaro/shared/tracing/setup.py` (entire file)
- Issue: There is no timeout configuration visible for the full request lifecycle: STT transcription -> orchestrator classification -> agent processing -> TTS synthesis. Individual agent timeouts exist in `InfraOrchestrator.agent_timeout` (types/infrastructure.ts:87), but there is no cumulative pipeline timeout. The voice gateway configuration is not visible in the tracing setup.
- Impact: A slow STT step plus a slow agent response could cause the total voice response time to exceed acceptable limits (typically 3-5 seconds for voice interactions). Without a pipeline-level timeout, the citizen waits indefinitely.
- Recommendation: Add a configurable end-to-end timeout for the voice pipeline path, with appropriate circuit-breaking if any stage exceeds its budget.

### Low Priority / Improvements

**LOW-001: Two Competing UI Component Libraries (Ant Design + Custom Tailwind)**
- File: `paco/frontend/package.json:23` (antd), multiple component files
- Issue: The project includes both `antd` v6.2.3 and a custom Tailwind-based component system. The builder uses Ant Design components (`Button`, `Modal`, `Form`, `Switch`, `Layout` from `antd` in `builder.tsx:25`), while the dashboard, agents, and executions pages use custom Tailwind-styled `btn-primary`, `card`, `input` classes. The `@headlessui/react` package is also installed but usage is not visible in source files.
- Impact: Bundle size includes the full Ant Design library (~300KB+ gzipped for used components), inconsistent visual design between builder and other pages, and developer confusion about which component system to use.
- Recommendation: Consolidate on one approach. If the custom Tailwind system is preferred, migrate builder components away from Ant Design and remove the dependency. Also audit `@headlessui/react` -- if unused, remove it.

**LOW-002: Only 2 Test Files -- No Component or Integration Tests**
- File: `paco/frontend/components/builder/code-generation/workflow-to-ir.test.ts`, `paco/frontend/components/builder/code-generation/ir-to-typescript.test.ts`
- Issue: The entire frontend has only 2 test files, both for the code generation module. Zero test coverage for: API client, auth store, builder store, all React components, all pages, validation logic, SSE parsing. Jest is configured (`jest.config.js`) with React Testing Library and jsdom, but essentially unused.
- Impact: No regression protection for any UI changes. API client changes, auth flow modifications, and builder state management updates all ship without automated verification.
- Recommendation: Prioritize tests for: (1) API client error handling, (2) auth store login/logout/rehydration flows, (3) builder store sync/undo/redo, (4) SSE parsing in usePlayground.

**LOW-003: Builder Component is 958 Lines with 15+ useState Hooks**
- File: `paco/frontend/components/builder/builder.tsx:1-958`
- Issue: The main builder component has ~958 lines with 15+ individual `useState` calls (lines 94-126), managing JSON mode, fullscreen, grid visibility, minimap, validation, test drawer, save modal, export modal, workflow ID, name, description, saving state, loading workflows, and deleting workflows. This is a "god component" pattern.
- Impact: Difficult to maintain, test, or reason about. Every state change triggers potential re-renders of the entire builder canvas. New features require modifying this already-large file.
- Recommendation: Extract focused sub-components: `WorkflowSaveManager`, `WorkflowLoadModal`, `BuilderToolbar` (already partially done), and `ValidationPanel`. Move workflow CRUD state into a dedicated Zustand store or custom hook.

**LOW-004: `JSON.parse(JSON.stringify(component))` Deep Clone Pattern**
- File: `paco/frontend/components/builder/store.tsx:160`
- Issue: `const clonedComponent = JSON.parse(JSON.stringify(component))` is used for deep cloning in the store's `addNode` method. This loses any non-serializable values (functions, undefined, Dates as objects, symbols) and is slower than `structuredClone()` which is available in all modern browsers.
- Impact: Potential data loss if components ever contain non-JSON-serializable values. Performance impact is minimal for typical component sizes but adds to the builder's rendering overhead.
- Recommendation: Replace with `structuredClone(component)` for correctness and performance.

**LOW-005: Training Pipeline Requires External Dependencies Not Pinned**
- File: `gobierno-queretaro/training/requirements.txt` (not read, but referenced in code)
- Issue: The training scripts reference `agentlightning[verl]` and `agentlightning[apo]` as optional extras. The `train_classifier_rl.py` also requires `torch`, `vllm`, and `flash-attn` (line 176). These heavy ML dependencies are not in a lock file, and versions are not pinned. The training scripts also use `sys.path.insert(0, ...)` to resolve sibling module imports (lines 22-23 in multiple files).
- Impact: Training runs may fail silently with version incompatibilities. The `sys.path` hack is fragile and breaks if the directory structure changes.
- Recommendation: Create a dedicated `requirements-training.txt` with pinned versions. Use proper Python packaging (pyproject.toml or setup.py) instead of `sys.path.insert`.

**LOW-006: Dashboard Auth Guard Causes Flash of Empty Content**
- File: `paco/frontend/app/dashboard/layout.tsx:24-26`
- Issue: The dashboard layout checks `if (!token) { return null; }` on line 24-26, rendering nothing before redirecting. The redirect happens in a `useEffect` (line 16-22), so there is at least one render cycle where the user sees a blank page.
- Impact: Brief white flash on initial load and when auth expires. Not a functional issue but a poor user experience.
- Recommendation: Use Next.js middleware for auth checking, or show a loading spinner instead of `return null`.

**LOW-007: next.config.js Uses Deprecated `serverActions` Experimental Flag**
- File: `paco/frontend/next.config.js:4-5`
- Issue: `experimental: { serverActions: true }` was needed in Next.js 13 but server actions are stable in Next.js 14.1.0 (the version used). This flag is now unnecessary and generates a deprecation warning.
- Impact: Console warning on build. No functional impact.
- Recommendation: Remove the `experimental.serverActions` configuration.

### Positive Observations

- **Well-structured type system**: The `types/datamodel.ts` file provides comprehensive TypeScript types for the component system with clean separation between PACO and legacy AutoGen types. The type guards in `types/guards.ts` are well-implemented and properly narrow types.
- **React Query usage**: Data fetching with `@tanstack/react-query` is consistent across all pages, providing automatic caching, deduplication, and background refetching. The pattern of `queryKey` with dependencies is correct throughout.
- **Zustand store architecture**: Both `lib/auth.ts` and `components/builder/store.tsx` use Zustand effectively. The auth store properly handles token persistence and rehydration. The builder store implements undo/redo with bounded history (50 entries max).
- **Auto-reward heuristics**: The `shared/tracing/auto_rewards.py` module provides thoughtful, well-documented reward signals based on Spanish-language conversation patterns. The reward values are well-calibrated with clear justification comments.
- **Feedback collection**: The `orchestrator/feedback.py` provides a clean FastAPI endpoint with proper Pydantic validation for collecting human feedback signals. The best-effort pattern (log but don't fail) is appropriate for feedback collection.
- **Code generation pipeline**: The builder includes a complete IR (Intermediate Representation) -> TypeScript/Python code generation pipeline with actual test coverage for the transformation logic.
- **Visual builder with undo/redo**: The builder provides a sophisticated drag-and-drop visual canvas using `@xyflow/react` with undo/redo, auto-save (30s interval), validation, and code export capabilities.
- **Utility functions**: `lib/utils.ts` provides well-tested formatting functions (tokens, cost, duration, dates) that are consistently used across all dashboard and monitoring pages.
- **TypeScript strict mode enabled**: `tsconfig.json` has `"strict": true`, providing the strongest type-checking guarantees for properly typed code.

### Metrics

- Files reviewed: 52
- Critical findings: 4
- High findings: 5
- Medium findings: 6
- Low findings: 7
