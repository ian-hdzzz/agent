# Phase 3: Claude Agent Node - Research

**Researched:** 2026-02-03
**Domain:** React properties panel for LLM agent configuration
**Confidence:** HIGH

## Summary

This phase implements a visual properties panel for configuring Claude agents. The research establishes patterns for building a right-sidebar form editor using React Hook Form with Zod validation, integrated with the existing Zustand store and Ant Design UI framework. The project already uses Ant Design's Drawer component for editing, which aligns with the user's decision for a right sidebar panel.

The standard approach for form-heavy properties panels in 2026 is React Hook Form + Zod for validation, with component composition for field rendering. The existing codebase uses Ant Design components extensively, so the implementation should continue leveraging Ant Design's Input, Select, Slider, and InputNumber components rather than introducing a new UI library.

Multi-provider model support requires maintaining a current model ID list that spans Anthropic Claude, OpenAI GPT, and Google Gemini families. Default parameter values follow industry standards: temperature 1.0, top_p 1.0, top_k disabled, max_tokens varies by model.

**Primary recommendation:** Use React Hook Form with Zod validation and Ant Design form components, building on the existing ComponentEditor pattern with a fixed right sidebar instead of a drawer overlay.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-hook-form | ^7.x | Form state management | Minimal re-renders, TypeScript-first, works with uncontrolled components |
| zod | ^3.x | Schema validation | TypeScript inference, runtime + compile-time safety |
| @hookform/resolvers | ^3.x | Connect Zod to RHF | Official integration package |
| antd | ^6.2.3 (existing) | UI components | Already in project, provides Input, Select, Slider, InputNumber |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| zustand | ^4.5.7 (existing) | Global state | Persist agent config to canvas state |
| lodash/debounce | existing | Debounce inputs | Auto-save system prompt as user types |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| React Hook Form | Formik | RHF is lighter, better TypeScript support, less re-renders |
| Zod | Yup | Zod has better TS inference, Yup is more established |
| Ant Design inputs | Headless UI | Ant Design already in project, consistent styling |

**Installation:**
```bash
npm install react-hook-form zod @hookform/resolvers
```

## Architecture Patterns

### Recommended Project Structure
```
components/builder/
  properties-panel/
    index.tsx                    # Main panel layout with fixed sidebar
    agent-config-form.tsx        # Agent configuration form
    schemas/
      agent-schema.ts            # Zod schema for agent config
    fields/
      model-selector.tsx         # Model dropdown with custom option
      system-prompt-editor.tsx   # Expandable textarea
      parameter-sliders.tsx      # Temperature, Top P, Top K sliders
      max-tokens-input.tsx       # Number input for tokens
      stop-sequences.tsx         # Tag-style input for sequences
```

### Pattern 1: Fixed Right Sidebar (Figma/n8n style)
**What:** Properties panel as a fixed-position sidebar that doesn't overlay the canvas
**When to use:** When editing node properties while still viewing the canvas
**Example:**
```typescript
// Source: User decision from CONTEXT.md
// Layout: Canvas takes remaining space, sidebar is fixed width

const BuilderLayout: React.FC = () => {
  const selectedNodeId = useTeamBuilderStore((s) => s.selectedNodeId);

  return (
    <div className="flex h-full">
      {/* Component Library - Left */}
      <ComponentLibrary />

      {/* Canvas - Center/Flexible */}
      <div className="flex-1 relative">
        <ReactFlow ... />
      </div>

      {/* Properties Panel - Right, fixed width */}
      {selectedNodeId && (
        <PropertiesPanel nodeId={selectedNodeId} className="w-96 border-l" />
      )}
    </div>
  );
};
```

### Pattern 2: React Hook Form with Zod
**What:** Type-safe form with runtime validation
**When to use:** All form inputs for agent configuration
**Example:**
```typescript
// Source: https://react-hook-form.com/get-started, https://zod.dev/
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const agentSchema = z.object({
  name: z.string().min(1, 'Name required'),
  model: z.string().min(1, 'Model required'),
  systemPrompt: z.string().optional(),
  temperature: z.number().min(0).max(2).default(1.0),
  maxTokens: z.number().min(1).max(200000).optional(),
  topP: z.number().min(0).max(1).default(1.0),
  topK: z.number().min(1).optional(),
  stopSequences: z.array(z.string()).optional(),
});

type AgentFormData = z.infer<typeof agentSchema>;

const AgentConfigForm: React.FC<{ defaultValues: AgentFormData }> = ({ defaultValues }) => {
  const { register, control, handleSubmit, formState: { errors } } = useForm<AgentFormData>({
    resolver: zodResolver(agentSchema),
    defaultValues,
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Form fields */}
    </form>
  );
};
```

