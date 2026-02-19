# Phase 7: Code Generation - Research

**Researched:** 2026-02-04
**Domain:** Code generation from visual workflows to Claude Agent SDK (Python/TypeScript)
**Confidence:** HIGH

## Summary

This phase transforms visual workflow designs into deployable Claude Agent SDK code in both Python and TypeScript. The research covers the Claude Agent SDK APIs, code generation patterns, templating approaches, and UI components for code preview/export.

The Claude Agent SDK provides a unified interface for building AI agents in both Python and TypeScript, with nearly identical APIs. Code generation requires an intermediate representation (IR) that abstracts the visual workflow into a language-agnostic structure, then language-specific templates render the final code.

The standard approach is: **Visual Workflow (React Flow nodes/edges) -> Intermediate Representation (JSON/TypeScript interface) -> Language Templates (Jinja2 for Python, Template Literals for TypeScript) -> Generated Code**. Monaco Editor provides the industry-standard code preview component.

**Primary recommendation:** Use a strongly-typed IR based on PACO's existing datamodel.ts types, with Jinja2 templates (Python backend) generating Python SDK code and TypeScript template literals (frontend) generating TypeScript SDK code. Monaco Editor for code preview with syntax highlighting.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | 3.1+ | Python template engine | Industry standard for Python code generation, used by Flask, Ansible, Sphinx |
| @monaco-editor/react | 4.6+ | Code editor component | Powers VS Code, industry standard for browser-based code editing |
| claude-agent-sdk | latest | Python SDK target | Official Anthropic SDK for Python agents |
| @anthropic-ai/claude-agent-sdk | latest | TypeScript SDK target | Official Anthropic SDK for TypeScript agents |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| js-beautify | 1.14+ | JavaScript/TypeScript formatting | Format generated TypeScript code |
| black | 24.0+ | Python formatting | Format generated Python code (backend) |
| file-saver | 2.0+ | File download in browser | Export code files from frontend |
| jszip | 3.10+ | Create zip archives | Bundle multiple files (code + requirements) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Jinja2 | Mako, Cheetah | Jinja2 is most widely used, best documented |
| Monaco Editor | CodeMirror 6, Prism | Monaco has richer features, but larger bundle |
| Template literals | Handlebars (TS) | Template literals are native, no extra dependency |

**Installation:**

Backend (Python):
```bash
pip install Jinja2 black
```

Frontend:
```bash
npm install @monaco-editor/react file-saver jszip @types/file-saver
```

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── components/builder/
│   ├── code-generation/
│   │   ├── index.ts                  # Public API
│   │   ├── ir.ts                     # Intermediate representation types
│   │   ├── workflow-to-ir.ts         # Convert workflow to IR
│   │   ├── ir-to-typescript.ts       # Generate TypeScript from IR
│   │   └── code-preview.tsx          # Monaco-based preview component
│   └── export/
│       ├── export-modal.tsx          # Export dialog
│       └── download-utils.ts         # File download helpers
backend/
├── app/
│   └── api/
│       └── codegen.py               # Code generation endpoints
└── templates/
    └── agent/
        ├── python/
        │   ├── agent.py.j2          # Main agent template
        │   ├── mcp_config.py.j2     # MCP server config template
        │   └── requirements.txt.j2   # Dependencies template
        └── typescript/
            ├── agent.ts.j2          # TypeScript template (optional, prefer frontend)
            └── package.json.j2       # Dependencies template
```

### Pattern 1: Intermediate Representation (IR)

**What:** A language-agnostic data structure representing the workflow that can be transformed into any target language.

**When to use:** Always. Never generate code directly from React Flow nodes.

**Example:**
```typescript
// Source: Based on PACO datamodel.ts and Claude Agent SDK patterns
interface WorkflowIR {
  name: string;
  description?: string;

  // Agent configuration
  agent: {
    name: string;
    model: string;
    systemPrompt?: string;
    temperature?: number;
    maxTokens?: number;
    topP?: number;
    topK?: number;
    stopSequences?: string[];
  };

  // MCP servers from connected nodes
  mcpServers: {
    name: string;
    type: 'stdio' | 'sse' | 'http';
    command?: string;
    args?: string[];
    url?: string;
    env?: Record<string, string>;
    enabledTools: string[];
  }[];

  // Built-in tools enabled
  allowedTools: string[];

