# Feature Landscape: Visual Agent Builder

**Domain:** Visual agent builder for Claude Agent SDK
**Researched:** 2026-02-03
**Confidence:** MEDIUM

## Executive Summary

Visual agent builders have converged on a core set of table-stakes features. PACO's unique position—Claude-native with existing channel integrations (Chatwoot, ElevenLabs)—creates differentiation opportunities that pure-play builders lack.

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity |
|---------|--------------|------------|
| **Drag-and-drop canvas** | Core UX paradigm; every competitor has it | Medium |
| **Agent configuration node** | Users need to set model, temperature, system prompt | Low |
| **Tool/function nodes** | Agents need tools to be useful | Medium |
| **Connection lines between nodes** | Visual data flow is the whole point | Low |
| **Save/load workflows** | Users expect to not lose work | Low |
| **Preview/test chat** | Testing before deployment is essential | Medium |
| **Node properties panel** | Configure selected node without modal hell | Low |
| **Undo/redo** | Users make mistakes | Medium |
| **Workflow validation** | Prevent invalid configurations | Medium |

### Priority Ranking for Table Stakes

1. **Must ship in v1:** Canvas, agent config, tool nodes, save/load, test chat, properties panel
2. **Should ship in v1:** Undo/redo, validation, error display
3. **Can ship post-v1:** Copy/paste (users work around)

---

## Differentiators

Features that set PACO apart.

| Feature | Value Proposition | Complexity |
|---------|-------------------|------------|
| **Claude-native with MCP** | Only builder designed for Claude Agent SDK + MCP | High |
| **Native Chatwoot integration** | Deploy to customer service channels immediately | Medium |
| **Native ElevenLabs voice** | Voice agents from same canvas | Medium |
| **Code export to Claude SDK** | Generate deployable Python/TypeScript | High |
| **Knowledge base nodes (RAG)** | Document upload, URL scraping, vector search | High |
| **Conditional logic nodes** | If/else branching based on context | Medium |
| **Workflow templates** | Pre-built starting points | Low |
| **Real-time execution trace** | Watch agent "think" during test (Langfuse) | Medium |

### Differentiation Strategy

**Primary differentiators (must have for positioning):**
1. Claude-native with MCP — this is our unique value
2. Code export — vendor independence story
3. Chatwoot/ElevenLabs native — immediate deployment to channels

---

## Anti-Features

Features to deliberately NOT build.

| Anti-Feature | Why Avoid |
|--------------|-----------|
| **Visual code editor** | Leads to worst of both worlds |
| **Proprietary workflow format** | Lock-in reduces trust |
| **"No-code" messaging** | Attracts wrong audience |
| **Marketplace for agents** | Complex to moderate; security risks |
| **Real-time collaboration** | Extremely complex; v2 at earliest |
| **Custom LLM provider integration** | Spreads focus thin; Claude is primary value |
| **Mobile canvas editor** | Touch-based node editing is painful |

---

## MVP Recommendation

### Must Have (Table Stakes)
1. Drag-and-drop canvas with React Flow
2. Agent configuration node
3. MCP tool nodes
4. Save/load workflows to PostgreSQL
5. Test chat interface
6. Properties panel for node configuration

### Should Have (Basic Differentiation)
7. Code export (generate Claude Agent SDK code)
8. Deploy button (deploy via PM2)
9. Workflow validation

### Defer to Post-MVP
- Knowledge base nodes (RAG) — Phase 3
- Logic nodes (conditionals) — Phase 3
- Multi-agent orchestration — v2
- Version history — Phase 4

---
*Feature research: 2026-02-03*