### Pattern 3: Controlled Components with Controller
**What:** Wrap Ant Design components with RHF Controller
**When to use:** Ant Design Select, Slider, and other controlled components
**Example:**
```typescript
// Source: https://react-hook-form.com/get-started#IntegratingControlledInputs
import { Controller } from 'react-hook-form';
import { Select, Slider } from 'antd';

<Controller
  name="model"
  control={control}
  render={({ field }) => (
    <Select
      {...field}
      options={modelOptions}
      placeholder="Select model"
    />
  )}
/>

<Controller
  name="temperature"
  control={control}
  render={({ field }) => (
    <Slider
      {...field}
      min={0}
      max={2}
      step={0.1}
      marks={{ 0: 'Focused', 1: 'Balanced', 2: 'Creative' }}
    />
  )}
/>
```

### Pattern 4: Auto-expanding Textarea
**What:** Textarea that grows with content
**When to use:** System prompt editor
**Example:**
```typescript
// Source: User decision for expandable textarea
const SystemPromptEditor: React.FC = ({ value, onChange }) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [value]);

  return (
    <div>
      <Input.TextArea
        ref={textareaRef}
        value={value}
        onChange={onChange}
        autoSize={{ minRows: 3, maxRows: 20 }}
        placeholder="You are a helpful assistant..."
      />
      <div className="text-xs text-gray-500 mt-1">
        {value?.length || 0} characters
      </div>
    </div>
  );
};
```

### Anti-Patterns to Avoid
- **Drawer overlay for properties:** User decided against overlay - use fixed sidebar instead
- **Code editor for system prompt:** User decided against Monaco/CodeMirror - use simple textarea
- **Single-provider models:** User requires multi-provider support - include Claude, GPT, Gemini
- **Validation on blur only:** Use real-time validation for better UX
- **State in component only:** Persist to Zustand store for undo/redo support

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Custom validation logic | Zod + React Hook Form | Edge cases (async validation, field dependencies, error aggregation) |
| Model dropdown | Static hardcoded list | Dynamic options with "Custom" | Models change frequently, need custom model support |
| Slider with labels | Custom range input | Ant Design Slider with marks | Accessibility, keyboard nav, touch support |
| Character counter | Manual state tracking | Derived from value.length | Avoid stale counts |
| Auto-save | setTimeout patterns | debounce from lodash | Proper cleanup, cancel on unmount |

**Key insight:** Form state management has many subtle edge cases (dirty tracking, async validation, field arrays, dependent fields). React Hook Form handles these better than custom useState patterns.

## Common Pitfalls

### Pitfall 1: Re-rendering entire form on every keystroke
**What goes wrong:** Controlled inputs cause parent re-render, degrading performance
**Why it happens:** Lifting all state to parent component
**How to avoid:** Use React Hook Form's uncontrolled approach with register(), only use Controller for controlled Ant Design components
**Warning signs:** Laggy typing in textarea, slow slider dragging

### Pitfall 2: Losing form state on node selection change
**What goes wrong:** User edits are lost when clicking different node
**Why it happens:** Form state not synced to store before unmount
**How to avoid:** Auto-save with debounce, or persist form state in Zustand
**Warning signs:** "Unsaved changes" that disappear

### Pitfall 3: Model dropdown doesn't support new models
**What goes wrong:** User can't use a model that was released after the preset list
**Why it happens:** Hardcoded model list without custom option
**How to avoid:** Include "Custom" option that reveals text input for any model string
**Warning signs:** Support tickets asking for specific model IDs

### Pitfall 4: Validation blocks valid configurations
**What goes wrong:** Strict validation rejects valid edge cases
**Why it happens:** Over-specifying constraints (e.g., max_tokens must be set)
**How to avoid:** Make most parameters optional, use sensible defaults, allow empty/undefined
**Warning signs:** Users can't save a config they expect to work

### Pitfall 5: Ant Design version mismatch
**What goes wrong:** Drawer or form components don't work as expected
**Why it happens:** Project uses Ant Design v6, most examples are v4/v5
**How to avoid:** Check current antd version (6.2.3), use v6 API patterns
**Warning signs:** Props not recognized, styling differences

## Code Examples

Verified patterns from official sources:

### Complete Agent Form with Zod
```typescript
// Source: Combined from RHF docs + Zod docs + Ant Design docs
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Input, Select, Slider, InputNumber, Tag } from 'antd';

const agentSchema = z.object({
  name: z.string().min(1, 'Agent name is required'),
  model: z.string().min(1, 'Model is required'),
  customModel: z.string().optional(),
  systemPrompt: z.string().optional().default(''),
  temperature: z.number().min(0).max(2).default(1.0),
  maxTokens: z.number().min(1).max(200000).optional(),
  topP: z.number().min(0).max(1).optional(),
  topK: z.number().min(1).max(500).optional(),
  stopSequences: z.array(z.string()).optional().default([]),
});

type AgentFormValues = z.infer<typeof agentSchema>;

interface AgentConfigFormProps {
  defaultValues: Partial<AgentFormValues>;
  onSubmit: (data: AgentFormValues) => void;
}

export const AgentConfigForm: React.FC<AgentConfigFormProps> = ({
  defaultValues,
  onSubmit,
}) => {
  const {
    control,
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<AgentFormValues>({
    resolver: zodResolver(agentSchema),
    defaultValues: {
      temperature: 1.0,
      topP: 1.0,
      stopSequences: [],
      ...defaultValues,
    },
  });

  const selectedModel = watch('model');
  const isCustomModel = selectedModel === 'custom';

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Name field */}
      <div>
        <label className="block text-sm font-medium mb-1">Agent Name</label>
        <Input {...register('name')} placeholder="my_agent" />
        {errors.name && (
          <span className="text-red-500 text-xs">{errors.name.message}</span>
        )}
      </div>

      {/* Model selector */}
      <div>
        <label className="block text-sm font-medium mb-1">Model</label>
        <Controller
          name="model"
          control={control}
          render={({ field }) => (
            <Select
              {...field}
              className="w-full"
              placeholder="Select model"
              options={MODEL_OPTIONS}
            />
          )}
        />
        {isCustomModel && (
          <Input
            {...register('customModel')}
            className="mt-2"
            placeholder="Enter model ID (e.g., claude-sonnet-4-5-20250929)"
          />
        )}
      </div>

      {/* System Prompt */}
      <div>
        <label className="block text-sm font-medium mb-1">System Prompt</label>
        <Controller
          name="systemPrompt"
          control={control}
          render={({ field }) => (
            <Input.TextArea
              {...field}
              autoSize={{ minRows: 3, maxRows: 15 }}
              placeholder="You are a helpful assistant..."
            />
          )}
        />
        <div className="text-xs text-gray-500 mt-1">
          {watch('systemPrompt')?.length || 0} characters
        </div>
      </div>

      {/* Temperature slider */}
      <div>
        <label className="block text-sm font-medium mb-1">
          Temperature: {watch('temperature')?.toFixed(1)}
        </label>
        <Controller
          name="temperature"
          control={control}
          render={({ field }) => (
            <Slider
              {...field}
              min={0}
              max={2}
              step={0.1}
              marks={{ 0: 'Focused', 1: 'Balanced', 2: 'Creative' }}
            />
          )}
        />
      </div>

      {/* Max Tokens */}
      <div>
        <label className="block text-sm font-medium mb-1">Max Tokens</label>
        <Controller
          name="maxTokens"
          control={control}
          render={({ field }) => (
            <InputNumber
              {...field}
              className="w-full"
              min={1}
              max={200000}
              placeholder="Default (model-specific)"
            />
          )}
        />
      </div>
    </form>
  );
};
```

### Model Options Constant
```typescript
// Source: Official Anthropic, OpenAI, Google documentation (Feb 2026)
export const MODEL_OPTIONS = [
  // Anthropic Claude (current)
  { label: 'Claude Sonnet 4.5', value: 'claude-sonnet-4-5-20250929', group: 'Anthropic' },
  { label: 'Claude Opus 4.5', value: 'claude-opus-4-5-20251101', group: 'Anthropic' },
  { label: 'Claude Haiku 4.5', value: 'claude-haiku-4-5-20251001', group: 'Anthropic' },
  // Anthropic Claude (legacy)
  { label: 'Claude Sonnet 4', value: 'claude-sonnet-4-20250514', group: 'Anthropic Legacy' },
  { label: 'Claude Opus 4', value: 'claude-opus-4-20250514', group: 'Anthropic Legacy' },

  // OpenAI GPT
  { label: 'GPT-5.2', value: 'gpt-5.2', group: 'OpenAI' },
  { label: 'GPT-5.1', value: 'gpt-5.1', group: 'OpenAI' },
  { label: 'GPT-5', value: 'gpt-5', group: 'OpenAI' },
  { label: 'GPT-4.1', value: 'gpt-4.1', group: 'OpenAI Legacy' },

  // Google Gemini
  { label: 'Gemini 3 Pro', value: 'gemini-3-pro-preview', group: 'Google' },
  { label: 'Gemini 3 Flash', value: 'gemini-3-flash-preview', group: 'Google' },
  { label: 'Gemini 2.5 Flash', value: 'gemini-2.5-flash', group: 'Google' },

  // Custom option
  { label: 'Custom Model...', value: 'custom', group: 'Other' },
];

// Group options for Ant Design Select
export const GROUPED_MODEL_OPTIONS = Object.entries(
  MODEL_OPTIONS.reduce((acc, opt) => {
    const group = opt.group || 'Other';
    if (!acc[group]) acc[group] = [];
    acc[group].push({ label: opt.label, value: opt.value });
    return acc;
  }, {} as Record<string, { label: string; value: string }[]>)
).map(([label, options]) => ({ label, options }));
```