  // Permission mode
  permissionMode: 'default' | 'acceptEdits' | 'bypassPermissions' | 'plan';

  // Knowledge sources (for documentation/context)
  knowledgeSources?: {
    name: string;
    type: 'document' | 'url';
    sources: string[];
  }[];
}
```

### Pattern 2: Workflow to IR Transformation

**What:** Pure function that converts React Flow state to IR.

**When to use:** Before any code generation.

**Example:**
```typescript
// Source: Pattern derived from React Flow + PACO datamodel.ts
import { Node, Edge } from 'reactflow';
import { WorkflowIR } from './ir';
import { Component, AgentConfig, McpServerConfig } from '@/types/datamodel';
import { isAgentComponent, isMcpServerComponent } from '@/types/guards';

export function workflowToIR(
  nodes: Node[],
  edges: Edge[],
  workflowName: string,
  workflowDescription?: string
): WorkflowIR {
  // Find the agent node (should be exactly one)
  const agentNode = nodes.find(n =>
    isAgentComponent(n.data.component)
  );

  if (!agentNode) {
    throw new Error('Workflow must have exactly one agent node');
  }

  const agentConfig = agentNode.data.component.config as AgentConfig;

  // Find connected MCP server nodes via edges
  const mcpEdges = edges.filter(e =>
    e.target === agentNode.id &&
    e.data?.connectionType === 'mcp'
  );

  const mcpServers = mcpEdges.map(edge => {
    const mcpNode = nodes.find(n => n.id === edge.source);
    if (!mcpNode || !isMcpServerComponent(mcpNode.data.component)) {
      return null;
    }
    const config = mcpNode.data.component.config as McpServerConfig;
    return {
      name: config.name || mcpNode.data.component.label || 'mcp-server',
      type: config.serverType || 'stdio',
      command: config.command,
      args: config.args,
      url: config.url,
      env: config.env,
      enabledTools: config.enabledTools || []
    };
  }).filter(Boolean);

  return {
    name: workflowName,
    description: workflowDescription,
    agent: {
      name: agentConfig.name,
      model: agentConfig.model || 'claude-sonnet-4-20250514',
      systemPrompt: agentConfig.systemPrompt,
      temperature: agentConfig.temperature,
      maxTokens: agentConfig.maxTokens,
      topP: agentConfig.topP,
      topK: agentConfig.topK,
      stopSequences: agentConfig.stopSequences
    },
    mcpServers,
    allowedTools: agentConfig.tools || [],
    permissionMode: 'acceptEdits' // Default for generated agents
  };
}
```

### Pattern 3: TypeScript Code Generation (Frontend)

**What:** Generate TypeScript Agent SDK code using template literals.

**When to use:** Frontend-side generation for instant preview without API call.

**Example:**
```typescript
// Source: Claude Agent SDK TypeScript documentation
import { WorkflowIR } from './ir';

export function generateTypeScriptCode(ir: WorkflowIR): string {
  const mcpServersCode = ir.mcpServers.length > 0
    ? generateMcpServersConfig(ir.mcpServers)
    : '';

  const allowedToolsCode = generateAllowedTools(ir);

  return `import { query } from "@anthropic-ai/claude-agent-sdk";

/**
 * ${ir.name}
 * ${ir.description || 'Generated by PACO Visual Agent Builder'}
 */

async function main() {
  for await (const message of query({
    prompt: "YOUR_PROMPT_HERE",
    options: {
      ${ir.agent.systemPrompt ? `systemPrompt: \`${escapeTemplateString(ir.agent.systemPrompt)}\`,` : ''}
      ${ir.agent.model ? `model: "${ir.agent.model}",` : ''}
      ${ir.agent.temperature !== undefined ? `// Note: temperature not directly supported, use model defaults` : ''}
      ${allowedToolsCode}
      ${mcpServersCode}
      permissionMode: "${ir.permissionMode}"
    }
  })) {
    if (message.type === "assistant") {
      for (const block of message.message?.content || []) {
        if ("text" in block) {
          console.log(block.text);
        }
      }
    }
    if (message.type === "result" && message.subtype === "success") {
      console.log("\\nTask completed:", message.result);
    }
  }
}

