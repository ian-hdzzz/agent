# Phase 3: Claude Agent Node - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can configure a Claude agent's settings visually via a properties panel. This includes adding an agent node to the canvas, selecting it to reveal configuration options, and editing model, system prompt, and parameters. Changes persist in canvas state.

</domain>

<decisions>
## Implementation Decisions

### Panel layout
- Right sidebar for properties panel (like Figma, Linear, n8n)
- Fixed position, always visible when node selected
- Does not cover canvas

### System prompt editor
- Expandable textarea that grows as user types
- Character count displayed
- Clean and simple — no code editor complexity

### Model selection
- Dropdown with preset common models (Claude, GPT, etc.)
- "Custom" option to type any model string for any provider
- Support multi-provider models (not Claude-only)

### Parameters
- Extended parameter set visible:
  - Temperature
  - Max tokens
  - Top P
  - Top K
  - Stop sequences
- Fields appropriate for each type (sliders for 0-1 values, number inputs for tokens)

### Claude's Discretion
- Exact preset model list (research current models from providers)
- Default values for parameters
- Advanced settings collapse/expand behavior
- Validation timing and error display style

</decisions>

<specifics>
## Specific Ideas

- "Simple but powerful like the top agent SDK builders" — reference tools like n8n, Langflow, Flowise for UX patterns
- Multi-provider support is important — not Claude-only

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-claude-agent-node*
*Context gathered: 2026-02-03*