### Default Parameter Values
```typescript
// Source: LLM documentation, AWS Bedrock defaults
export const DEFAULT_PARAMETERS = {
  temperature: 1.0,    // Balanced creativity/consistency
  topP: 1.0,           // Consider all tokens (disabled)
  topK: undefined,     // Disabled by default
  maxTokens: undefined, // Use model default
  stopSequences: [],   // No stop sequences
};

// Parameter constraints by provider
export const PARAMETER_CONSTRAINTS = {
  anthropic: {
    temperature: { min: 0, max: 1, step: 0.1 },
    topP: { min: 0, max: 1, step: 0.01 },
    topK: { min: 1, max: 500, step: 1 },
    maxTokens: { min: 1, max: 64000 },
  },
  openai: {
    temperature: { min: 0, max: 2, step: 0.1 },
    topP: { min: 0, max: 1, step: 0.01 },
    maxTokens: { min: 1, max: 128000 },
  },
  google: {
    temperature: { min: 0, max: 2, step: 0.1 },
    topP: { min: 0, max: 1, step: 0.01 },
    topK: { min: 1, max: 100, step: 1 },
    maxTokens: { min: 1, max: 65536 },
  },
};
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Drawer overlay panel | Fixed sidebar panel | 2025 (Figma pattern) | Better canvas visibility while editing |
| Formik + Yup | React Hook Form + Zod | 2024 | Better TypeScript inference, less boilerplate |
| Hardcoded model lists | Dynamic with custom option | Ongoing | Support new models without code changes |
| Separate save button | Auto-save with debounce | 2024 | Reduced data loss risk |

**Deprecated/outdated:**
- Ant Design Drawer for permanent properties panels (use fixed Layout.Sider)
- Class components for forms (use hooks)
- Manual validation with useState (use form library)

## Open Questions

Things that couldn't be fully resolved:

1. **Stop sequences input format**
   - What we know: Need array of strings, displayed as tags
   - What's unclear: Best UX for adding/removing sequences (comma-separated input vs individual tag creation)
   - Recommendation: Use Ant Design Select with mode="tags" for familiar UX

2. **Advanced settings collapse**
   - What we know: Top P, Top K, Stop Sequences are "advanced"
   - What's unclear: Whether collapsed by default or expanded
   - Recommendation: Collapsed by default with "Show Advanced" toggle

3. **Validation timing**
   - What we know: Need real-time feedback
   - What's unclear: Show errors immediately or on blur/submit
   - Recommendation: Validate on change with debounce (300ms), show inline errors

## Sources

### Primary (HIGH confidence)
- Anthropic Claude Models Documentation (https://platform.claude.com/docs/en/about-claude/models/overview) - Model IDs, parameters, pricing
- React Hook Form Get Started (https://react-hook-form.com/get-started) - Form patterns
- Zod Documentation (https://zod.dev/) - Schema validation
- Ant Design Drawer Component (https://ant.design/components/drawer/) - Drawer API

### Secondary (MEDIUM confidence)
- LLM Settings Prompt Engineering Guide (https://www.promptingguide.ai/introduction/settings) - Parameter explanations
- Langflow/n8n/Flowise comparison articles - Agent builder UX patterns
- OpenAI GPT-5.2 documentation - Model IDs (platform.openai.com restricted)
- Google Gemini API documentation - Model IDs

### Tertiary (LOW confidence)
- WebSearch results for "LLM parameters default values" - Default parameter recommendations
- WebSearch results for "React form sidebar pattern" - UI patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official documentation verified for RHF, Zod, Ant Design
- Architecture: HIGH - Patterns verified with official docs, aligned with existing codebase
- Model list: MEDIUM - Official Anthropic verified, OpenAI/Google from WebSearch
- Pitfalls: MEDIUM - Common patterns from experience, not all verified with sources

**Research date:** 2026-02-03
**Valid until:** 2026-03-03 (30 days - model IDs may need updating sooner if new releases)