main().catch(console.error);
`;
}

function generateMcpServersConfig(servers: WorkflowIR['mcpServers']): string {
  if (servers.length === 0) return '';

  const serversObj = servers.map(s => {
    if (s.type === 'stdio') {
      return `        "${s.name}": {
          command: "${s.command}",
          args: ${JSON.stringify(s.args || [])}${s.env ? `,
          env: ${JSON.stringify(s.env)}` : ''}
        }`;
    } else {
      return `        "${s.name}": {
          type: "${s.type}",
          url: "${s.url}"
        }`;
    }
  }).join(',\n');

  return `mcpServers: {
${serversObj}
      },`;
}

function generateAllowedTools(ir: WorkflowIR): string {
  const tools: string[] = [...(ir.allowedTools || [])];

  // Add MCP tool wildcards
  for (const server of ir.mcpServers) {
    if (server.enabledTools.length > 0) {
      tools.push(...server.enabledTools.map(t => `mcp__${server.name}__${t}`));
    } else {
      tools.push(`mcp__${server.name}__*`);
    }
  }

  if (tools.length === 0) return '';
  return `allowedTools: ${JSON.stringify(tools)},`;
}

function escapeTemplateString(str: string): string {
  return str.replace(/`/g, '\\`').replace(/\$/g, '\\$');
}
```

### Pattern 4: Python Code Generation (Backend with Jinja2)

**What:** Generate Python Agent SDK code using Jinja2 templates on backend.

**When to use:** When user requests Python export (API call to backend).

**Jinja2 Template (agent.py.j2):**
```python
{# Source: Claude Agent SDK Python documentation #}
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions
{% if ir.mcpServers %}
{% endif %}

"""
{{ ir.name }}
{{ ir.description or 'Generated by PACO Visual Agent Builder' }}
"""

async def main():
    options = ClaudeAgentOptions(
        {% if ir.agent.systemPrompt %}
        system_prompt="""{{ ir.agent.systemPrompt | replace('"""', '\\"\\"\\"') }}""",
        {% endif %}
        {% if ir.agent.model %}
        model="{{ ir.agent.model }}",
        {% endif %}
        {% if allowed_tools %}
        allowed_tools={{ allowed_tools | tojson }},
        {% endif %}
        {% if ir.mcpServers %}
        mcp_servers={
            {% for server in ir.mcpServers %}
            "{{ server.name }}": {
                {% if server.type == 'stdio' %}
                "command": "{{ server.command }}",
                "args": {{ server.args | tojson }},
                {% if server.env %}
                "env": {{ server.env | tojson }},
                {% endif %}
                {% else %}
                "type": "{{ server.type }}",
                "url": "{{ server.url }}",
                {% endif %}
            },
            {% endfor %}
        },
        {% endif %}
        permission_mode="{{ ir.permissionMode }}"
    )

    async for message in query(
        prompt="YOUR_PROMPT_HERE",
        options=options
    ):
        if hasattr(message, 'content'):
            for block in message.content:
                if hasattr(block, 'text'):
                    print(block.text)
        elif hasattr(message, 'result'):
            print(f"\nTask completed: {message.result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Anti-Patterns to Avoid

- **Direct string concatenation:** Never build code with `+` operators. Use structured templates.
- **Generating from React Flow directly:** Always transform to IR first for clean separation.
- **Frontend Python generation:** Use Jinja2 on backend for proper Python code formatting.
- **Hardcoding SDK patterns:** Keep SDK patterns in templates, not scattered in code.
- **Missing escaping:** Always escape user strings in generated code (quotes, backticks).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Code editor UI | Custom textarea with highlighting | Monaco Editor | Syntax highlighting, autocomplete, error markers, folding |
| Python formatting | Manual indentation | black library | Consistent formatting, handles edge cases |
| TypeScript formatting | Manual formatting | js-beautify or prettier | Professional output |
| File download | Manual blob creation | file-saver library | Cross-browser compatibility |
| Multi-file export | Multiple downloads | jszip | Single download, better UX |
| Template rendering | Custom string replacement | Jinja2 (Python) | Loops, conditionals, filters, escaping |

**Key insight:** Code generation is deceptively complex. User input can break generated code through injection, improper escaping, or edge cases. Libraries handle these systematically.

## Common Pitfalls

### Pitfall 1: Template Injection / Code Injection

**What goes wrong:** User input (system prompts, names) contains characters that break generated code (quotes, backticks, newlines).

**Why it happens:** Developers forget that user strings appear in generated code.

**How to avoid:**
- Always escape user strings appropriately for target language
- Use Jinja2 filters: `{{ var | tojson }}` for strings in Python
- Use template literal escaping for TypeScript: replace backticks and `$`

**Warning signs:** Generated code has syntax errors, or worse, executes unintended operations.

### Pitfall 2: Missing Dependencies in Export

**What goes wrong:** User exports code but it fails to run because dependencies aren't documented.

**Why it happens:** Focus on main code file, forgetting requirements.txt/package.json.

**How to avoid:**
- Always generate accompanying requirements.txt (Python) or package.json (TypeScript)
- Include setup instructions in generated code comments
- Export as zip with all files

**Warning signs:** User support requests about "module not found" errors.

### Pitfall 3: Outdated SDK Patterns

**What goes wrong:** Generated code uses deprecated API patterns.

**Why it happens:** SDK evolves, templates become stale.

**How to avoid:**
- Version-pin SDK in generated dependencies
- Document SDK version in generated code comments
- Periodic template review against SDK changelog
- Add SDK version to IR for future migration

**Warning signs:** Deprecation warnings when running generated code.

### Pitfall 4: Large Bundle Size from Monaco

**What goes wrong:** Application bundle becomes huge (Monaco is ~2MB).

**Why it happens:** Monaco includes all language support by default.

**How to avoid:**
- Use `@monaco-editor/react` (lazy loads Monaco)
- Configure only needed languages (typescript, python)
- Consider dynamic import for code preview component

**Warning signs:** Initial page load > 3 seconds, bundle analysis shows Monaco dominating.

### Pitfall 5: Async/Await Handling in Generated Code

**What goes wrong:** Generated code doesn't properly handle the async nature of Claude Agent SDK.

**Why it happens:** Both Python and TypeScript SDKs use async iterators.

**How to avoid:**
- Always generate proper async main() function
- Include asyncio.run() for Python
- Use `for await...of` for TypeScript
- Handle cleanup/errors in generated code

**Warning signs:** Runtime errors about async iterators, uncaught promise rejections.

## Code Examples

### Claude Agent SDK - TypeScript Basic Pattern
```typescript
// Source: https://platform.claude.com/docs/en/agent-sdk/typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Your task here",
  options: {
    allowedTools: ["Read", "Edit", "Bash"],
    permissionMode: "acceptEdits"
  }
})) {
  if (message.type === "result" && message.subtype === "success") {
    console.log(message.result);
  }
}
```

### Claude Agent SDK - Python Basic Pattern
```python
# Source: https://platform.claude.com/docs/en/agent-sdk/python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Bash"],
        permission_mode="acceptEdits"
    )

    async for message in query(
        prompt="Your task here",
        options=options
    ):
        if hasattr(message, "result"):
            print(message.result)

asyncio.run(main())
```

### Claude Agent SDK - MCP Server Configuration (TypeScript)
```typescript
// Source: https://platform.claude.com/docs/en/agent-sdk/mcp
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Use the tools to complete this task",
  options: {
    mcpServers: {
      "github": {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-github"],
        env: {
          GITHUB_TOKEN: process.env.GITHUB_TOKEN
        }
      },
      "remote-api": {
        type: "sse",
        url: "https://api.example.com/mcp/sse"
      }
    },
    allowedTools: ["mcp__github__*", "mcp__remote-api__*"]
  }
})) {
  // Process messages
}
```

### Claude Agent SDK - MCP Server Configuration (Python)
```python
# Source: https://platform.claude.com/docs/en/agent-sdk/mcp
import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        mcp_servers={
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]
                }
            }
        },
        allowed_tools=["mcp__github__*"]
    )

    async for message in query(
        prompt="List issues in the repository",
        options=options
    ):
        pass

asyncio.run(main())
```

### Monaco Editor - Basic Preview Component
```tsx
// Source: https://www.npmjs.com/package/@monaco-editor/react
import Editor from '@monaco-editor/react';

interface CodePreviewProps {
  code: string;
  language: 'typescript' | 'python';
  onCodeChange?: (value: string | undefined) => void;
  readOnly?: boolean;
}

export function CodePreview({
  code,
  language,
  onCodeChange,
  readOnly = true
}: CodePreviewProps) {
  return (
    <Editor
      height="400px"
      language={language}
      value={code}
      onChange={onCodeChange}
      options={{
        readOnly,
        minimap: { enabled: false },
        fontSize: 13,
        lineNumbers: 'on',
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 2,
      }}
      theme="vs-dark"
    />
  );
}
```

### File Export with file-saver
```typescript
// Source: https://www.npmjs.com/package/file-saver
import { saveAs } from 'file-saver';
import JSZip from 'jszip';

export async function exportAsZip(
  files: { name: string; content: string }[],
  zipName: string
) {
  const zip = new JSZip();

  for (const file of files) {
    zip.file(file.name, file.content);
  }

  const blob = await zip.generateAsync({ type: 'blob' });
  saveAs(blob, zipName);
}

// Usage for Python export:
exportAsZip([
  { name: 'agent.py', content: generatedPythonCode },
  { name: 'requirements.txt', content: 'claude-agent-sdk\n' },
  { name: 'README.md', content: '# Generated Agent\n\n...' }
], 'my-agent-python.zip');
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Claude Code SDK | Claude Agent SDK | Jan 2026 | Renamed, check migration guide for breaking changes |
| query() with callbacks | Async iterators (for await) | 2025 | Both Python and TS use async iteration patterns |
| Manual tool execution | Built-in tool execution | 2025 | SDK handles Read, Edit, Bash tools automatically |
| Custom MCP integration | First-class mcpServers option | 2025 | MCP configuration is now a simple options object |

**Deprecated/outdated:**
- **Claude Code SDK name**: Now called Claude Agent SDK. Migration guide available.
- **Callback-based streaming**: Both SDKs now use async iterators exclusively.

## Open Questions

1. **Logic nodes in generated code**
   - What we know: PACO has Logic nodes (condition, loop, parallel, approval)
   - What's unclear: Claude Agent SDK doesn't have direct equivalents for conditional branching
   - Recommendation: For v1, generate comments indicating logic flow; actual implementation requires subagents or hooks

2. **Knowledge nodes in generated code**
   - What we know: PACO has Knowledge nodes with document/URL sources
   - What's unclear: Claude Agent SDK doesn't have built-in RAG/knowledge integration
   - Recommendation: Generate comments with knowledge source URLs; actual RAG requires external integration

3. **Multi-agent workflows**
   - What we know: SDK supports subagents via Task tool
   - What's unclear: How to represent multi-agent flows from visual canvas
   - Recommendation: For v1, single-agent focus; multi-agent is Phase 8+

## Sources

### Primary (HIGH confidence)
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview) - Core SDK documentation
- [Claude Agent SDK TypeScript Reference](https://platform.claude.com/docs/en/agent-sdk/typescript) - Complete TypeScript API
- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) - Complete Python API
- [Claude Agent SDK MCP Documentation](https://platform.claude.com/docs/en/agent-sdk/mcp) - MCP server configuration
- [Claude Agent SDK Quickstart](https://platform.claude.com/docs/en/agent-sdk/quickstart) - Getting started patterns
- [GitHub: claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python) - Python SDK source
- [GitHub: claude-agent-sdk-typescript](https://github.com/anthropics/claude-agent-sdk-typescript) - TypeScript SDK source

### Secondary (MEDIUM confidence)
- [@monaco-editor/react](https://www.npmjs.com/package/@monaco-editor/react) - React Monaco wrapper
- [Jinja2 Documentation](https://jinja.palletsprojects.com/) - Python templating
- [file-saver](https://www.npmjs.com/package/file-saver) - Browser file downloads
- [Real Python - Jinja Templating](https://realpython.com/primer-on-jinja-templating/) - Jinja2 best practices
- [LogRocket - Monaco Editor](https://blog.logrocket.com/build-web-editor-with-react-monaco-editor/) - Monaco integration patterns

### Tertiary (LOW confidence)
- WebSearch results for code generation patterns - General industry practices

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Anthropic documentation verified
- Architecture: HIGH - Patterns derived from official SDK examples
- Pitfalls: MEDIUM - Based on general code generation experience + SDK docs
- Code examples: HIGH - Directly from official documentation

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - SDK is stable but check for updates)

**Note on SDK versions:** The Claude Agent SDK was recently renamed from Claude Code SDK. Templates should include the current SDK version in generated dependency files. Check the official changelog periodically for breaking changes.
